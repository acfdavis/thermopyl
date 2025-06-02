import sys
import os
from typing import List, Tuple, Union

def check_dependencies(dependencies: List[Union[Tuple[str], Tuple[str, str]]]):
    """Check for required dependencies and print install instructions if missing.

    Parameters
    ----------
    dependencies : list of (import_name,) or (import_name, pip_name)
        Each entry is a tuple: (import_name,) or (import_name, pip/conda name)
    """
    def module_exists(dep):
        try:
            __import__(dep)
            return True
        except ImportError:
            return False

    for dep in dependencies:
        if len(dep) == 1:
            import_name, pkg_name = dep[0], dep[0]
        elif len(dep) == 2:
            import_name, pkg_name = dep
        else:
            raise ValueError(f"Dependency tuple must have 1 or 2 elements: {dep}")

        if not module_exists(import_name):
            lines = [
                '-' * 50,
                f'Warning: This package requires {import_name!r}. Try',
                '',
                f'  $ conda install {pkg_name}',
                '',
                'or:',
                '',
                f'  $ pip install {pkg_name}',
                '-' * 50,
            ]
            print(os.linesep.join(lines), file=sys.stderr)
