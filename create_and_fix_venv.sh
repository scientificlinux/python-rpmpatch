#!/usr/bin/env bash


virtualenv -p /usr/bin/python3 venv
. venv/bin/activate
pip install -r ./requirements.txt
#
# This sucks - we have to manually copy rpm package :/ to venv
#

echo "Installing rpm from host site-packages"
cp -Rv /usr/lib64/python3*/site-packages/rpm ./venv/lib64/python3*/site-packages
echo "Installing libdnf from host site-packages"
cp -Rv /usr/lib64/python3*/site-packages/libdnf ./venv/lib64/python3*/site-packages
echo "Installing libcomps from host site-packages"
cp -Rv /usr/lib64/python3*/site-packages/libcomps ./venv/lib64/python3*/site-packages
echo "Installing gpg from host site-packages"
cp -Rv /usr/lib64/python3*/site-packages/gpg ./venv/lib64/python3*/site-packages
echo "Installing hawkey from host site-packages"
cp -Rv /usr/lib64/python3*/site-packages/hawkey ./venv/lib64/python3*/site-packages
echo "Installing dnf from host site-packages"
cp -Rv /usr/lib/python3*/site-packages/dnf* ./venv/lib64/python3*/site-packages
