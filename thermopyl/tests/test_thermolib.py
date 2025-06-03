import tempfile
import os
import shutil

from thermopyl.core.chemistry_utils import (
    count_atoms,
    count_atoms_in_set,
    formula_to_element_counts
)


from thermopyl.utils import get_fn, build_pandas_dataframe, pandas_dataframe

formula = "C3H5N2OClBr"
reference_atom_count = 13
reference_element_counts = dict(C=3, H=5, N=2, O=1, Cl=1, Br=1)

def test_count():
    assert count_atoms(formula) == reference_atom_count

def test_count_atoms_in_set():
    assert count_atoms_in_set(formula, ["C", "H"]) == 8

def test_formula_to_element_counts():
    assert formula_to_element_counts(formula) == reference_element_counts

def test_build_pandas_dataframe():
    tmpdir = tempfile.mkdtemp()
    try:
        filenames = [get_fn("je8006138.xml")]
        data, compounds = build_pandas_dataframe(filenames)
        data.to_hdf(os.path.join(tmpdir, 'data.h5'), key='data')
        compounds.to_hdf(os.path.join(tmpdir, 'compound_name_to_formula.h5'), key='data')
        df = pandas_dataframe(thermoml_path=tmpdir)
        assert not df.empty
    finally:
        shutil.rmtree(tmpdir)
