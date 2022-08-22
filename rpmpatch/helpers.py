#!/usr/bin/env python
# pylint: disable=line-too-long

'''
    This is a simple script where it all comes together.
    You can make you own if you want but this one is rather simple
'''

import configparser
import difflib
import os
import re
import shutil
import sys
import tarfile
import tempfile

# make it easier to test this from the source archive
PARENT, BINDIR = os.path.split(os.path.dirname(os.path.abspath(sys.argv[0])))
if os.path.exists(os.path.join(PARENT, 'rpmpatch')):
    sys.path.insert(0, PARENT)

from rpmpatch.SourcePackage import SourcePackage
from rpmpatch.SpecFile import SpecFile


def rpmpatch(configdir, srpm, changelog_user, verbose=False, keep_dist=False):
    '''
        Read the config, perform the steps, build the package
    '''
    package = SourcePackage(srpm)
    name = package.packageName()
    version = package.packageVersion()
    release = package.packageRelease()
    cfgfilename = configdir + '/' + name + '.ini'
    if not os.path.isfile(cfgfilename):
        otherspot = configdir + '/' + name + '/' + name + '.ini'
        if not os.path.isfile(otherspot):
            raise RuntimeError('No config file found for ' + srpm)
        else:
            cfgfilename = configdir + '/' + name + '/' + name + '.ini'

    config = configparser.SafeConfigParser()
    config.read(cfgfilename)

    configdir = os.path.abspath(os.path.dirname(cfgfilename))

    cfg_file = {}
    for section in config.sections():
        cfg_file[section] = {}
        for entry in config.options(section):
            value = config.get(section, entry)
            cfg_file[section.lower()][entry] = value

    # empty is ok, but we do need these
    if 'program' not in cfg_file:
        cfg_file['program'] = {}
    if 'autodist' not in cfg_file:
        cfg_file['autodist'] = {}
    if 'define' not in cfg_file:
        cfg_file['define'] = []

    # need changelog user or else
    if changelog_user is None:
        if 'changelog_user' in cfg_file['program']:
            changelog_user = cfg_file['program']['changelog_user']
        else:
            print('\nMissing changelog user, see --help or config file', file=sys.stderr)
            sys.exit(1)

    if verbose:
        print('# working on ' + srpm)

    # don't bother installing until we have a config file
    package.install()

    specfile = SpecFile(package.specfile, changelog_user)

    not_applicable = []
    if 'package_config' not in cfg_file['program']:
        cfg_file['program']['package_config'] = False
    elif cfg_file['program']['package_config'] in ('false', 'False', 'none', 'None', ''):
        cfg_file['program']['package_config'] = False

    if 'package_unused' not in cfg_file['program']:
        cfg_file['program']['package_unused'] = False
    elif cfg_file['program']['package_unused'] in ('false', 'False', 'none', 'None', ''):
        cfg_file['program']['package_unused'] = False

    if 'compile' not in cfg_file['program']:
        cfg_file['program']['compile'] = False
    elif cfg_file['program']['compile'] in ('false', 'False', 'none', 'None', ''):
        cfg_file['program']['compile'] = False

    if 'build_targets' not in cfg_file['program']:
        cfg_file['program']['build_targets'] = None
    elif cfg_file['program']['build_targets'] in ('false', 'False', 'none', 'None', ''):
        cfg_file['program']['build_targets'] = None

    if 'enable_autodist' not in cfg_file['autodist']:
        cfg_file['autodist']['enable_autodist'] = False
    elif cfg_file['autodist']['enable_autodist'] in ('false', 'False', 'none', 'None', ''):
        cfg_file['autodist']['enable_autodist'] = False

    if 'autodist_re_match' not in cfg_file['autodist']:
        cfg_file['autodist']['autodist_re_match'] = None
    if 'autodist_re_replace' not in cfg_file['autodist']:
        cfg_file['autodist']['autodist_re_replace'] = None

    # get into sorted order
    sections = list(cfg_file.keys())
    sections.sort()

    if cfg_file['autodist']['enable_autodist']:
        autodist = find_dist_tag(cfg_file, srpm, specfile)
        cfg_file['define'].append(('dist', autodist))

    # do all specfile work
    for section in sections:
        if section.startswith('spec'):
            if not cfg_file[section]['diff'].startswith('/'):
                cfg_file[section]['diff'] = configdir + '/' + cfg_file[section]['diff']
            if 'package_config' not in cfg_file[section]:
                cfg_file[section]['package_config'] = cfg_file['program']['package_config']
            result = spec_patch(cfg_file[section], version, specfile)
            if result == NotImplemented:
                not_applicable.append(cfg_file[section]['diff'])
            elif verbose:
                print('## applied ' + cfg_file[section]['diff'])

    # do all regex work
    for section in sections:
        if section.startswith('re'):
            result = run_re(cfg_file[section], version, specfile)
            if result == NotImplemented:
                pass
            elif verbose:
                print('## ran regex ' + cfg_file[section]['match'] + '=>' + cfg_file[section]['replace'])

    # do all patch work
    for section in sections:
        if section.startswith('patch'):
            if not cfg_file[section]['patch'].startswith('/'):
                cfg_file[section]['patch'] = configdir + '/' + cfg_file[section]['patch']
            result = patches(cfg_file[section], section, version, specfile)
            if result == NotImplemented:
                not_applicable.append(cfg_file[section]['patch'])
            elif verbose:
                print('## ' + str(cfg_file[section]['method']) + ' patch ' + str(result[1]) + ' num:' + str(result[0]) + ' stripe:' + str(result[2]))

    # do all source work
    for section in sections:
        if section.startswith('source'):
            if not cfg_file[section]['source'].startswith('/'):
                cfg_file[section]['source'] = configdir + '/' + cfg_file[section]['source']
            result = sources(cfg_file[section], section, version, specfile)
            if result == NotImplemented:
                not_applicable.append(cfg_file[section]['source'])
            elif verbose:
                print('## processed source ' + result[1])

    if cfg_file['program']['package_config']:
        fake_source = {}
        fake_source['method'] = 'add'
        fake_source['source'] = cfgfilename
        fake_source['changelog'] = 'Config file for automated patch script'
        sources(fake_source, 'program', version, specfile)
        if verbose:
            print('## added config file')

    if not_applicable:
        if cfg_file['program']['package_unused']:
            tararchive = name + '-extras-python-rpmpatch.tar.bz2'
            tempdir = tempfile.mkdtemp()
            tar = tarfile.open(tempdir + '/' + tararchive, 'w:bz2')
            os.chdir(tempdir)
            for filepath in not_applicable:
                shutil.copy2(filepath, tempdir)
                filename = os.path.basename(filepath)
                tar.add(filename)
            tar.close()

            fake_source = {}
            fake_source['method'] = 'add'
            fake_source['source'] = tararchive
            fake_source['changelog'] = 'Un-used items from automated patch script'

            sources(fake_source, 'program', version, specfile)

            os.chdir(tempfile.gettempdir())
            # done with this, clean it up
            shutil.rmtree(tempdir)
            if verbose:
                print('## added un-used items')

    if verbose:
        print('## building rpm')

    defines_dict = {}
    for thing in cfg_file['define']:
        defines_dict[thing[0]] = thing[1]

    if keep_dist:
        dist = __guess_srpm_dist(release) 
        defines_dict['%dist'] = f'.{dist}'

    built = specfile.build(defines_dict, cfg_file['program']['compile'],
                           cfg_file['program']['build_targets'])
    return built


