import sys
import os

def check_dependencies(dependencies):
    """Check for required dependencies and print install instructions if missing."""
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
            raise ValueError(dep)

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
