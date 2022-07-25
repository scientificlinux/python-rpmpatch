#pylint: disable=line-too-long
'''
   The idea here was to make it really easy to do some basic stuff
   with an RPM in a much cleaner mode than the default 'rpm' object
   will allow.  The RPM object is able to install and remove packages
   which requires it to have way more functionality than I need for
   simply looking at a package.  This object has its goal in being
   far more simple.

   So it doesn't do a whole lot.... but what it does it does cleanly
'''
import difflib
import os
import re
import rpm

try:
    import rpmUtils.miscutils
except:
    raise ImportError('rpmUtils.miscutils (which ships with yum) is required')

class SimpleRPM(object):
    '''
       This is just a simple class that abstracts away
       some of the more frustrating things to get out of
       an RPM.  Not that it is hard, it is just ugly.

       If anything goes wrong this class throws an
       IOError.

       I've overloaded:

             != == >= <= < > and 'in'

             for > and <   it compares version info if
                            the package name is the same

             for == and !=  it compares bit for bit

             <= and >=  exist and work as a union of the above
                         but that is a bit weird so....

             You can even pass in a filename rather than a SimpleRPM object
              if you want, it will then create the necessary object for
              shorterm use so your code can be even more simple.

             NOTE: the RPM name MUST MATCH or you will get problems
                   so check that before you try to compare, you've been warned

             the 'in' construct checks files within the rpm

       Useful Methods:
        getFullPath()
        getFilename()
        getFileSize()
        getFiles()
        isDebuginfo()
        isSRPM()
        whatSRPM()
        packageName()
        packageFullVersion()
        packageVersion()
        packageRelease()
        packageArch()
        packageBuildHost()
        isSigned()
        isSignedBy()
        packageKeys()
    '''
    def __init__(self, thisfile):
        if not os.path.isfile(thisfile):
            raise IOError('No such file ' + thisfile)

        self.full_path = ''
        self.filename = ''
        self.filesize = ''
        self._set_file_info(thisfile)

        # I know these can be determined in 'real time'
        # but since they might throw exceptions,
        # it seemed nicer to do the work now and store the results
        # so that later calls a certian not to fail
        # you can catch exceptions all at once and be sure that
        # if you get an object back that it won't barf on you later
        self.hdr = self.__open_hdr()

        # these require a bit more work than the rest
        self.is_debuginfo = self.__is_debuginfo()
        self.is_signed = self.__is_signed()
        self.package_keys = self.__get_keys()

    def __str__(self):
        return self.getFilename()

    @staticmethod
    def __temp_rpm(somefile):
        '''
           This creates a short lived SimpleRPM object
           for use in the comparison operators
        '''
        if not os.path.isfile(somefile):
            raise IOError("Can't find " + somefile + " for compare")
        return SimpleRPM(somefile)

    def __contains__(self, key):
        '''x in object, checks package filenames'''
        if key in self.hdr[rpm.RPMTAG_FILENAMES]:
            return True
        else:
            return False

    def __vercmp(self, other):
        '''Stolen outright from rpmdev-vercmp'''
        (e_1, v_1, r_1) = rpmUtils.miscutils.stringToVersion(self.getFullPath())
        (e_2, v_2, r_2) = rpmUtils.miscutils.stringToVersion(other.getFullPath())
        # stringToVersion in yum < 3.1.2 may return numeric (non-string)
        # Epochs, and labelCompare does not like that.
        if e_1 is not None:
            e_1 = str(e_1)
        if e_2 is not None:
            e_2 = str(e_2)

        rcode = rpm.labelCompare((e_1, v_1, r_1), (e_2, v_2, r_2))
        if rcode > 0:
            # return 1 if self > other
            return 1
        elif rcode < 0:
            # return -1 if self < other
            return -1
        elif rcode == 0:
            # return 0 if self == other
            return 0

    def __lt__(self, other):
        '''
            This lets us use nice simple comparison operators like <
        '''
        # has to be this kind of object
        if not isinstance(other, SimpleRPM):
            if isinstance(other, str):
                otherrpm = self.__temp_rpm(other)
            else:
                raise IOError("What is "+ other)
        else:
            otherrpm = other

        # has to be this package
        if self.packageName() != otherrpm.packageName():
            return NotImplemented

        result = self.__vercmp(otherrpm)

        if result == -1:
            return True
        else:
            return False

    def __gt__(self, other):
        '''
            This lets us use nice simple comparison operators like >
        '''
        # has to be this kind of object
        if not isinstance(other, SimpleRPM):
            if isinstance(other, str):
                otherrpm = self.__temp_rpm(other)
            else:
                raise IOError("What is " + other)
        else:
            otherrpm = other

        # has to be this package
        if self.packageName() != otherrpm.packageName():
            return NotImplemented

        result = self.__vercmp(otherrpm)

        if result == 1:
            return True
        else:
            return False

    def __le__(self, other):
        '''
           This lets us use nice simple comparison operators like <=
           I'm not sure when it would make sense to do this, but here it is
        '''
        # has to be this kind of object
        if not isinstance(other, SimpleRPM):
            if isinstance(other, str):
                otherrpm = self.__temp_rpm(other)
            else:
                raise IOError("What is " + other)
        else:
            otherrpm = other

        # has to be this package
        if self.packageName() != otherrpm.packageName():
            return NotImplemented

        result = self.__vercmp(otherrpm)

        if result == -1:
            return True
        elif result == 0:
            return self.__eq__(otherrpm)
        else:
            return False

    def __ge__(self, other):
        '''
           This lets us use nice simple comparison operators like >=
           I'm not sure when it would make sense to do this, but here it is
        '''
        # has to be this kind of object
        if not isinstance(other, SimpleRPM):
            if isinstance(other, str):
                otherrpm = self.__temp_rpm(other)
            else:
                raise IOError("What is " + other)
        else:
            otherrpm = other

        # has to be this package
        if self.packageName() != otherrpm.packageName():
            return NotImplemented

        result = self.__vercmp(otherrpm)

        if result == 1:
            return True
        elif result == 0:
            return self.__eq__(otherrpm)
        else:
            return False

    def __eq__(self, other):
        '''
           For == we have a bit more to say than with
           the other operators.
           You can pass in a path to a RPM or a SimpleRPM object
           The files must be exactly identical down to the
           bits or this returns false
        '''
        # has to be this kind of object
        if not isinstance(other, SimpleRPM):
            if isinstance(other, str):
                otherrpm = self.__temp_rpm(other)
            else:
                raise IOError("What is " + other)
        else:
            otherrpm = other

        # has to be this package
        if self.packageName() != otherrpm.packageName():
            return NotImplemented

        # different size means different
        if self.getFileSize() != otherrpm.getFileSize():
            return False

        self_contains = open(self.getFullPath(), 'r').readlines()
        other_contains = open(otherrpm.getFullPath(), 'r').readlines()
        # python's built in difflib module, returns [] when things are the same
        differences = list(difflib.unified_diff(self_contains, other_contains))
        if differences:
            return False
        else:
            return True

    def __ne__(self, other):
        '''
            For != see __eq__, this just reverses it
        '''
        # has to be this kind of object
        if not isinstance(other, SimpleRPM):
            if isinstance(other, str):
                otherrpm = self.__temp_rpm(other)
            else:
                raise IOError("What is " + other)
        else:
            otherrpm = other

        # has to be this package
        if self.packageName() != otherrpm.packageName():
            return NotImplemented

        # different size means different
        if self.getFileSize() != otherrpm.getFileSize():
            return False

        return not self.__eq__(otherrpm)

    def _set_file_info(self, thisfile):
        '''
            Set some basic statistics about the file in question
        '''
        self.full_path = os.path.abspath(thisfile)
        self.filename = os.path.basename(self.full_path)
        self.filesize = os.path.getsize(thisfile)

    def getFullPath(self):
        '''
            return the full path to thisfile
        '''
        return self.full_path

    def getFilename(self):
        '''
            return the filename of thisfile
        '''
        return self.filename

    def getFileSize(self):
        '''
            return the file size of thisfile
        '''
        return self.filesize

    def getFiles(self):
        '''
            return the files in this rpm
        '''
        return self.hdr[rpm.RPMTAG_FILENAMES]

    def __open_hdr(self):
        '''
            This method tries to open an rpm and returns the headers of
            the transaction set resulting from it.
        '''
        try:
            _fd = os.open(self.getFullPath(), os.O_RDONLY)
            _ts = rpm.TransactionSet()
            hdr = _ts.hdrFromFdno(_fd)
            os.close(_fd)
            return hdr
        except:
            raise IOError('Something wrong rpm ' + self.getFullPath())

    def isDebuginfo(self):
        '''
            Is this file a debuginfo rpm?
            Returns True or False depending
        '''
        return self.is_debuginfo

    def __is_debuginfo(self):
        '''
            Does the actual parsing of the rpm so we don't have to later.
            Returns True or False depending
        '''
        if self.isSRPM():
            return False
        elif self.hdr['PROVIDENAME']:
            for provide in self.hdr['PROVIDENAME']:
                match_obj = re.search('debuginfo.+', provide)
                if match_obj:
                    return True
                match_obj = re.search(r'\.debug', provide)
                if match_obj:
                    return True
            return False
        else:
            raise IOError('Something wrong rpm ' + self.getFullPath())

    def isSRPM(self):
        '''Returns True or False depending'''
        if self.hdr[rpm.RPMTAG_SOURCERPM]:
            return False
        else:
            return True

    def whatSRPM(self):
        '''Returns the name of the sourcerpm for this RPM'''
        if self.isSRPM():
            return self.getFilename()
        else:
            return self.hdr[rpm.RPMTAG_SOURCERPM]

    def packageBuildDate(self):
        '''Returns a datetime object with the build time of this RPM'''
        return self.hdr[rpm.RPMTAG_BUILDTIME]

    def packageName(self):
        '''Returns the package name of a given RPM'''
        return self.hdr[rpm.RPMTAG_NAME]

    def packageFullVersion(self):
        '''Returns the package version (and release) of a given RPM'''
        data = self.hdr[rpm.RPMTAG_VERSION] + '-' + self.hdr[rpm.RPMTAG_RELEASE]
        return data

    def packageVersion(self):
        '''Returns the package version of a given RPM'''
        return self.hdr[rpm.RPMTAG_VERSION]

    def packageRelease(self):
        '''Returns the package release of a given RPM'''
        return self.hdr[rpm.RPMTAG_RELEASE]

    def packageArch(self):
        '''Returns the package arch of a given RPM'''
        return self.hdr[rpm.RPMTAG_ARCH]

    def packageBuildHost(self):
        '''Returns the buildhost of a given RPM'''
        return self.hdr[rpm.RPMTAG_BUILDHOST]

    def isSigned(self):
        '''Returns True if the package is signed.'''
        return self.is_signed

    def packageKeys(self):
        '''Returns a tuple of keyIDs used to sign this package'''
        return self.package_keys

    def isSignedBy(self, keys):
        '''
            Returns True/False if the rpm is signed by one of
            the keys passed in
        '''
        signedby = set(self.packageKeys())
        keylist = set(keys)
        if signedby.intersection(keylist):
            return True
        return False

    def __is_signed(self):
        '''
            Returns True if the package is signed.
            The acutal work is done here
        '''
        # these next lines shamelessly taken from rpmdev-checksig
        # minor adjustments to make them run here, but no logic change
        string = '%|DSAHEADER?{%{DSAHEADER:pgpsig}}:{%|RSAHEADER?{%{RSAHEADER:pgpsig}}:{%|SIGGPG?{%{SIGGPG:pgpsig}}:{%|SIGPGP?{%{SIGPGP:pgpsig}}:{(none)}|}|}|}|'
        siginfo = self.hdr.sprintf(string)
        if siginfo == '(none)':
            return False
        else:
            return True

    def __get_keys(self):
        '''
            Returns a tuple of keyIDs used to sign this package
            The acutal work is done here
        '''
        if not self.isSigned():
            return tuple()

        # these next lines shamelessly taken from rpmdev-checksig
        # minor adjustments to make them run here, but no logic change
        # I know I'm not using sigtype or sigdate but again
        # this is borrowed code from rpmdev-checksig where I'm trying not to
        # make any changes unless I must
        string = '%|DSAHEADER?{%{DSAHEADER:pgpsig}}:{%|RSAHEADER?{%{RSAHEADER:pgpsig}}:{%|SIGGPG?{%{SIGGPG:pgpsig}}:{%|SIGPGP?{%{SIGPGP:pgpsig}}:{(none)}|}|}|}|'
        siginfo = self.hdr.sprintf(string)
        sigtype, sigdate, sigid = siginfo.split(',')
        return tuple(sigid[-8:].upper())

