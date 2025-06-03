import re
from typing import Dict, List, Union

def formula_to_element_counts(formula_string: str) -> Dict[str, int]:
    """
    Transform a chemical formula into a dictionary of (element, number) pairs.

    Parameters
    ----------
    formula_string : str
        A string chemical formula like 'Pb', 'H2O', 'C6H12O6', 'Fe2(SO4)3'

    Returns
    -------
    dict
        Dictionary mapping element symbols to integer counts
    """
    pattern = r'([A-Z][a-z]{0,2})(\d*)'
    counts = {}
    for match in re.finditer(pattern, formula_string):
        element, number = match.groups()
        counts[element] = counts.get(element, 0) + int(number or 1)
    return counts

def count_atoms(formula_string: str) -> int:
    """
    Count the total number of atoms in a chemical formula.

    Parameters
    ----------
    formula_string : str
        Chemical formula string

    Returns
    -------
    int
        Total number of atoms
    """
    element_counts = formula_to_element_counts(formula_string)
    return sum(element_counts.values())

def count_atoms_in_set(formula_string: str, which_atoms: List[str]) -> int:
    """
    Count how many atoms from a given set are present in a formula.

    Parameters
    ----------
    formula_string : str
        Chemical formula
    which_atoms : list of str
        List of element symbols to count (e.g., ['Pb', 'Zn'])

    Returns
    -------
    int
        Total number of selected atoms
    """
    element_counts = formula_to_element_counts(formula_string)
    return sum(val for key, val in element_counts.items() if key in which_atoms)

def get_first_entry(entry: Union[List, str]) -> str:
    """
    Return the first entry from a list or a string.

    Parameters
    ----------
    entry : list or str
        Possibly a list of strings (e.g., from CIR or InChI parsing)

    Returns
    -------
    str
        First string entry
    """
    if isinstance(entry, list):
        return entry[0]
    return entry
