import pytest
import os
import logging # Add logging
from thermopyl.core.utils import build_pandas_dataframe # Corrected import
from thermopyl.core.utils import get_fn

# Configure logging for parser and utils
# Add this block to configure logging
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Configure parser logger
parser_logger = logging.getLogger('thermopyl.core.parser')
parser_logger.setLevel(logging.DEBUG)
# Check if handlers are already added to prevent duplicates if tests are run multiple times
if not parser_logger.handlers:
    parser_handler = logging.StreamHandler()
    parser_handler.setFormatter(formatter)
    parser_logger.addHandler(parser_handler)
parser_logger.propagate = False

# Configure utils logger
utils_logger = logging.getLogger('thermopyl.core.utils')
utils_logger.setLevel(logging.DEBUG)
if not utils_logger.handlers:
    utils_handler = logging.StreamHandler()
    utils_handler.setFormatter(formatter)
    utils_logger.addHandler(utils_handler)
utils_logger.propagate = False

# Test files (replace with your actual file paths or use a fixture)
test_dir = os.path.join(os.path.dirname(__file__), "..", "data")
test_files = [get_fn(f) for f in os.listdir(test_dir) if f.endswith(".xml")]
single_test_file = get_fn("j.ces.2005.08.012.xml") # Example single file for some tests
alloy_test_file = get_fn("j.tca.2007.01.009.xml") # Pb-Cd alloy file

def test_single_file_no_normalize():
    """Test parsing a single file without alloy normalization."""
    if not os.path.exists(single_test_file):
        pytest.skip(f"Test file {single_test_file} not found.")
    
    data, compounds = build_pandas_dataframe([single_test_file], normalize_alloys=False)
    print("\\n=== Single File (No Normalize) Data ===")
    print(data.head())
    print("=== Compound Data ===")
    print(compounds.head())
    assert not data.empty
    assert "normalized_formula" not in data.columns # Should not be present if normalize_alloys=False
    assert "active_components" not in data.columns # Should not be present

def test_real_file_no_normalize():
    """Test parsing multiple files without alloy normalization."""
    if not test_files:
        pytest.skip("No XML test files found in the data directory.")
        
    data, compounds = build_pandas_dataframe(test_files, normalize_alloys=False)
    print("\\n=== All Files (No Normalize) Data ===")
    print(data.head())
    print("=== Compound Data ===")
    print(compounds.head())
    assert not data.empty
    assert "normalized_formula" not in data.columns
    assert "active_components" not in data.columns

def test_real_file_alloy_output():
    from pymatgen.core import Composition

    # Use only the specific file that has alloys for focused testing
    if not os.path.exists(alloy_test_file):
        pytest.skip(f"Test file {alloy_test_file} not found.")
        
    data, compounds = build_pandas_dataframe([alloy_test_file], normalize_alloys=True)

    print("\\n\\n=== Full Alloy Data (Focused Test) ===")
    print(data.to_string()) # Print entire dataframe for this focused test
    print("=== Compound Data (Focused Test) ===")
    print(compounds.head())
    print(f"Total records parsed: {len(data)}\\n")

    assert not data.empty, "Parsed DataFrame is empty — check parser or input file."
    assert "normalized_formula" in data.columns, "Missing normalized_formula column"
    assert "active_components" in data.columns, "Missing active_components column"

    any_parsed = False
    for i, row in data.iterrows():
        formula = row.get("normalized_formula", "")
        active_components_str = row.get('active_components', "")
        print(f"[{i}] Formula: '{formula}' | Active: '{active_components_str}'")

        if not formula or not isinstance(formula, str) or formula.strip() == "":
            print(f"[{i}] Skipped: Empty or invalid formula")
            continue

        try:
            comp = Composition(formula)
            assert isinstance(comp, Composition), f"Invalid composition object for: {formula}"
            if active_components_str: # Only check if active_components is not empty
                for el_symbol in active_components_str.split(','):
                    el_symbol = el_symbol.strip()
                    if el_symbol: # Ensure element symbol is not empty after strip
                        assert el_symbol in comp, f"Expected element {el_symbol} not found in formula {formula} (Composition elements: {[e.symbol for e in comp.elements]})"
            any_parsed = True
        except Exception as e:
            raise AssertionError(f"❌ Failed to parse/validate normalized formula '{formula}' for row {i} (active: '{active_components_str}'): {e}")

    assert any_parsed, "No valid normalized formulas were parsed and validated — check mapping logic and normalization."

# Example of how you might test specific values if you knew them:
# def test_specific_alloy_composition():
#     # ... setup to parse j.tca.2007.01.009.xml ...
#     # data, _ = build_pandas_dataframe([get_fn("j.tca.2007.01.009.xml")], normalize_alloys=True)
#     # specific_row = data[data['material_id'] == 'SOME_ID_FOR_PB_CD_ALLOY_POINT'] 
#     # assert specific_row['normalized_formula'].iloc[0] == "Pb0.967Cd0.033" # Or mole fraction equivalent
#     # assert specific_row['active_components'].iloc[0] == "Cd, Pb"
