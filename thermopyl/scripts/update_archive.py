#!/usr/bin/env python3
"""
Update local mirror of the ThermoML Archive.
"""
from thermopyl.core.update_archive import update_archive

def main():
    
    update_archive()

if __name__ == '__main__':
    raise SystemExit(main())
