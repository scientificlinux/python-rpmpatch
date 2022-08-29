'''
    This makes the manipulation of some parts of a specfile very easy
'''

import datetime
import os
import re
import shutil
import subprocess
import tempfile


class SpecFile(object):
    '''
        Provides the manipulation functions of the automatic patch tools
    '''
    def __init__(self, specfile, changelog_user):
        '''
            Read in the specfile and setup our environment
        '''
        self.specfile = specfile

        self.changelog_user = changelog_user
        self.changelog = {}

        self.changelog_done = False

        self.text = None

        _fd = open(self.specfile, 'r')
        self.text = _fd.read()
        _fd.close()

        basedir = os.path.dirname(self.specfile)
        self.basedir = basedir
        self.sourcesdir = os.path.abspath(basedir + '/../SOURCES/')
        if os.path.isfile(self.sourcesdir + '/' + self.specfile):
            os.remove(self.sourcesdir + '/' + self.specfile)
        shutil.copy2(self.specfile, self.sourcesdir)

    def __del__(self):
        '''
            Make sure to save changes
        '''
        if self.text is not None:
            self.save()

    def build(self, define_dict=None, compileit=False, build_arches=None):
        '''
            Build a SRPM from this specfile

            If you want to define some values for build time (like %{dist})
            pass in a dict of the following form:

            { 'define': 'value' }

            and a macro named 'define' will be set to 'value' during rpmbuild

            If you set 'compileit' to True this runs rpmbuild -ba
            If you set 'build_arches' to a list, this will set --target for
             each item in the list
        '''
        self.save()

        buildsrc = ['rpmbuild', '-bs']

        defines = []
        if isinstance(define_dict, dict):
            for key in define_dict.keys():
                defines.append('--define')
                defines.append(key + ' ' + define_dict[key])

        buildsrc = buildsrc + defines

        buildsrc.append(self.specfile)

        tmpstdout = tempfile.NamedTemporaryFile()
        tmpstderr = tempfile.NamedTemporaryFile()

        code = subprocess.call(buildsrc, stdout=tmpstdout, stderr=tmpstderr)
        tmpstderr.seek(0)
        tmpstdout.seek(0)

        if code != 0:
            print(tmpstderr.read().decode('utf-8'))
            raise RuntimeError(' '.join(buildsrc))

        matches = re.findall(r'Wrote:\s(\S+.src.rpm)\n', tmpstdout.read().decode('utf-8'))
        tmpstdout.close()
        tmpstderr.close()

        rpms = [matches[0]]

        if compileit:
            if build_arches is None:
                build_arches = [None]
            for thisarch in build_arches:
                buildbinary = ['rpmbuild', '-bb']

                if thisarch is not None:
                    buildbinary.append('--target=' + thisarch)

                buildbinary = buildbinary + defines
                buildbinary.append(self.specfile)

                tmpstdout = tempfile.NamedTemporaryFile()
                tmpstderr = tempfile.NamedTemporaryFile()

                code = subprocess.call(buildbinary, shell=True,
                                       stderr=tmpstderr, stdout=tmpstdout)

                tmpstderr.seek(0)
                tmpstdout.seek(0)

                if code != 0:
                    print(tmpstderr.read().decode('utf-8'))
                    raise RuntimeError(' '.join(buildbinary))

                matches = re.findall(r'Wrote:\s(\S+.rpm)\n', tmpstdout.read().decode('utf-8'))

                rpms = rpms + matches

                tmpstdout.close()
                tmpstderr.close()

        return rpms

    def get_srpmname(self, define_dict=None):
        '''
            Based on the given 'defines' what is the expected name of the srpm
        '''
        query_string = ['rpm', '-q', '--qf', "'%{n}-%{v}-%{r}.src.rpm\\n'"]

        if isinstance(define_dict, dict):
            for key in define_dict.keys():
                query_string.append('--define')
                query_string.append(key + ' ' + define_dict[key])

        query_string.append('--specfile')
        query_string.append(self.specfile)

        # need a real shell for some things
        # can't use in memory buffers.... they aren't large enough
        tmpstdout = tempfile.NamedTemporaryFile(bufsize=0)
        tmpstderr = tempfile.NamedTemporaryFile(bufsize=0)

        code = subprocess.call(query_string,
                               stderr=tmpstderr, stdout=tmpstdout)

        tmpstderr.seek(0)
        tmpstdout.seek(0)

        if code != 0:
            print(tmpstderr.read().decode('utf-8'))
            raise RuntimeError(' '.join(query_string))

        matches = re.findall(r'(\S+.src.rpm)\n', tmpstdout.read().decode('utf-8'))

        tmpstdout.close()
        tmpstderr.close()

        return matches[0]

    def run_re(self, regex_match, regex_replace, changelog):
        '''
            Run a regex against the specfile
        '''
        self.text = re.sub(regex_match, regex_replace, self.text)

        regname = regex_match + ' => ' + regex_replace

        self.changelog['Ran Regex: ' + regname] = changelog

        return True

    def apply_specfile_diff(self, spec_patch, changelog, add_to_source=False):
        '''
            For any actual changes to the specfile you will need to generate
            a nice simple unified diff summarizing your changes.  The diff will
            be automatically added to the SRPM as a 'SOURCE' file so that you
            can easily review your changes in the future.

            This is not pure python. http://bugs.python.org/issue2057

            Your patch must have a stripe of '0' or things wont work right.
            Rather than accounting for all use cases I'm just forcing a simple
            one so you will have to deal with it.
        '''
        tempdir = tempfile.mkdtemp()
        specname = os.path.basename(self.specfile)
        _fd = open(tempdir + '/' + specname, 'w')
        _fd.write(self.text)
        _fd.close()

        _fd = open(spec_patch, 'r')

        thisdir = os.getcwd()
        os.chdir(tempdir)
        code = subprocess.call(['patch', '-p0'], stdin=_fd,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               shell=True)
        _fd.close()
        if code != 0:
            raise RuntimeError(code, "Spec diff failed")

        _fd = open(tempdir + '/' + specname, 'r')
        self.text = _fd.read()
        _fd.close()

        if add_to_source:
            self.add_source(spec_patch, None, changelog=changelog)

        os.chdir(thisdir)
        shutil.rmtree(tempdir)

        return True

    def add_patch(self, patchfile, patchstripe, patchnum, changelog):
        '''
            This will add a given patch into the rpm package.  You must
            specify the patch stripe (the 1 from -p1).

            A unique number is required for the patchnum.
            You can specify one or set it to 'None' and a somewhat random,
            though unique, number will be created for you.

            You must provide a changelog reason for this modification.
        '''
        not_changelog = self.text.split('%changelog\n')[0]
        patch_re = r'^\s*([pP]atch(\d*):\s+(\S+))'
        matches = re.findall(patch_re, not_changelog, re.M)
        # if we are making a number up
        if patchnum is None:
            # if there are no existing patches we start at 0, else at 1
            if not matches:
                patchnum_list = [0]
            else:
                patchnum_list = [1]

            # put all the numbers in a list
            for match in matches:
                if match[1]:
                    patchnum_list.append(int(match[1]))

            # find the biggest num and + 1
            patchnum = (max(patchnum_list) + 1)

        patchname = os.path.basename(patchfile)
        if os.path.isfile(self.basedir + '/../SOURCES/' + patchname):
            os.remove(self.basedir + '/../SOURCES/' + patchname)
        shutil.copy2(patchfile, self.sourcesdir)
        entry = "\nPatch" + str(patchnum) + ":\t" + patchname

        matches = re.findall(patch_re, self.text, re.M)
        if matches:
            patch_entry = matches[-1][0]
        else:
            namematch = re.findall(r'(\s*[nN]ame:\s+.*)', self.text)
            patch_entry = namematch[0]

        self.text = self.text.replace(patch_entry, patch_entry + entry)

        if patchstripe:
            entry = "\n%patch" + str(patchnum) + ' -p' + str(patchstripe)
        else:
            entry = "\n%patch" + str(patchnum) + ' '
        patch_re = r'(%patch\d+\s+-p\d.*)'
        matches = re.findall(patch_re, self.text)
        if matches:
            patch_entry = matches[-1]
        else:
            setup_re = '(%setup.*)'
            matches = re.findall(setup_re, self.text)
            if matches:
                patch_entry = matches.pop()
            else:
                # autosetup doesn't need special patch lines, I think
                setup_re = '(%autosetup.*)'
                matches = re.findall(setup_re, self.text)
                if matches:
                    patch_entry = None
        # if %autopatch we should not add patch lines
        setup_re = '(%autopatch.*)'
        matches = re.findall(setup_re, not_changelog)
        if matches:
            patch_entry = None

        if patch_entry:
            self.text = self.text.replace(patch_entry, patch_entry + entry)

        self.changelog['Added Patch: ' + patchname] = changelog

        return (patchnum, patchname, patchstripe)

    def rm_patch(self, patchname, patchnum, changelog):
        '''
            Prevent a given patch from being applied to the rpm package.

            You can describe the patch by name or by number, but you
            must pick one!  Set the other to 'None'

            You must provide a changelog reason for this modification.
        '''

        if patchname is not None:
            patch_re = r'(\s*[pP]atch(\d+):\s+(' + patchname + ')\n)'
        elif patchnum is not None:
            patch_re = r'(\s*[pP]atch(' + str(patchnum) + r'):\s+(\S+?)\s+?)'
        else:
            raise ValueError('You must specify something I can use here')

        matches = re.findall(patch_re, self.text)
        self.text = self.text.replace(matches[0][0], '\n')

        patchnum = matches[0][1]
        patchname = matches[0][2]

        patch_re = '(%patch' + patchnum + '.+?\n)'
        match_patch = re.findall(patch_re, self.text)
        if match_patch:
            self.text = self.text.replace(match_patch[0], '\n')

        self.changelog['Removed Patch: ' + patchname] = changelog

        return (patchnum, patchname)

    def replace_source(self, sourcename, sourcefile, changelog):
        '''
            Replace a specific source file with a different one
        '''
        if os.path.isfile(self.basedir + '/../SOURCES/' + sourcename):
            os.remove(self.basedir + '/../SOURCES/' + sourcename)

        oldname = os.path.basename(sourcefile)
        shutil.copy2(sourcefile, self.sourcesdir)
        os.rename(self.basedir + '/../SOURCES/' + oldname, self.basedir + '/../SOURCES/' + sourcename)

        self.changelog['Replaced Source: ' + sourcename] = changelog

        return (oldname, sourcename)

    def rm_source(self, sourcename, sourcenum, changelog):
        '''
            Remove a given Source from the package.

            You can describe the Source by name or by number, but you
            must pick one!  Set the other to 'None'

            You must provide a changelog reason for this modification.
        '''
        if sourcename is not None:
            source_re = r'(\s*[sS]ource(\d+):\s+(' + sourcename + ')\n)'
        elif sourcenum is not None:
            source_re = r'(\s*[sS]ource(' + str(sourcenum) + r'):\s+(\S+?)\s+?)'
        else:
            raise ValueError('You must specify something I can use here')

        matches = re.findall(source_re, self.text)
        self.text = self.text.replace(matches[0][0], '\n')

        sourcenum = matches[0][1]
        sourcename = matches[0][2]

        self.changelog['Removed Source: ' + sourcename] = changelog

        return (sourcenum, sourcename)

    def add_source(self, sourcefile, sourcenum, changelog):
        '''
            Add a source file to the rpm spec.

            A unique number is required for the sourcenum.
            You can specify one or set it to 'None' and a somewhat random,
            though unique, number will be created for you.

            You must provide a changelog reason for this modification.
        '''
        not_changelog = self.text.split('%changelog\n')[0]
        source_re = r'([sS]ource(\d*):\s+(\S+))'
        matches = re.findall(source_re, not_changelog)
        # if we are making a number up
        if sourcenum is None:
            # if there are no existing sources we start at 0, else at 1
            if not matches:
                sourcenum_list = [0]
            else:
                sourcenum_list = [1]

            # put all the numbers in a list
            for match in matches:
                if match[1]:
                    sourcenum_list.append(int(match[1]))

            # find the biggest num and + 1
            sourcenum = (max(sourcenum_list) + 1)

        sourcename = os.path.basename(sourcefile)
        if os.path.isfile(self.basedir + '/../SOURCES/' + sourcename):
            os.remove(self.basedir + '/../SOURCES/' + sourcename)
        shutil.copy2(sourcefile, self.sourcesdir)
        entry = "\nSource" + str(sourcenum) + ":\t" + sourcename

        matches = re.findall(source_re, not_changelog)
        if matches:
            source_entry = matches[-1][0]
        else:
            namematch = re.findall(r'(\s*[nN]ame:\s+.+)', self.text)
            source_entry = namematch[0]

        self.text = self.text.replace(source_entry, source_entry + entry + "\n")
        self.text = self.text.replace(entry + '\n%endif\n', '\n%endif\n' + entry)

        self.changelog['Added Source: ' + sourcename] = changelog

        return (sourcenum, sourcename)

    def __add_changelog(self):
        '''
            Record the changes in the changelog
        '''
        if self.changelog_done is True:
            return
        now = datetime.datetime.now().strftime('%a %b %d %Y ')
        changelog_text = '%changelog\n* ' + now + self.changelog_user + '\n'
        for action in self.changelog.keys():
            changelog_text = changelog_text + '- ' + action + '\n'
            changelog_text = changelog_text + '-->  ' + self.changelog[action]
            changelog_text = changelog_text + '\n'

        changelog_text = changelog_text + '\n'

        self.text = self.text.replace('%changelog\n', changelog_text, 1)

        self.changelog_done = True

        return True

    def save(self):
        '''
            Write out the specfile with changes
        '''
        self.__add_changelog()
        _fd = open(self.specfile, 'w')
        _fd.write(self.text)
        _fd.close()

        return True
