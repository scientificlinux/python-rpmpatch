'''
    This class is derived from SimpleRPM and won't run on non SRPMs
'''

import os
import rpm
import subprocess

from SimpleRPM import SimpleRPM


class SourcePackage(SimpleRPM):
    '''
        Takes in all the tools from SimpleRPM and limits its scope to
        source rpms.

        Provides a few new tools:
    '''
    def __init__(self, thisfile):
        '''
            Raises RuntimeError if not a SRPM
        '''
        SimpleRPM.__init__(self, thisfile)
        if not self.isSRPM():
            raise RuntimeError('Package is not a SRPM ' + thisfile)

        self.topdir = rpm.expandMacro('%_topdir')

        # patches are provided in reverse order, fix it up
        self.patches = self.hdr[rpm.RPMTAG_PATCH]
        self.patches.reverse()

        # sourcefiles are provided in reverse order, fix it up
        self.sourcefiles = self.hdr[rpm.RPMTAG_SOURCE]
        self.sourcefiles.reverse()

        self.specfile = None

    def install(self):
        '''
            I've not been able to figure out how to get the python rpm library
             to install source rpms as a non-root user.....
            So this installs the rpm with subprocess
        '''
        __p = subprocess.Popen(['rpm', '-i', '--quiet', self.getFullPath()],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        result = os.waitpid(__p.pid, 0)
        return_code = result[1]
        if return_code != 0:
            raise RuntimeError("Can't install " + self.getFullPath())

        for fileinrpm in self.getFiles():
            if not fileinrpm.endswith('.spec'):
                continue

            if os.path.isfile(self.topdir + '/SPECS/' + fileinrpm):
                self.specfile = self.topdir + '/SPECS/' + fileinrpm

        if self.specfile is None:
            raise RuntimeError("Missing spec in " + self.getFilename())
