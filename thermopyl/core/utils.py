import os
import pandas as pd
from typing import List, Tuple, Dict
from thermopyl.core.parser import parse_thermoml_xml
from pymatgen.core import Element



def get_fn(filename: str) -> str:
    local_path = os.path.join(os.path.dirname(__file__), "..", "data", filename)
    if os.path.exists(local_path):
        return os.path.abspath(local_path)
    return filename  # fallback if running locally

def build_pandas_dataframe(filenames: List[str], long_form: bool = False, normalize_alloys: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
    all_records = []
    compound_metadata: Dict[str, str] = {}

    for path in filenames:
        try:
            results = parse_thermoml_xml(path)
        except Exception as e:
            print(f"Failed to parse {path}: {e}")
            continue

        for record in results:
            compound_metadata.update(record.compound_formulas)

            if long_form:
                for var in record.variable_values:
                    all_records.append({
                        "material_id": record.material_id,
                        "components": ", ".join(record.components),
                        "type": f"var_{var.var_type}",
                        "var_number": var.var_number,
                        "value": var.values[0],
                        "name": var.var_type
                    })
                for prop in record.property_values:
                    all_records.append({
                        "material_id": record.material_id,
                        "components": ", ".join(record.components),
                        "type": f"prop_{prop.prop_name}",
                        "value": prop.values[0],
                        "name": prop.prop_name,
                        "uncertainty": prop.uncertainties[0] if prop.uncertainties else None
                    })
            else:
                # Normalize alloy data if requested
                mole_fracs = {}
                mass_fracs = {}

                varnum_to_element = {
                    var.var_number: record.component_id_map.get(var.var_number)
                    for var in record.variable_values
                    if var.var_number in record.component_id_map
                }
                active_elements = set(varnum_to_element.values())

                row = {
                    "material_id": record.material_id,
                    "components": ", ".join(record.components),
                    "active_components": ", ".join(sorted(active_elements))
                }

                for var in record.variable_values:
                    row[f"var_{var.var_type}"] = var.values[0]
                    if var.var_number and var.var_number in varnum_to_element:
                        element = varnum_to_element[var.var_number]
                        if var.var_type.startswith("Mole fraction") and element:
                            mole_fracs[element] = var.values[0]
                        elif var.var_type.startswith("Mass fraction") and element:
                            mass_fracs[element] = var.values[0]

                for prop in record.property_values:
                    row[f"prop_{prop.prop_name}"] = prop.values[0]

                if normalize_alloys:
                    if mole_fracs:
                        if len(mole_fracs) < len(active_elements):
                            total_frac = sum(mole_fracs.values())
                            if total_frac > 1.01:
                                print(f"Warning: mole fractions exceed 1.0 for {record.material_id}")
                            elif total_frac < 0.99:
                                print(f"Warning: mole fractions less than 1.0 for {record.material_id}")

                            missing = [el for el in active_elements if el not in mole_fracs]
                            if len(missing) == 1:
                                mole_fracs[missing[0]] = max(0.0, 1.0 - total_frac)
                            else:
                                print(f"Warning: skipping normalization for {record.material_id} — insufficient component fractions ({mole_fracs})")
                                mole_fracs = {}

                        def pretty_formula(frac_dict):
                            parts = []
                            for el, amt in sorted(frac_dict.items()):
                                if abs(amt - 1.0) < 1e-3:
                                    parts.append(f"{el}")
                                else:
                                    parts.append(f"{el}{round(amt, 4)}")
                            return ''.join(parts)

                        row["normalized_formula"] = pretty_formula(mole_fracs)

                    elif mass_fracs:
                        try:
                            moles = {el: mass / Element(el).atomic_mass for el, mass in mass_fracs.items()}
                            total = sum(moles.values())
                            mole_fracs = {el: amt / total for el, amt in moles.items() if amt > 0}
                            row["normalized_formula"] = ''.join(f"{el}{round(frac, 4)}" for el, frac in mole_fracs.items())
                        except ImportError:
                            raise ImportError("pymatgen must be installed to normalize alloys by mass fraction.")
                        except Exception as e:
                            print(f"Mass fraction conversion failed for {record.material_id}: {e}")

                all_records.append(row)


    df = pd.DataFrame(all_records)
    compound_df = pd.DataFrame([
        {"name": name, "formula": formula}
        for name, formula in compound_metadata.items()
    ])
    print("Compound metadata:", compound_metadata)


    return df, compound_df

def pandas_dataframe(path: str) -> pd.DataFrame:
    try:
        return pd.read_hdf(os.path.join(path, "data.h5"), key="data")
    except Exception as e:
        print(f"Failed to load DataFrame from HDF5: {e}")
        return pd.DataFrame()
