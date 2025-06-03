import os
from pkg_resources import resource_filename
from typing import List, Tuple
import pandas as pd
from thermopyl.core.parser import load_thermoml_data

def get_fn(name: str) -> str:
    fn = resource_filename('thermopyl', os.path.join('data', name))
    if not os.path.exists(fn):
        raise ValueError(f"Sorry! {fn} does not exist. If you just added it, you'll have to re-install.")
    return fn

def make_path(filename: str) -> None:
    path = os.path.split(filename)[0]
    if path:
        os.makedirs(path, exist_ok=True)

def build_pandas_dataframe(filenames: List[str], xsd_path: str = "ThermoML.xsd") -> Tuple[pd.DataFrame, pd.Series]:
    """
    Build pandas dataframe for property data and compounds.

    Parameters
    ----------
    filenames : list
        List of ThermoML filenames to process.
    xsd_path : str
        Path to the ThermoML schema file

    Returns
    -------
    data : pandas DataFrame
        Compiled ThermoML dataframe
    compounds : pandas Series
        Compounds dictionary: name -> formula
    """
    all_records = []
    compound_dict = {}

    for filename in filenames:
        print(f"Processing {filename}")
        try:
            entries = load_thermoml_data(filename, xsd_path)
            for entry in entries:
                for record in entry.values:
                    row = {
                        "material_id": entry.material_id,
                        "components": "__".join(entry.components),
                        **entry.metadata
                    }
                    for var in record.variable_values:
                        row[f"var_{var.var_type}"] = var.value
                    for prop in record.property_values:
                        row[f"prop_{prop.prop_name}"] = prop.value
                        row[f"prop_{prop.prop_name}_uncertainty"] = prop.uncertainty
                        row[f"prop_{prop.prop_name}_phase"] = prop.phase
                    all_records.append(row)
                for comp in entry.components:
                    formula = next((v['formula'] for v in compound_dict.values() if v['name'] == comp), "")
                    compound_dict[comp] = formula
        except Exception as e:
            print(f"Failed to parse {filename}: {e}")

    df = pd.DataFrame(all_records)
    compounds = pd.Series(compound_dict)
    return df, compounds

def pandas_dataframe(thermoml_path: str = None):
    if thermoml_path is None:
        if 'THERMOML_PATH' in os.environ:
            hdf5_filename = os.path.join(os.environ["THERMOML_PATH"], 'data.h5')
        else:
            hdf5_filename = os.path.join(os.path.expanduser("~"), '.thermopyl', 'data.h5')
    else:
        hdf5_filename = os.path.join(thermoml_path, 'data.h5')

    if not os.path.exists(hdf5_filename):
        raise FileNotFoundError(
            f"Could not find `data.h5` in path `{thermoml_path or '~/.thermopyl'}`.\n"
            "Make sure you have run `thermoml-build-pandas` and it has completed successfully."
        )

    df = pd.read_hdf(hdf5_filename)
    return df
