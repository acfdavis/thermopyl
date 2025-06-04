import os
from importlib.resources import files
from typing import List, Tuple, Dict, Any
import pandas as pd
from thermopyl.core.parser import load_thermoml_data


def get_fn(name: str) -> str:
    """
    Get the full path to one of the reference files shipped for testing.

    In the source distribution, these files are in ``thermopyl/data``.
    On installation, they're placed in the package resources.
    """
    try:
        return str(files("thermopyl.data").joinpath(name))
    except FileNotFoundError:
        raise ValueError(f"Sorry! {name} does not exist. If you just added it, you'll need to reinstall.")


def make_path(filename: str) -> None:
    """
    Ensure the directory structure exists for a given filename.
    """
    path = os.path.split(filename)[0]
    if path:
        os.makedirs(path, exist_ok=True)


def build_pandas_dataframe(
    filenames: List[str], xsd_path: str = "ThermoML.xsd", long_form: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build pandas dataframe for property data and compounds.

    Parameters
    ----------
    filenames : list
        List of ThermoML filenames to process.
    xsd_path : str
        Path to the ThermoML schema file.
    long_form : bool
        Whether to return the data in long-form instead of wide-form.

    Returns
    -------
    data : pandas DataFrame
        Compiled ThermoML dataframe (long-form or wide-form).
    compounds : pandas DataFrame
        Compound metadata.
    """
    all_records = []
    compound_metadata: Dict[str, Dict[str, Any]] = {}

    for filename in filenames:
        try:
            print(f"Processing {filename}")
            entries = load_thermoml_data(filename, xsd_path)

            if not entries:
                print("Warning: No entries parsed from file.")
            else:
                print(f"Found {len(entries)} ThermoML entries")

            for entry in entries:
                for record in entry.values:
                    base = {
                        "material_id": entry.material_id,
                        "components": "__".join(entry.components),
                        **entry.metadata
                    }

                    if long_form:
                        # One row per variable/property (tidy format)
                        for var in record.variable_values:
                            row = base.copy()
                            row.update({
                                "type": "variable",
                                "name": var.var_type,
                                "value": var.value
                            })
                            all_records.append(row)

                        for prop in record.property_values:
                            row = base.copy()
                            row.update({
                                "type": "property",
                                "name": prop.prop_name,
                                "value": prop.value,
                                "uncertainty": prop.uncertainty,
                                "phase": prop.phase
                            })
                            all_records.append(row)
                    else:
                        # Wide format: all variables and properties as columns
                        row = base.copy()
                        var_seen = {}
                        prop_seen = {}

                        for var in record.variable_values:
                            col = f"var_{var.var_type}"
                            if col in row:
                                var_seen[col] = var_seen.get(col, 1) + 1
                                col = f"{col}_{var_seen[col]}"
                            row[col] = var.value

                        for prop in record.property_values:
                            base_col = f"prop_{prop.prop_name}"
                            index = prop_seen.get(base_col, 0)
                            prop_seen[base_col] = index + 1
                            col = base_col if index == 0 else f"{base_col}_{index+1}"
                            row[col] = prop.value
                            row[f"{col}_uncertainty"] = prop.uncertainty
                            row[f"{col}_phase"] = prop.phase

                        all_records.append(row)

                # Store compound metadata
                for comp in entry.components:
                    if comp not in compound_metadata:
                        compound_metadata[comp] = {
                            "name": comp,
                            "formula": entry.compound_formulas.get(comp, "")
                        }

        except Exception as e:
            print(f"Failed to parse {filename}: {e}")

    df = pd.DataFrame(all_records)
    compounds = pd.DataFrame.from_dict(compound_metadata, orient='index')
    return df, compounds


def pandas_dataframe(thermoml_path: str = None):
    """
    Load prebuilt ThermoML HDF5 file from the configured or default path.

    Parameters
    ----------
    thermoml_path : str, optional
        Optional path to override default HDF5 location.

    Returns
    -------
    df : pd.DataFrame
        Loaded ThermoML data.
    """
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
