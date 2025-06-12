import os
import pandas as pd
from typing import List, Tuple, Dict
from thermopyl.core.parser import parse_thermoml_xml
from pymatgen.core import Element, Composition # Ensure Composition is imported
import logging

logger = logging.getLogger(__name__)

def get_fn(filename: str) -> str:
    local_path = os.path.join(os.path.dirname(__file__), "..", "data", filename)
    if os.path.exists(local_path):
        return os.path.abspath(local_path)
    return filename  # fallback if running locally

# Helper function to check pymatgen availability
def _is_pymatgen_available() -> bool:
    try:
        # Check for Element and Composition classes
        if not (callable(getattr(Element, "is_valid_symbol", None)) and hasattr(Element("H"), "atomic_mass") and callable(getattr(Composition, "get_el_amt_dict", None))):
            return False
        return True
    except ImportError:
        return False
    except Exception: # Other potential issues during check
        return False

def build_pandas_dataframe(
    xml_files: List[str], normalize_alloys: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    all_records = []
    all_compounds_data = [] # Initialize this list
    compound_metadata: Dict[str, str] = {} # Initialize compound_metadata

    # Define pretty_formula as an inner function or a local helper
    def pretty_formula(frac_dict: Dict[str, float]) -> str:
        parts = []
        significant_fracs = {el: amt for el, amt in frac_dict.items() if amt > 1e-5}
        if not significant_fracs:
            return ""
        for el, amt in sorted(significant_fracs.items()):
            if abs(amt - 1.0) < 1e-3 and len(significant_fracs) == 1:
                parts.append(f"{el}")
            else:
                parts.append(f"{el}{round(amt, 3)}") # Changed rounding from 4 to 3 decimal places
        return "".join(parts)

    for file_path in xml_files:
        logger.info(f"Processing file: {file_path}")
        parsed_data = parse_thermoml_xml(file_path)

        for record in parsed_data:
            row = {
                "material_id": record.material_id,
                "components": ", ".join(record.components),
            }

            for var in record.variable_values:
                var_key_name = str(var.var_type).replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")
                row[f"var_{var_key_name}"] = str(var.values[0])
            
            for prop in record.property_values:
                prop_key_name = str(prop.prop_name).replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")
                row[f"prop_{prop_key_name}"] = str(prop.values[0])

            if normalize_alloys:
                mole_fracs = {}
                mass_fracs = {}
                current_record_active_elements = set()

                for var in record.variable_values:
                    if var.linked_component_org_num is not None:
                        element_symbol = record.component_id_map.get(var.linked_component_org_num)
                        if element_symbol:
                            try:
                                if Element.is_valid_symbol(element_symbol):
                                    current_record_active_elements.add(element_symbol)
                                    if var.var_type.startswith("Mole fraction"):
                                        mole_fracs[element_symbol] = var.values[0]
                                    elif var.var_type.startswith("Mass fraction"):
                                        mass_fracs[element_symbol] = var.values[0]
                                else:
                                    logger.warning(f"Invalid element symbol '{element_symbol}' from component_id_map for material_id {record.material_id}. Skipping.")
                            except ImportError:
                                current_record_active_elements.add(element_symbol)
                                if var.var_type.startswith("Mole fraction"):
                                    mole_fracs[element_symbol] = var.values[0]
                                elif var.var_type.startswith("Mass fraction"):
                                    mass_fracs[element_symbol] = var.values[0]
                            except Exception as e:
                                logger.warning(f"Error validating element symbol '{element_symbol}': {e}. Skipping.")
                
                active_components_str = ""
                normalized_formula_str = ""

                if current_record_active_elements:
                    active_components_str = ", ".join(sorted(list(current_record_active_elements)))
                elif record.components:
                    all_possible_elements = set()
                    for comp_name in record.components:
                        formula = record.compound_formulas.get(comp_name)
                        if formula:
                            try:
                                if Element.is_valid_symbol(formula):
                                    all_possible_elements.add(formula)
                            except ImportError:
                                all_possible_elements.add(formula)
                            except Exception:
                                pass 
                    if all_possible_elements:
                        active_components_str = ", ".join(sorted(list(all_possible_elements)))
                
                row["active_components"] = active_components_str # Set initial

                try:
                    if not _is_pymatgen_available():
                        logger.warning(f"Pymatgen not available. Alloy normalization skipped for {record.material_id}.")
                        row["normalized_formula"] = ""
                        all_records.append(row)
                        continue

                    if mole_fracs:
                        defined_elements_for_material = set(el for el in record.component_id_map.values() if el and Element.is_valid_symbol(el))
                        if len(mole_fracs) < len(defined_elements_for_material) and defined_elements_for_material.issuperset(mole_fracs.keys()):
                            total_frac = sum(mole_fracs.values())
                            missing_elements_set = defined_elements_for_material - mole_fracs.keys()
                            if len(missing_elements_set) == 1 and (0.95 < total_frac < 1.0):
                                missing_element = list(missing_elements_set)[0]
                                inferred_fraction = 1.0 - total_frac
                                if inferred_fraction > 1e-5:
                                    mole_fracs[missing_element] = inferred_fraction
                                    current_record_active_elements.add(missing_element)
                                    active_components_str = ", ".join(sorted(list(current_record_active_elements)))
                            elif total_frac < 0.95 or total_frac > 1.05:
                                logger.warning(f"Mole fractions for {record.material_id} ({mole_fracs}) sum to {total_frac}, not close to 1. Skipping fill.")
                        
                        normalized_formula_str = pretty_formula(mole_fracs)
                        if normalized_formula_str:
                            try:
                                final_elements_in_formula = set(Composition(normalized_formula_str).get_el_amt_dict().keys())
                                active_components_str = ", ".join(sorted(list(final_elements_in_formula)))
                            except Exception as e: # Catch issues with Composition parsing if pretty_formula is odd
                                logger.warning(f"Could not parse formula '{normalized_formula_str}' with Pymatgen for active component update: {e}")


                    elif mass_fracs:
                        logger.debug(f"Material ID {record.material_id}: Processing with mass_fracs. Initial mass_fracs: {mass_fracs}")
                        logger.debug(f"Material ID {record.material_id}: record.component_id_map: {record.component_id_map}")
                        
                        valid_mass_fracs = {el: mass for el, mass in mass_fracs.items() if Element.is_valid_symbol(el)}
                        if len(valid_mass_fracs) != len(mass_fracs):
                            logger.warning(f"Invalid symbols in mass_fracs for {record.material_id}. Using only valid: {valid_mass_fracs}")
                        
                        logger.debug(f"Material ID {record.material_id}: valid_mass_fracs before inference: {valid_mass_fracs}")

                        if not valid_mass_fracs:
                            normalized_formula_str = ""
                            # active_components_str is already set based on initial parsing or defaults to ""
                        else:
                            # Infer missing mass fraction if applicable
                            defined_elements_for_material = set(el for el in record.component_id_map.values() if el and Element.is_valid_symbol(el))
                            logger.debug(f"Material ID {record.material_id}: defined_elements_for_material (from map): {defined_elements_for_material}")
                            current_mass_frac_elements = set(valid_mass_fracs.keys())

                            if len(current_mass_frac_elements) < len(defined_elements_for_material):
                                total_known_mass_frac = sum(valid_mass_fracs.values())
                                missing_elements_set = defined_elements_for_material - current_mass_frac_elements
                                logger.debug(f"Material ID {record.material_id}: total_known_mass_frac: {total_known_mass_frac}, missing_elements_set: {missing_elements_set}")
                                
                                if len(missing_elements_set) == 1 and 0 < total_known_mass_frac < 1.0:
                                    missing_element = list(missing_elements_set)[0]
                                    inferred_fraction = 1.0 - total_known_mass_frac
                                    if inferred_fraction > 1e-5: # Only add if significant
                                        valid_mass_fracs[missing_element] = inferred_fraction
                                        logger.info(f"Material ID {record.material_id}: Inferred mass fraction for {missing_element}: {inferred_fraction:.4f} (original mass_fracs: {mass_fracs}, updated valid_mass_fracs: {valid_mass_fracs})")
                                elif len(missing_elements_set) > 0 and not (0 < total_known_mass_frac < 1.0):
                                     logger.warning(
                                        f"Material ID {record.material_id}: Mass fractions (known: {valid_mass_fracs}) sum to {total_known_mass_frac:.4f}. "
                                        f"{len(missing_elements_set)} component(s) ({missing_elements_set}) are undefined out of {defined_elements_for_material}. "
                                        f"Cannot reliably infer missing mass fractions."
                                    )
                            
                            logger.debug(f"Material ID {record.material_id}: valid_mass_fracs AFTER inference: {valid_mass_fracs}")
                            
                            # Proceed with conversion using potentially updated valid_mass_fracs
                            moles = {el: mass / Element(el).atomic_mass for el, mass in valid_mass_fracs.items()}
                            total_moles = sum(moles.values())
                            if total_moles > 1e-9:
                                final_mole_fracs = {el: amt / total_moles for el, amt in moles.items() if amt / total_moles > 1e-5}
                                logger.debug(f"Material ID {record.material_id}: final_mole_fracs for pretty_formula: {final_mole_fracs}")
                                normalized_formula_str = pretty_formula(final_mole_fracs)
                                if normalized_formula_str:
                                    try:
                                        final_elements_in_formula = set(Composition(normalized_formula_str).get_el_amt_dict().keys())
                                        active_components_str = ", ".join(sorted(list(final_elements_in_formula)))
                                    except Exception as e:
                                        logger.warning(f"Material ID {record.material_id}: Could not parse formula '{normalized_formula_str}' with Pymatgen for active component update: {e}")

                                elif valid_mass_fracs: 
                                     active_components_str = ", ".join(sorted(list(valid_mass_fracs.keys())))
                            else:
                                normalized_formula_str = ""
                                logger.warning(f"Material ID {record.material_id}: Total moles effectively zero for mass_fracs: {valid_mass_fracs}")
                                if valid_mass_fracs:
                                    active_components_str = ", ".join(sorted(list(valid_mass_fracs.keys())))
                    
                    row["normalized_formula"] = normalized_formula_str
                    row["active_components"] = active_components_str
                    logger.debug(f"Material ID {record.material_id}: Set row normalized_formula='{normalized_formula_str}', active_components='{active_components_str}'")

                except ImportError: # Should be caught by _is_pymatgen_available, but as a fallback
                    logger.error(f"Pymatgen import error during normalization for {record.material_id}.")
                    row["normalized_formula"] = ""
                except Exception as e:
                    logger.error(f"Normalization failed for {record.material_id}: {e}")
                    row["normalized_formula"] = ""
            
            all_records.append(row)

            # Process compound metadata (ensure this is correctly handled)
            for comp_name, comp_formula in record.compound_formulas.items():
                if comp_formula and comp_formula not in compound_metadata:
                    compound_metadata[comp_formula] = comp_name # Store symbol -> name
                # Or, if you want to store name -> symbol:
                # compound_metadata[comp_name] = comp_formula

        # Collect data for the compounds DataFrame
        for symbol, name_or_other_identifier in compound_metadata.items():
            # Assuming symbol is the key and you want to list it. Adjust if structure is different.
            all_compounds_data.append({"symbol": symbol, "name": name_or_other_identifier})


    df = pd.DataFrame(all_records)
    compounds_df = pd.DataFrame(all_compounds_data)
    
    # Deduplicate compounds_df if necessary, e.g., based on 'symbol'
    if not compounds_df.empty:
        compounds_df = compounds_df.drop_duplicates(subset=['symbol']).reset_index(drop=True)

    logger.debug(f"Final DataFrame columns: {df.columns.tolist()}")
    if normalize_alloys:
        logger.debug(f"Sample of normalized_formula: {df['normalized_formula'].head().tolist()}")
        logger.debug(f"Sample of active_components: {df['active_components'].head().tolist()}")

    return df, compounds_df

def pandas_dataframe(path: str) -> pd.DataFrame:
    try:
        result = pd.read_hdf(os.path.join(path, "data.h5"), key="data")
        if isinstance(result, pd.Series):
            result = result.to_frame().T
        return result
    except Exception as e:
        print(f"Failed to load DataFrame from HDF5: {e}")
        return pd.DataFrame()
