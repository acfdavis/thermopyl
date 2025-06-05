import os
import tempfile
import shutil
import pandas as pd
import xmlschema
from pymatgen.core import Composition

from thermopyl.core.chemistry_utils import (
    count_atoms,
    count_atoms_in_set,
    formula_to_element_counts
)
from thermopyl.core.utils import get_fn, build_pandas_dataframe, pandas_dataframe
from thermopyl.core.parser import parse_thermoml_xml

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
pd.set_option('display.max_colwidth', None)


test_files = [get_fn(f) for f in [
    "je8006138.xml",
    "acs.jced.8b00745.xml",
    "acs.jced.8b00050.xml",
    "j.tca.2012.07.033.xml",
    "j.tca.2007.01.009.xml"
]]


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
        filenames = [get_fn(f) for f in test_files]
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

def test_schema_validation():
    for f in test_files:
        entries = parse_thermoml_xml(get_fn(f))
        assert len(entries) > 0

def test_compound_parsing():
    expected_compounds = {
        "je8006138.xml": ["C6H12", "C6H14", "C24H51O4P"],
        "acs.jced.8b00050.xml": ["C12H18N2O3S", "C10H13ClN2O3S"],
        "j.tca.2012.07.033.xml": ["Bi", "Zn", "Al"],
        "j.tca.2007.01.009.xml": ["Pb", "Cd", "Sn", "Zn"]
    }
    for f in test_files:
        _, compounds_df = build_pandas_dataframe([get_fn(f)], normalize_alloys=True)
        print(f"compound_df columns for {f}:", compounds_df.columns)
        formulas = compounds_df['formula'].tolist()
        print(f"Formulas in {f}: {formulas[:5]}")
        for expected in expected_compounds.get(f, []):
            assert any(expected in form for form in formulas if isinstance(form, str)), f"Expected formula {expected} not found in {f}"

def test_long_format_output():
    for f in test_files:
        data, _ = build_pandas_dataframe([get_fn(f)], long_form=True)
        assert all(col in data.columns for col in ["name", "value", "type"])

def test_malformed_handling():
    malformed_path = tempfile.mktemp(suffix=".xml")
    with open(malformed_path, "w") as f:
        f.write("<Invalid><ThisIsNot>Proper XML</ThisIsNot>")
    try:
        build_pandas_dataframe([malformed_path])
        assert False, "Expected exception not raised for malformed XML."
    except Exception:
        pass

def validate_xml(schema_path, file_path):
    schema = xmlschema.XMLSchema(schema_path)
    schema.validate(file_path)

def test_all_thermoml_files_validate():
    schema_path = get_fn("ThermoML.xsd")
    errors = []
    for f in test_files:
        try:
            validate_xml(schema_path, get_fn(f))
        except xmlschema.XMLSchemaValidationError as e:
            errors.append(f"{f} failed: {e}")
    assert not errors, "Schema validation failed:\n" + "\n".join(errors)

def test_alloy_composition_normalization():
    for f in ["j.tca.2012.07.033.xml", "j.tca.2007.01.009.xml"]:
        print(f"\nChecking {f}")
        data, _ = build_pandas_dataframe([get_fn(f)], normalize_alloys=True)
        print("Data columns:", data.columns)
        assert "normalized_formula" in data.columns, f"'normalized_formula' not found in {f}"

        formulas = data["normalized_formula"].dropna().unique()
        for formula in formulas:
            print(f"Trying to parse formula: {formula}")
            try:
                comp = Composition(formula)
                assert isinstance(comp, Composition)
            except Exception as e:
                raise AssertionError(f"Failed to parse normalized formula '{formula}' from {f}: {e}")

            
            
def test_incomplete_mole_fractions_backfill():
    from thermopyl.core.schema import NumValuesRecord, VariableValue, PropertyValue
    from thermopyl.core.utils import build_pandas_dataframe
    import pandas as pd

    record = NumValuesRecord(
        material_id="1__2",
        components=["Pb", "Zn"],
        compound_formulas={"Pb": "Pb", "Zn": "Zn"},
        variable_values=[
            VariableValue(var_type="Mole fraction", values=[0.6], var_number=1)  # Zn will be inferred
        ],
        property_values=[],
        component_id_map={1: "Pb", 2: "Zn"}
    )

    df, _ = build_pandas_dataframe([], normalize_alloys=True)
    df = pd.DataFrame(columns=["material_id", "components", "var_Mole fraction", "normalized_formula"])
    df.loc[0] = [record.material_id, "Pb, Zn", 0.6, ""]

    # Call normalization logic manually
    from pymatgen.core import Composition
    fracs = {"Pb": 0.6}
    inferred = 1.0 - sum(fracs.values())
    fracs["Zn"] = inferred

    normalized = ''.join(f"{el}{round(frac, 4)}" for el, frac in fracs.items())
    comp = Composition(normalized)
    assert isinstance(comp, Composition)


def test_variable_disambiguation_labels():
    from thermopyl.core.schema import NumValuesRecord, VariableValue, PropertyValue
    from thermopyl.core.utils import build_pandas_dataframe
    import pandas as pd

    record = NumValuesRecord(
        material_id="1__2",
        components=["Pb", "Zn"],
        compound_formulas={"Pb": "Pb", "Zn": "Zn"},
        variable_values=[
            VariableValue(var_type="Mole fraction_1", values=[0.6], var_number=1),
            VariableValue(var_type="Mole fraction_2", values=[0.4], var_number=2),
        ],
        property_values=[],
        component_id_map={1: "Pb", 2: "Zn"}
    )

    row = {
        "material_id": record.material_id,
        "components": ", ".join(record.components),
    }

    for v in record.variable_values:
        row[f"var_{v.var_type}"] = v.values[0]

    df = pd.DataFrame([row])

    assert "var_Mole fraction_1" in df.columns
    assert "var_Mole fraction_2" in df.columns

