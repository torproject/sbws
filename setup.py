#!/usr/bin/env python3
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
import os


here = os.path.abspath(os.path.dirname(__file__))


def long_description():
    with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        return f.read()


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
    ]


def get_data_files():
    return [('examples', [os.path.join('examples', 'config.example.ini')])]


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
    long_description=long_description(),
    long_description_content_type="text/markdown",
    author='Matt Traudt, juga',
    author_email='{pastly, juga}@torproject.org',
    license='CC0',
    url="https://gitweb.torproject.org/sbws.git",
    classifiers=[
        'Development Status :: 4 - Beta',
        "Environment :: Console",
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: System :: Networking',
    ],
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'sbws': get_package_data(),
    },
    data_files=get_data_files(),
    keywords='tor onion bandwidth measurements scanner relay circuit',
    python_requires='>=3.4.5',
    entry_points={
        'console_scripts': [
            'sbws = sbws.sbws:main',
        ]
    },
    install_requires=[
        'stem>=1.7.0',
        'requests[socks]',
    ],
    extras_require={
        # vulture: find unused code
        'dev': ['flake8', 'vulture'],
        'test': ['tox', 'pytest', 'coverage'],
        # recommonmark: to make sphinx render markdown
        'doc': ['sphinx', 'recommonmark', 'pylint'],
    },
)
