import os
import tempfile
import shutil
import pandas as pd
import xmlschema
from thermopyl.core.chemistry_utils import (
    count_atoms,
    count_atoms_in_set,
    formula_to_element_counts
)
from thermopyl.core.utils import get_fn, build_pandas_dataframe, pandas_dataframe
from thermopyl.core.parser import parse_thermoml_xml  # updated function name

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
pd.set_option('display.max_colwidth', None)

test_files = "j.fluid.2006.10.021.xml"

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
        filenames = [get_fn(test_files)]
        data, compounds = build_pandas_dataframe(filenames)

        print("\n=== DEBUG OUTPUT ===")
        print(f"Parsed {len(data)} records")
        print(f"DataFrame columns: {list(data.columns)}")
        print(f"Compound entries: {len(compounds)}")
        print(f"First few entries:\n{data.head()}")
        print("=== END DEBUG OUTPUT ===\n")

        data.to_hdf(os.path.join(tmpdir, 'data.h5'), key='data')
        compounds.to_hdf(os.path.join(tmpdir, 'compound_name_to_formula.h5'), key='data')
        df = pandas_dataframe(tmpdir)
        assert not df.empty
    finally:
        shutil.rmtree(tmpdir)

def test_parsed_content_correctness():
    filenames = [get_fn(test_files)]
    data, compounds = build_pandas_dataframe(filenames)

    print("\n=== Columns in parsed DataFrame ===\n")
    print(list(data.columns))
    print("\n=== Data ===\n")
    print(data.head(3))

    assert not data.empty
    assert "prop_Viscosity, Pa*s" in data.columns

    subset = data[
        (data["var_Temperature, K"] == 293.15) &
        (data["var_Mole fraction_3"] == 0.5005)
    ]
    assert not subset.empty
    value = subset.iloc[0]["prop_Viscosity, Pa*s"]
    assert abs(value - 0.003881) < 1e-6

def test_schema_validation():
    entries = parse_thermoml_xml(get_fn(test_files))
    assert len(entries) > 0

def test_compound_parsing():
    _, compounds_df = build_pandas_dataframe([get_fn("j.fluid.2006.10.021.xml")])
    print("compound_df columns:", compounds_df.columns)

    formulas = compounds_df['formula'].tolist()
    print(formulas[:5])

    assert any("C6H12" in f for f in formulas if isinstance(f, str))
    assert any("C6H14" in f for f in formulas if isinstance(f, str))
    assert any("C24H51O4P" in f for f in formulas if isinstance(f, str))


def test_long_format_output():
    data, _ = build_pandas_dataframe([get_fn(test_files)], long_form=True)
    assert all(col in data.columns for col in ["name", "value", "type"])

def test_parsed_content_correctness():
    malformed_path = tempfile.mktemp(suffix=".xml")
    with open(malformed_path, "w") as f:
        f.write("<Invalid><ThisIsNot>Proper XML</ThisIsNot>")
    try:
        build_pandas_dataframe([malformed_path])
    except Exception:
        pass

def validate_xml(schema_path, file_path):
    schema = xmlschema.XMLSchema(schema_path)
    schema.validate(file_path)

def test_all_thermoml_files_validate():
    schema_path = get_fn("ThermoML.xsd")
    data_dir = os.path.dirname(get_fn(test_files))
    xml_files = [f for f in os.listdir(data_dir) if f.endswith(".xml")]
    assert xml_files, "No XML files found for validation."

    errors = []
    for xml_file in xml_files:
        full_path = os.path.join(data_dir, xml_file)
        try:
            validate_xml(schema_path, full_path)
        except xmlschema.XMLSchemaValidationError as e:
            errors.append(f"{xml_file} failed: {e}")

    assert not errors, "Schema validation failed:\n" + "\n".join(errors)
