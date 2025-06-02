#!/usr/bin/env python3
"""
Parse ThermoML XML files in the local ThermoML Archive mirror.
"""
import pandas as pd
import glob
import os
import argparse
from thermopyl import Parser
from thermopyl.utils import build_pandas_dataframe

def main():
    # Parse command-line arguments.
    parser = argparse.ArgumentParser(description='Build a Pandas dataset from local ThermoML Archive mirror.')
    parser.add_argument('--journalprefix', dest='journalprefix', metavar='JOURNALPREFIX', type=str, default=None,
                        help='journal prefix to use in globbing *.xml files')
    parser.add_argument('--path', dest='path', metavar='path', type=str, default=None,
                        help='path to local ThermoML Archive mirror')
    args = parser.parse_args()

    # Get location of local ThermoML Archive mirror.
    XML_PATH = os.path.join(os.path.expanduser("~"), '.thermoml')  # DEFAULT LOCATION
    if args.path is not None:
        XML_PATH = args.path
    elif 'THERMOML_PATH' in os.environ:
        XML_PATH = os.environ["THERMOML_PATH"]

    # Get path for XML files.
    pattern = f"{args.journalprefix}*.xml" if args.journalprefix else "*.xml"
    filenames = glob.glob(os.path.join(XML_PATH, pattern))

    if not filenames:
        print(f"No XML files found in {XML_PATH} matching pattern '{pattern}'.")
        return 1

    # Process data.
    data, compound_dict = build_pandas_dataframe(filenames)
    data.to_hdf(os.path.join(XML_PATH, 'data.h5'), key='data')
    compound_dict.to_hdf(os.path.join(XML_PATH, 'compound_name_to_formula.h5'), key='data')
    print(f"Wrote {len(data)} records to {os.path.join(XML_PATH, 'data.h5')}")
    print(f"Wrote compound dictionary to {os.path.join(XML_PATH, 'compound_name_to_formula.h5')}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
