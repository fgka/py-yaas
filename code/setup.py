#!/usr/bin/env python
#
"""
Setup for this package
"""
import io
import os

import itertools

from setuptools import find_packages, setup

# Package meta-data.
NAME = "py_yaas_playground"
DESCRIPTION = """
"""
LICENSE = "Proprietary"
URL = "https://github.com/fgka/py-yaas"
EMAIL = "gkandriotti@google.com"
AUTHOR = "Gustavo Kuhn Andriotti"
# https://devguide.python.org/versions/#branchstatus
REQUIRES_PYTHON = ">=3.10.0"  # End-of-life: 2026-10 (checked on 2022-09-01)
VERSION = 1.00
CLASSIFIERS = [
    # Trove classifiers
    # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
    "License :: Other/Proprietary License",
    "Development Status :: 5 - Production/Stable",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Operating System :: OS Independent",
    "Environment :: Console",
]

# What packages are required for this module to be executed?
# pylint: disable=consider-using-with
INSTALL_REQUIRED = []
with io.open("requirements.txt", encoding="UTF-8") as f:
    for line in f.readlines():
        INSTALL_REQUIRED.append(line.strip())

DEBUG_REQUIRED = [
    "ipython>=8.4.0",
]

CODE_QUALITY_REQUIRED = [
    "black>=22.6",
    "deepdiff>=5.8.1",
    "mock>=4.0.3",
    "nose>=1.3.7",
    "pudb>=2022.1.2",
    "pylama>=8.4.1",
    "pylama-pylint>=3.1.1",
    "pylint>=2.14.5",
    "pytest>=7.1.2",
    "pytest-cov>=3.0.0",
    "pytest-mock>=3.8.2",
    "pytest-pudb>=0.7.0",
    "pytest-pylint>=0.18.0",
    "pytest-xdist>=2.5.0",
    "vulture>=2.5",
]

SETUP_REQUIRED = [
    "pytest-runner>=6.0.0",
]

# What packages are required for this module's docs to be built
DOCS_REQUIRED = [
    "diagrams>=0.21.1",
    "Sphinx>=5.1.1",
]

EXTRA_REQUIRED = {
    "tools": DEBUG_REQUIRED,
    "docs": DOCS_REQUIRED,
    "tests": CODE_QUALITY_REQUIRED,
    "setup": SETUP_REQUIRED,
}
ALL_REQUIRED = list(itertools.chain(*EXTRA_REQUIRED.values(), INSTALL_REQUIRED))
EXTRA_REQUIRED["all"] = ALL_REQUIRED

HERE = os.path.abspath(os.path.dirname(__file__))

# Long description
try:
    with io.open(os.path.join(HERE, "README.md"), encoding="UTF-8") as f:
        LONG_DESCRIPTION = "\n" + f.read()
except FileNotFoundError:
    LONG_DESCRIPTION = DESCRIPTION

# Long license
try:
    with io.open(os.path.join(HERE, "LICENSE"), encoding="UTF-8") as f:
        LONG_LICENSE = "\n" + f.read()
except FileNotFoundError:
    LONG_LICENSE = LICENSE

# Load the package's __version__.py module as a dictionary.
ABOUT = {}
if not VERSION:
    with open(os.path.join(HERE, NAME, "__version__.py"), encoding="UTF-8") as f:
        # pylint: disable=exec-used
        exec(f.read(), ABOUT)
else:
    ABOUT["__version__"] = VERSION


# Where the magic happens:
setup(
    name=NAME,
    version=ABOUT["__version__"],
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    install_requires=INSTALL_REQUIRED,
    setup_requires=SETUP_REQUIRED,
    extras_require=EXTRA_REQUIRED,
    include_package_data=True,
    license=LONG_LICENSE,
    packages=find_packages(exclude=("tests",)),
    classifiers=CLASSIFIERS,
)
