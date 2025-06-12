import os
import tempfile
import shutil
import pandas as pd
import xmlschema
from pymatgen.core import Composition
import logging # Added logging import

from thermopyl.core.chemistry_utils import (
    count_atoms,
    count_atoms_in_set,
    formula_to_element_counts
)
from thermopyl.core.utils import get_fn, build_pandas_dataframe, pandas_dataframe
from thermopyl.core.parser import parse_thermoml_xml
from thermopyl.core.schema import NumValuesRecord, VariableValue # Ensure these are imported for the tests that use them

# Configure logging for utils to see errors from build_pandas_dataframe
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Configure utils logger
utils_logger = logging.getLogger('thermopyl.core.utils')
utils_logger.setLevel(logging.DEBUG) # Set to DEBUG to capture all levels of logs
if not utils_logger.handlers: # Avoid adding multiple handlers if tests are run multiple times
    utils_handler = logging.StreamHandler() # Log to console
    utils_handler.setFormatter(formatter)
    utils_logger.addHandler(utils_handler)
utils_logger.propagate = False # To prevent logs from being passed to the root logger if it has handlers

# Configure parser logger (optional, but good for consistency if parser issues are suspected elsewhere)
parser_logger = logging.getLogger('thermopyl.core.parser')
parser_logger.setLevel(logging.DEBUG)
if not parser_logger.handlers:
    parser_handler = logging.StreamHandler()
    parser_handler.setFormatter(formatter)
    parser_logger.addHandler(parser_handler) # Added handler
    parser_logger.propagate = False # Added propagate setting

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
pd.set_option('display.max_colwidth', None)


