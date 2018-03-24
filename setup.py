#!/usr/bin/env python3
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
import os
import re

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()


def get_package_data():
    # Example that grabs all *.ini files in the cwd and all files in foo/bar
    # other_files = ['*.ini']
    # for r, _, fs in os.walk(os.path.join(here, 'foo', 'bar')):
    #     for f in fs:
    #         other_files.append(os.path.join(r, f))
    # return other_files
    return []


def find_version(fname):
    with open(fname, 'rt') as fd:
        contents = fd.read()
        match = re.search(r"^VERSION = ['\"]([^'\"]*)['\"]", contents, re.M)
        if match:
            return match.group(1)
        raise RuntimeError('Unable to find version string')


setup(
    name='sbws',
    version=find_version('sbws/__main__.py'),
    description='Simple Bandwidth Scanner',
    long_description=long_description,
    author='Matt Traudt',
    author_email='pastly@torproject.org',
    # license='MIT',
    # https://packaging.python.org/tutorials/distributing-packages/#id48
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
    ],
    packages=find_packages(),
    # package_data={
    #     'foo': get_package_data(),
    # },
    keywords='',
    python_requires='>=3.5',
    # test_suite='test',
    entry_points={
        'console_scripts': [
            'sbws = sbws.__main__:main',
        ]
    },
    install_requires=[
        'stem',
        'pysocks',
    ],
    extras_require={
        'dev': [],
        'test': [],
        'doc': ['sphinx'],
    },
)
