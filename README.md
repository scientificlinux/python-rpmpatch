# Python RPM AutoPatch

Basically this is a toolset for doing automated customization of a given rpm.

The idea is to keep it simple and easy to back up, while also making it simple
to track what changed and reproduce the changes from the source archive.

The patchsrpm.py script will provide a sample of how to use these libraries. It
also provides instructions on how to build a configuration file to begin
working with this toolset right away.


## Setup

We strongly recommend using virtual environment. Because rpm is system
dependent python package, we introduced, simple `create_and_fix_venv.sh`
scripts that works on EL8 and EL9 systems. The whole setup is as simple as
```
sudo yum install -y python3-virtualenv
./create_and_fix_venv.sh
```

## Usage

Firstly let's activate virtualenv
```
. venv/bin/activate
```

Then

## Creating patching rules


## Example patching rule - for firefox


## History

This project was originaly developed by Scientific Linux Developers, that we
would like to thanks from very bottom of our hearts. We migrated it
for python3 and add some hacks/fixes.

It's now used in EuroLinux 8 and 9 pipeline/GaiaBuildSystem for some packages
like firefox or thunderbird that have very stable set of patches and changes
that are required to build them.