def __guess_srpm_dist(release):
    """
    the dist tag must be extracted from the release. The problem is that it might look like this:
    - %release.%dist
    - %release.%dist.%subrelease
    - %dist.%release
    so the easiest thing is going through release, mark the index of first
    not numerical and not dot character then find next dot or end of the
    string.
    This method still won't work if %release is something like:
    git_123123123.el8_6. So it's not very clever
    
    There is a separate way to find distag for modular package that is based on
    the `module+` string.
    """
    if 'module+' not in release:
        # using set to make it a little bit faster than array
        skip_chars = set(['.']+[str(x) for x in range(0, 9)])
        dist_first_char = -1
        dist_last_char = -1
        index = 0
        while index < len(release):
            # stop counting after dot (skip_chars changed inside loop) when
            # dist_first_char is assigned
            if dist_first_char > 0 and release[index] in skip_chars:
                break

            if release[index] not in skip_chars:
                skip_chars = set('.')  # this is stupid
                if dist_first_char < 0:
                    dist_first_char = index
                    dist_last_char = index
                else:
                    dist_last_char += 1

            index += 1
        dist = release[dist_first_char:dist_last_char+1]
        print(f"Found dist {dist} - keeping it")
    else:  # f*** modularity, silent majority, raised by system(d) - builderwise
        disttag_index = release.find('module+')
        # if there is disttag with .module, we can add our own modified packages
        # that might not have it
        if disttag_index >= 0:
            src_rpm_disttag = release[disttag_index:]
            # WELL no so fast! Sometimes there are packages that have modular
            # disttag and also additional release number! That's why we also
            # check if there is nothing after "extra"(additional release) dot
            last_dot_index = src_rpm_disttag.rfind('.')
            src_rpm_orig_length = len(src_rpm_disttag)
            # Number 5 is arbitrary but worked for all EuroLinux builds
            print(f"{last_dot_index}, {src_rpm_orig_length}")
            if src_rpm_orig_length - 5 < last_dot_index:
                print("I'm here")
                dist = src_rpm_disttag[:last_dot_index]
            else:
                dist = src_rpm_disttag
    return dist