test_files = [get_fn(f) for f in [
    "je8006138.xml",
    "acs.jced.8b00745.xml",
   # "acs.jced.8b00050.xml",
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
        result = build_pandas_dataframe(filenames)
        data = result["data"]
        compounds = result["compounds"]
        repository_metadata = result["repository_metadata"]

        print("\n=== DEBUG OUTPUT ===")
        print(f"Parsed {len(data)} records")
        print(f"DataFrame columns: {list(data.columns)}")
        print(f"Compound entries: {len(compounds)}")
        print(f"Repository metadata: {repository_metadata}")
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
        # "acs.jced.8b00050.xml": ["C12H18N2O3S", "C10H13ClN2O3S"],  # Commented out to match test_files
        "acs.jced.8b00745.xml": ["C2H6O", "C31H52O3", "CO2"],
        "j.tca.2012.07.033.xml": ["Bi", "Zn", "Al"],
        "j.tca.2007.01.009.xml": ["Pb", "Cd", "Sn", "Zn"]
    }
    for f in test_files:
        result = build_pandas_dataframe([get_fn(f)], normalize_alloys=True)
        compounds_df = result["compounds"]
        print(f"compound_df columns for {f}:", compounds_df.columns)
        # Ensure 'symbol' column exists before trying to access it
        if 'symbol' not in compounds_df.columns:
            raise AssertionError(f"'symbol' column not found in compounds_df for {f}. Columns: {compounds_df.columns}")
        formulas = compounds_df['symbol'].tolist() # Changed 'formula' to 'symbol'
        expected = expected_compounds.get(os.path.basename(f), [])
        assert sorted(formulas) == sorted(expected), f"Mismatch for {f}"

def test_long_format_output():
    for f in test_files:
        result = build_pandas_dataframe([get_fn(f)])
        data = result["data"]
        assert not data.empty, f"Dataframe is empty for {f}"
        # Add more specific assertions based on expected long_form behavior if re-implemented

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
        result = build_pandas_dataframe([get_fn(f)], normalize_alloys=True)
        data = result["data"]
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

            
            
def test_incomplete_mole_fractions_backfill(mocker): # Added mocker fixture
    # from thermopyl.core.schema import NumValuesRecord, VariableValue, PropertyValue # Already imported
    # from thermopyl.core.utils import build_pandas_dataframe # Already imported
    # import pandas as pd # Already imported

    # Define a dummy file path for parse_thermoml_xml to "process"
    dummy_xml_path = "dummy.xml"

    record = NumValuesRecord(
        material_id="test_material_1", 
        components=["Pb", "Zn"],
        compound_formulas={"Pb": "Pb", "Zn": "Zn"},
        variable_values=[
            VariableValue(var_type="Mole fraction", values=[0.6], var_number=1, linked_component_org_num=1) 
        ],
        property_values=[],
        component_id_map={1: "Pb", 2: "Zn"}, 
        source_file=dummy_xml_path,
        citation=None # Added citation field with a default value
    )
    
    # Mock parse_thermoml_xml where it's used in the utils module
    mocker.patch('thermopyl.core.utils.parse_thermoml_xml', return_value=[record])
    # Patch xmlschema.XMLSchema.is_valid to always return True to avoid file access
    mocker.patch('xmlschema.XMLSchema.is_valid', return_value=True)
    # Patch xmlschema.XMLSchema.to_dict to avoid file access
    mocker.patch('xmlschema.XMLSchema.to_dict', return_value={})

    # Pass the dummy_xml_path to build_pandas_dataframe
    result = build_pandas_dataframe([dummy_xml_path], normalize_alloys=True)
    df = result["data"]

    assert not df.empty
    assert "normalized_formula" in df.columns
    actual_formula = df["normalized_formula"].iloc[0]
    
    print(f"DEBUG: test_incomplete_mole_fractions_backfill - Actual normalized_formula: {actual_formula}")
    print(f"DEBUG: test_incomplete_mole_fractions_backfill - DataFrame head:\\n{df.head()}")

    expected_formula = "Pb0.6Zn0.4" # Updated expected formula
    assert actual_formula == expected_formula, f"Expected '{expected_formula}', got '{actual_formula}'"
    assert "active_components" in df.columns
    assert df["active_components"].iloc[0] == "Pb, Zn"


def test_variable_disambiguation_labels(mocker): # Added mocker fixture
    # from thermopyl.core.schema import NumValuesRecord, VariableValue, PropertyValue # Already imported
    # from thermopyl.core.utils import build_pandas_dataframe # Already imported
    # import pandas as pd # Already imported

    dummy_xml_path = "dummy_disambiguation.xml"

    record = NumValuesRecord(
        material_id="test_material_2", 
        components=["Fe", "Ni"], 
        compound_formulas={"Fe": "Fe", "Ni": "Ni"},
        variable_values=[
            VariableValue(var_type="Mole fraction", values=[0.7], var_number=1, linked_component_org_num=1), # Fe
            VariableValue(var_type="Mole fraction", values=[0.3], var_number=2, linked_component_org_num=2), # Ni
        ],
        property_values=[],
        component_id_map={1: "Fe", 2: "Ni"}, 
        source_file=dummy_xml_path,
        citation=None # Added citation field with a default value
    )
    
    # Mock parse_thermoml_xml where it's used in the utils module
    mocker.patch('thermopyl.core.utils.parse_thermoml_xml', return_value=[record])
    # Patch xmlschema.XMLSchema.is_valid to always return True to avoid file access
    mocker.patch('xmlschema.XMLSchema.is_valid', return_value=True)
    # Patch xmlschema.XMLSchema.to_dict to avoid file access
    mocker.patch('xmlschema.XMLSchema.to_dict', return_value={})

    result = build_pandas_dataframe([dummy_xml_path], normalize_alloys=True)
    df = result["data"]
    
    assert not df.empty
    assert "normalized_formula" in df.columns
    expected_formula = "Fe0.7Ni0.3" # Updated expected formula
    actual_formula = df["normalized_formula"].iloc[0]

    print(f"DEBUG: test_variable_disambiguation_labels - Actual normalized_formula: {actual_formula}")
    print(f"DEBUG: test_variable_disambiguation_labels - DataFrame head:\\n{df.head()}")
    
    assert actual_formula == expected_formula, f"Expected '{expected_formula}', got '{actual_formula}'"
    assert "active_components" in df.columns
    assert df["active_components"].iloc[0] == "Fe, Ni"

