#!/usr/bin/env python3
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
import os


here = os.path.abspath(os.path.dirname(__file__))

# Causes the lint Travis builds to fail for some reason, so just going to
# remove the long description for now.
# with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
#         long_description = f.read()


def get_package_data():
    # Example that grabs all *.ini files in the cwd and all files in foo/bar
    # other_files = ['*.ini']
    # for r, _, fs in os.walk(os.path.join(here, 'foo', 'bar')):
    #     for f in fs:
    #         other_files.append(os.path.join(r, f))
    # return other_files
    return [
        'config.default.ini',
        'config.log.default.ini',
        'config.example.ini',
    ]


def get_data_files():
    return []


def find_version():
    with open(os.path.join("sbws", "__init__.py")) as fp:
        for line in fp:
            if "__version__" in line.strip():
                version = line.split("=", 1)[1].strip().strip("'")
                return version


setup(
    name='sbws',
    version=find_version(),
    description='Simple Bandwidth Scanner',
    # long_description=long_description,
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
    include_package_data=True,
    package_data={
        'sbws': get_package_data(),
    },
    data_files=get_data_files(),
    keywords='',
    python_requires='>=3.4',
    # test_suite='test',
    entry_points={
        'console_scripts': [
            'sbws = sbws.sbws:main',
        ]
    },
    install_requires=[
        'stem==1.6.0.dev0',
        'requests[socks]',
    ],
    dependency_links=[
        "git+https://git.torproject.org/stem.git#egg=stem-1.6.0.dev0",
    ],
    extras_require={
        'dev': ['flake8'],
        'test': ['tox', 'pytest', 'coverage'],
        # recommonmark: to make sphinx render markdown
        'doc': ['sphinx', 'recommonmark'],
    },
)
