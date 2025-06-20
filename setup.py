"""ThermoPyl: Python tools for ThermoML
"""

import os
import sys
import glob
import traceback
import numpy as np
from os.path import join as pjoin
from setuptools import setup, find_packages
try:
    sys.dont_write_bytecode = True
    sys.path.insert(0, '.')
    from basesetup import write_version_py, CompilerDetection, check_dependencies
finally:
    sys.dont_write_bytecode = False


if '--debug' in sys.argv:
    sys.argv.remove('--debug')
    DEBUG = True
else:
    DEBUG = False

# #########################
VERSION = '1.0.1'
ISRELEASED = True
__version__ = VERSION
# #########################

setup(
    name="thermopyl",
    author="Kyle Beauchamp",
    author_email="kyle.beauchamp@choderalab.org",
    description="Python tools for ThermoML",
    long_description=(
        open("README.md").read() if os.path.exists("README.md")
        else "Python tools for ThermoML"
    ),
    long_description_content_type="text/markdown",
    version=__version__,
    url="https://github.com/choderalab/thermopyl",
    platforms=["Linux", "Mac OS-X", "Unix", "Windows"],
    python_requires=">=3.7",
    packages=find_packages(),
    package_data={"thermopyl": ["data/*"]},
    zip_safe=False,
    install_requires=[
        "six",
        "pandas",
        "pyxb==1.2.4",
        "feedparser",
        "tables",
    ],
    entry_points={
        "console_scripts": [
            "thermoml-update-mirror = thermopyl.scripts.update_archive:main",
            "thermoml-build-pandas = thermopyl.scripts.parse_xml:main",
        ]
    },
    license="GPL-2.0-or-later",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Chemistry",
    ],
)
