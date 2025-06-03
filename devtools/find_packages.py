import os

def find_packages(base_dir='MDTraj', prefix='mdtraj'):
    """Find all Python packages in a directory tree."""
    packages = [f'{prefix}.scripts']
    for dirpath, subdirs, files in os.walk(base_dir):
        if '__init__.py' not in files:
            continue
        package = dirpath.replace(os.path.sep, '.')
        packages.append(package.replace(base_dir, prefix))
    return packages
