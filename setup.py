from distutils.core import setup

setup(
    name='rpmpatch',
    version='0.0.3',
    author='Pat Riehecky',
    author_email='riehecky@fnal.gov',
    packages=['rpmpatch'],
    scripts=[],
    url='http://www.scientificlinux.org/maillists/',
    license='LICENSE',
    description='Tools for automatically customizing a source rpm',
    long_description=open('README.md').read(),
    requires=[
        "python",
    ],
)
