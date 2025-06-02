#!/usr/bin/env python3
"""
Update local mirror of the ThermoML Archive.
"""
import thermopyl

def main():
    thermopyl.update_archive()

if __name__ == '__main__':
    raise SystemExit(main())

