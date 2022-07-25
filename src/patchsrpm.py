#!/usr/bin/env python3
# pylint: disable=line-too-long

'''
    This is a simple script where it all comes together.
    You can make you own if you want but this one is rather simple
'''

import os
import sys
import optparse
import rpm

# make it easier to test this from the source archive
#parent, bindir = os.path.split(os.path.dirname(os.path.abspath(sys.argv[0])))
#if os.path.exists(os.path.join(parent, 'rpmpatch')):
#    sys.path.insert(0, parent)

from helpers import parsesrpms

if __name__ == "__main__":


    # don't fix epilog white space, useful for manual formating control
    optparse.OptionParser.format_epilog = lambda self, formatter: self.epilog

    DEF_CONF = rpm.expandMacro('%_topdir') + '/CUSTOM_PATCHES'

    DESC = '''This program will take in a config directory along with source
              packages and then customize them for you based on config files.'''

    EPILOG = '\nExamples:\n\n'
    EPILOG = EPILOG + ' ' + sys.argv[0]
    EPILOG = EPILOG + ' my.src.rpm \n'
    EPILOG = EPILOG + ' ' + sys.argv[0]
    EPILOG = EPILOG + ' --configdir=/etc/myconf.d/  my.src.rpm\n'
    EPILOG = EPILOG + ' ' + sys.argv[0]
    EPILOG = EPILOG + ' --configdir=/etc/myconf.d/  my.src.rpm'
    EPILOG = EPILOG + ' --changelog_user=me\n'
    EPILOG = EPILOG + ' ' + sys.argv[0]
    EPILOG = EPILOG + ' --configdir=/etc/myconf.d/  my.src.rpm --verbose\n'
    EPILOG = EPILOG + '\n' + '#' * 78 + '\n'

    SAMPLE_CONFIG = '''

Things are run in groups organized by their section names.
Each section is run alphabeticaly, but the sections are run in this order:

autodist -> spec-> re -> patch -> source

This way your specfile adjustments and regex matches don't need to contend
with your other modifications

-------------------------------------------------
Example Config:
-------------------------------------------------
[program]
# you can control behavior here

# you can override this on the command line
changelog_user = me <my@addr.com>

# if you set this to 'True' the ini file used
# to configure this program will be added to the
# source rpm
package_config = True

# if you set this to 'True' any patches or sources
# that were not applied due to version restrictions
# will be placed in a tar archive called
# %{name}-extras-python-rpmpatch.tar.bz2
package_unused = True

# if set to 'True' then rpmbuild -bb will be called
# automatically rather than just rpmbuild -bs
compile = False

# which arches should this rpm be built for
# if this is defined, when a compile is requested
# the items here will be passed to rpmbuild as 
# a --target=<> 
build_targets = [ 'i386', 'i686' ]

[autodist]
# This program can attempt to determine the
# dist tag of the package and set it automatically
#
# NOTE: if you've defined 'dist' in the [define]
#       section, this will not work.
#       Everything defined in [define] will be used
#       to determine the dist tag.
enable_autodist = False

# Since you are changing the rpm, you really
# should change the dist tag, but with autodist
# the value is inherited from the source rpm
# so we provide a regex to wrapper to adjust
autodist_re_match = el
autodist_re_replace = sl

# anything you want set for rpmbuild, mark here
[define]
scl = python27
mymacro = somevalue

# ----------------------------------------------------
# The patch sections are either for adding or removing.
# They are processed in numeric order
[patch1]
# example for adding a patch
method = add

# DO NOT PUT THESE IN rpmbuild/SOURCES they will be copied in there for you
patch = /path/to/patch

# the arg to -p, ie 1 for -p1
stripe = 1

# you can leave the 'num' line off or set it if you want
num = 200

# on package version, this should be a list of versions
# for which this is performed.  The sort of thing you
# get from the %{version} macro
# If undefined, we assume you want everyone to get this
on_version = [ '1.2' ]

# you must have a changelog entry
changelog = I'm adding this patch to resolve issue and fix bug

# ----------------------------------------------------
[patch2]
# example for removing a patch
method = del

# you must either specify patch name or patch num
# your choice
patch = mypatch.patch
num = 12

# on package version, this should be a list of versions
# for which this is performed.  The sort of thing you
# get from the %{version} macro
# If undefined, we assume you want everyone to get this
on_version = [ '1.2' ]

# you must have a changelog entry
changelog = I'm removing this patch because it causes problem

# ----------------------------------------------------
# The 'source' sections are for adding sources right now
# Removing sources requires more complex work (like a patch)
# You probably still need a patch to do something with your newly added source
# They are processed in numeric order
[source1]
# example for adding a source
method = add

# DO NOT PUT THESE IN rpmbuild/SOURCES they will be copied in there for you
source = /path/to/source/file

# you can leave the 'num' line off or set it if you want
num = 200

# on package version, this should be a list of versions
# for which this is performed.  The sort of thing you
# get from the %{version} macro
# If undefined, we assume you want everyone to get this
on_version = [ '1.2' ]

# you must have a changelog entry
changelog = An extra thingy

[source2]
# example for removing a source
method = del

# By filename
source = thissource.tar.gz

# you can leave the 'num' line off or set it if you want
num = 200

# on package version, this should be a list of versions
# for which this is performed.  The sort of thing you
# get from the %{version} macro
# If undefined, we assume you want everyone to get this
on_version = [ '1.2' ]

# you must have a changelog entry
changelog = Not this thingy

# ----------------------------------------------------
# The 'spec' sections are for applying patches to the specfile itself
# when you've added a new source or want to remove a source file
# this is how you can do it.
# They are processed in numeric order
[spec1]
# The patch will be added as a 'Source' so you can review it later
diff = /path/to/patch

# on package version, this should be a list of versions
# for which this is performed.  The sort of thing you
# get from the %{version} macro
# If undefined, we assume you want everyone to get this
on_version = [ '1.2' ]

# you must have a changelog entry
changelog = I'm making some important changes such as 

# ----------------------------------------------------
# the 're' sections are for running any random regex you want
# against the specfile.  It isn't as focused as a patch, but that
# can be a benefit
# They are processed in numeric order
[re1]

# set your expression up here
match = .
replace = L

# on package version, this should be a list of versions
# for which this is performed.  The sort of thing you
# get from the %{version} macro
# If undefined, we assume you want everyone to get this
on_version = [ '1.2' ]

# you must have a changelog entry
changelog = I changed everything to L for some reason

'''

    PARSER = optparse.OptionParser(description=DESC, epilog=EPILOG)

    PARSER.add_option('--configdir', metavar="<"+DEF_CONF+">", default=DEF_CONF,
                      help='''Path to a directory containing ini style configs
                              for the rpms you wish to patch.  The config
                              filenames should be in the format %{name}.ini
                              or %{name}/%{name}.ini your choice.
                              For example, httpd-2.2-2.el5.i386.rpm would have
                              a config file named 'httpd.ini' within this
                              directory or a directory named 'httpd' with
                              a config file named 'httpd.ini' within.
                              The default is within your 'rpmbuild' location''')

    PARSER.add_option('--changelog_user', metavar="<USER>", default=None,
                      help='''Name of user who gets credit for these changes.
                              You can define this in the config if you want.
                              The command line will override this value if set.                               (OPTIONAL)''')

    PARSER.add_option('--sampleconfig', default=False, action='store_true',
                      help='''Show a sample config file''')

    PARSER.add_option('--verbose', default=False, action='store_true',
                      help='''Print action information''')

    (OPTIONS, ARGS) = PARSER.parse_args()

    if OPTIONS.sampleconfig:
        print(SAMPLE_CONFIG)
        sys.exit(1)

    if not os.path.isdir(os.path.expanduser(OPTIONS.configdir)):
        PARSER.print_help()
        print('')
        raise IOError('No such directory: ' + OPTIONS.configdir)

    if len(ARGS) < 1:
        PARSER.print_help()
        print('\nMissing srpm(s), see help', file=sys.stderr)

    for THEFILE in ARGS:
        if not os.path.isfile(THEFILE):
            raise IOError('No such file: ' + THEFILE)

    parsesrpms(os.path.expanduser(OPTIONS.configdir), ARGS, OPTIONS.changelog_user, OPTIONS.verbose)
