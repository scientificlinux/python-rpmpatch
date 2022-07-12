Summary: Tools for automatically customizing a source rpm
Name: python-rpmpatch
Version: 0.0.3
Release: 4.sl%{rhel}.1
Source0: python-rpmpatch.tar.gz
License: GPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Pat Riehecky <riehecky@fnal.gov>
Url: http://www.scientificlinux.org/maillists
Requires: python >= 2.4
Requires: hardlink rpm-python rpmdevtools rpm-build

%description
Tools for making rpm customizations consistant as a program will be performing
the edits automatically based on a defined set of parameters.

There is a fairly extensive feature set packaged.

%prep
%setup -n %{name}

%build
python setup.py build

%install
python setup.py install -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

mkdir -p $RPM_BUILD_ROOT/usr/share/doc/python-rpmpatch/
cp -r docs/* $RPM_BUILD_ROOT/usr/share/doc/python-rpmpatch/
find $RPM_BUILD_ROOT/usr/share/doc/python-rpmpatch/ -type f -exec chmod 644 {} \;
find $RPM_BUILD_ROOT/usr/share/doc/python-rpmpatch/ -type d -exec chmod 755 {} \;

mkdir -p $RPM_BUILD_ROOT/usr/bin/
cp bin/* $RPM_BUILD_ROOT/usr/bin/
chmod 755 $RPM_BUILD_ROOT/usr/bin/*

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
/usr/bin/*
%{python_sitelib}/*
%doc /usr/share/doc/python-rpmpatch/

%changelog
* Mon Aug 22 2015 Pat Riehecky <riehecky@fnal.gov> 0.0.3-1.sl
- now with 'remove source'

* Thu Jan 29 2015 Pat Riehecky <riehecky@fnal.gov> 0.0.2-4.sl
- now supports optional dist tag detection and manipulation

* Tue Jan 27 2015 Pat Riehecky <riehecky@fnal.gov> 0.0.2-3.sl
- Better documentation, fixed minor logic error

* Tue Jun 26 2013 Pat Riehecky <riehecky@fnal.gov> 0.0.2-1.sl
- Error messages are now much more accurate

* Tue Jan 15 2013 Pat Riehecky <riehecky@fnal.gov> 0.0.2-0.sl
- non full paths in config are now relative to the config file
- now works on python 2.4 ie SL5

* Mon Jan 14 2013 Pat Riehecky <riehecky@fnal.gov> 0.0.1-0.sl6
- Initial build
