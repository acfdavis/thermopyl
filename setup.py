"""ThermoPyl: Python tools for ThermoML
"""

import os
import sys
import glob
import traceback
import numpy as np
from os.path import join as pjoin
from setuptools import setup, find_packages
from devtools.versioning import write_version_py
from devtools.compiler_detection import CompilerDetection
from devtools.check_dependencies import check_dependencies
from devtools.static_library import StaticLibrary

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Example usage of versioning utility (customize as needed)
VERSION = '1.0.1'
ISRELEASED = True
write_version_py(VERSION, ISRELEASED, filename=os.path.join('thermopyl', 'version.py'))

setup(
    name="thermopyl",
    author="Kyle Beauchamp",
    author_email="kyle.beauchamp@choderalab.org",
    description="Python tools for ThermoML",
    long_description=long_description,
    long_description_content_type="text/markdown",
    version=VERSION,
    url="https://github.com/choderalab/thermopyl",
    platforms=["Linux", "Mac OS-X", "Unix", "Windows"],
    classifiers=[
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Development Status :: 4 - Beta",
        "Topic :: Software Development",
        "Topic :: Scientific/Engineering",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
    ],
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
    # ext_modules=[], # Add C/C++ extensions here if needed, using StaticLibrary or Extension
)