def find_dist_tag(config, srpm, specfile):
    '''
        Look at a given spec file and try to find its dist tag
    '''
    thisfilename = os.path.basename(srpm).replace('.src.rpm', '')
    tmp_defines = {}

    disttag = ''

    for thing in config['define']:
        tmp_defines[thing[0]] = thing[1]
    tmp_defines['dist'] = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    name_with_odd_dist = os.path.basename(specfile.get_srpmname(tmp_defines)).replace('.src.rpm', '')

    difflist = difflib.Differ().compare(thisfilename, name_with_odd_dist)

    for item in difflist:
        if item[:1] == '-':
            disttag = disttag + item[2:]

    disttag = re.sub(config['autodist']['autodist_re_match'], config['autodist']['autodist_re_replace'], disttag)

    return disttag


def spec_patch(config, version, specfile):
    '''
        Apply a patch to the specfile
    '''
    if 'on_version' in config:
        if config['on_version'].startswith('['):
            config['on_version'] = eval(config['on_version'])
        else:
            config['on_version'] = [config['on_version']]

        if version not in config['on_version']:
            return NotImplemented

    changelog = config['changelog']
    patch = config['diff']
    return specfile.apply_specfile_diff(patch, changelog, config['package_config'])


def run_re(config, version, specfile):
    '''
        Run the listed regex against the specfile
    '''
    if 'on_version' in config:
        if config['on_version'].startswith('['):
            config['on_version'] = eval(config['on_version'])
        else:
            config['on_version'] = [config['on_version']]

        if version not in config['on_version']:
            return NotImplemented

    changelog = config['changelog']
    find = config['match']
    replace = config['replace']
    return specfile.run_re(find, replace, changelog)


def patches(config, section, version, specfile):
    '''
        Add or remove the patch listed
    '''
    if 'on_version' in config:
        if config['on_version'].startswith('['):
            config['on_version'] = eval(config['on_version'])
        else:
            config['on_version'] = [config['on_version']]

        if version not in config['on_version']:
            return NotImplemented

    method = config['method']
    changelog = config['changelog']
    stripe = None
    if method.lower() == 'add':
        name = config['patch']
        if 'stripe' in config:
            stripe = config['stripe']

        if 'num' in config:
            num = config['num']
        else:
            num = None
        return specfile.add_patch(name, stripe, num, changelog)

    if method.lower() == 'del':
        if 'num' in config:
            num = config['num']
        else:
            num = None

        if 'patch' in config:
            name = os.path.basename(config['patch'])
        else:
            name = None

        if num == name:
            raise RuntimeError('Bad ' + section + ' in config file')

        return specfile.rm_patch(name, num, changelog)


def sources(config, section, version, specfile):
    '''
        Add a source to the specfile
    '''
    if 'on_version' in config:
        if config['on_version'].startswith('['):
            config['on_version'] = eval(config['on_version'])
        else:
            config['on_version'] = [config['on_version']]

        if version not in config['on_version']:
            return NotImplemented

    changelog = config['changelog']
    method = config['method']

    if method.lower() == 'add':
        if 'num' in list(config.keys()):
            num = config['num']
        else:
            num = None
        thisfile = config['source']
        return specfile.add_source(thisfile, num, changelog)
    if method.lower() == 'del':
        if 'num' in list(config.keys()):
            num = config['num']
        else:
            num = None
        thisfile = config['source']
        return specfile.rm_source(thisfile, num, changelog)
    if method.lower() == 'replace':
        mysrc = config['source']
        specsrc = config['specsourcename']
        return specfile.replace_source(specsrc, mysrc, changelog)
    else:
        raise RuntimeError('Bad ' + section + ' in config file')


def parsesrpms(configdir, srpms, changelog_user, verbose=False, keep_dist=False):
    '''
        Loop through the rpms, possible use of threading here later
    '''
    result = []
    for srpm in srpms:
        result.append(rpmpatch(configdir, srpm, changelog_user, verbose, keep_dist))

    for item in result:
        for element in item:
            print("Wrote: " + element)
