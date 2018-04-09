#!/usr/bin/env python3
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
import os


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
    return [
        'passwords.txt.example',
        'config.default.ini',
        'config.example.ini',
    ]


def get_data_files():
    return []


def find_version():
    with open(os.path.join("sbws", "__init__.py")) as fp:
        for line in fp:
            if "version" in line.strip():
                version = line.split("=", 1)[1].strip().strip("'")
                return version


setup(
    name='sbws',
    version=find_version(),
    description='Simple Bandwidth Scanner',
    long_description=long_description,
    author='Matt Traudt',
    author_email='pastly@torproject.org',
    license='CC0',
    # https://packaging.python.org/tutorials/distributing-packages/#id48
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',
    ],
    packages=find_packages(),
    package_data={
        'sbws': get_package_data(),
    },
    data_files=get_data_files(),
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
        'filelock',
    ],
    extras_require={
        'dev': [],
        'test': ['tox', 'pytest', 'pytest-cov'],
        # recommonmark: to make sphinx render markdown
        'doc': ['sphinx', 'recommonmark'],
    },
)
