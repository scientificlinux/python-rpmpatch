# Python RPM AutoPatch

Basically, this is a toolset for doing automated customization of a given rpm.

The idea is to keep it simple and easy to back up, while also making it simple
to track what changed and reproduce the changes from the source archive.

The patchsrpm.py script will provide a sample of how to use these libraries. It
also provides instructions on how to build a configuration file to begin
working with this toolset right away.


## Setup
Firstly install rpm-build and development packages

```
sudo yum install -y rpm-build @development
```

We strongly recommend using a virtual environment. Because rpm is system
dependent python package, we introduced, a simple `create_and_fix_venv.sh`
scripts that work (at least) on EL8 and EL9 systems. The whole setup is as
simple as
```
sudo dnf install -y rpm-build
sudo dnf install -y python3-virtualenv
./create_and_fix_venv.sh
```

**Note: this step is optional**.

## Usage

Download the package that you want to fix
```bash
wget https://your.mirror.example.net/sources/9/x86_64/appstream/Packages/f/firefox-91.9.1-1.el9_0.src.rpm -P srpms
```

Optionally activate virtualenv
```
. venv/bin/activate
```

To patch, you need a configuration directory. **Example configuration**
directory is placed inside `configs` directory, that has sample hierarchy for
EuroLinux 6 and 9.

```bash
./rpmpatch/patchsrpm.py --keep_dist --config=configs/el9/ srpms/firefox-91.9.1-1.el9_0.src.rpm
```

Congratulations You have nicely patched source rpm!

**Note:**

With `--keep_dist` the patcher will produce `firefox-91.9.1-1.el9_0.src.rpm`,
without it it will produce srpm with distag used by your distribution/system.


## Getting help

- Invoking `./rpmpatch/patchsrpm.py` without argument will provide options and examples.
- Invoking `./rpmpatch/patchsrpm.py --sampleconfig` prints sample config that
  has all necessary information to create the autopatching process
- In case of a bug/problem or if You need help GitHub issues are very welcome :)!

## Tests

There are very simple smoke tests. **Note that smoke tests use
`rpmdev-wipetree` command during executions**. The tests are bats
based. 

Installing bats on Enterprise Linux 8/9:

```bash
sudo dnf install -y epel-release
sudo dnf install -y bats
```

Running tests
```
bats smoke-tests.bats
```

## History

This project was originally developed by Scientific Linux Developers, which we
would like to thanks. We migrated it to Python 3 and add developed it a little
further.
