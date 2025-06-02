import os
from typing import List

def find_packages(base_dir: str = 'thermopyl', prefix: str = 'thermopyl') -> List[str]:
    """Find all Python packages in a directory tree."""
    packages = []
    for dirpath, subdirs, files in os.walk(base_dir):
        if '__init__.py' not in files:
            continue
        package = dirpath.replace(os.path.sep, '.')
        if base_dir != prefix:
            package = package.replace(base_dir, prefix, 1)
        packages.append(package)
    return packages
