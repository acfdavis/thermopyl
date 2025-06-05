import os
import pandas as pd
from typing import List, Tuple, Dict
from .parser import parse_thermoml_xml

def get_fn(filename: str) -> str:
    local_path = os.path.join(os.path.dirname(__file__), "..", "data", filename)
    if os.path.exists(local_path):
        return os.path.abspath(local_path)
    return filename  # fallback if running locally

def build_pandas_dataframe(filenames: List[str], long_form: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
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
                row = {
                    "material_id": record.material_id,
                    "components": ", ".join(record.components)
                }
                for var in record.variable_values:
                    row[f"var_{var.var_type}"] = var.values[0]
                for prop in record.property_values:
                    row[f"prop_{prop.prop_name}"] = prop.values[0]
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
