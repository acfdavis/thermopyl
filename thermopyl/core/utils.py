import os
import json
import pandas as pd
from typing import List, Tuple, Dict, Any, Optional # Added Optional
from thermopyl.core.parser import parse_thermoml_xml
from pymatgen.core import Element, Composition # Ensure Composition is imported
import logging
from thermopyl import version as thermopyl_version # Added import for version

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

def load_repository_metadata(metadata_path: str = None) -> dict:
    """
    Load repository-level metadata from archive_info.json (NERDm metadata).
    If metadata_path is None, will look for ~/.thermoml/archive_info.json.
    """
    if metadata_path is None:
        home = os.path.expanduser("~")
        metadata_path = os.path.join(home, ".thermoml", "archive_info.json")
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        return metadata
    except Exception as e:
        logger.warning(f"Could not load repository metadata from {metadata_path}: {e}")
        return {}

def build_pandas_dataframe(
    xml_files: List[str], normalize_alloys: bool = False, repository_metadata: Optional[dict] = None
) -> dict:
    """
    Build pandas DataFrames from ThermoML XML files and include repository-level metadata.
    Returns a dict with keys: 'data', 'compounds', 'repository_metadata'.
    """
    if repository_metadata is None:
        repository_metadata = load_repository_metadata()

    all_records = []
    all_compounds_data = [] 
    # Ensure row dictionary can handle Optional[str] for citation fields or use empty string for None
    compound_metadata: Dict[str, Dict[str, Any]] = {} 

    # Get thermopyl version
    current_thermopyl_version = thermopyl_version.short_version

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
                parts.append(f"{el}{round(amt, 3)}") # Reverted to round() for no trailing zero padding
        return "".join(parts)

    for file_path in xml_files:
        logger.info(f"Processing file: {file_path}")
        parsed_data = parse_thermoml_xml(file_path)
        # REMOVED: compound_metadata initialization was here, moved to function start

        for record in parsed_data:
            # Initialize row with Any to accommodate None then convert to string for DataFrame
            row: Dict[str, Any] = {
                "material_id": record.material_id,
                "components": ", ".join(record.components),
                "thermopyl_version": current_thermopyl_version, 
            }

            for var in record.variable_values:
                var_key_name = str(var.var_type).replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")
                row[f"var_{var_key_name}"] = str(var.values[0])
            
            for prop in record.property_values:
                prop_key_name = str(prop.prop_name).replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")
                row[f"prop_{prop_key_name}"] = str(prop.values[0])

            # ADDED: Citation information added to the row
            row["source_file"] = record.source_file # This is already a string
            if record.citation:
                row["doi"] = record.citation.get("sDOI")
                row["publication_year"] = record.citation.get("yrPubYr")
                row["title"] = record.citation.get("sTitle")
                
                s_authors_list = record.citation.get("sAuthor") 
                if s_authors_list and isinstance(s_authors_list, list) and len(s_authors_list) > 0:
                    first_author_full_string = s_authors_list[0]
                    row["author"] = first_author_full_string.split(';')[0].strip()
                else:
                    row["author"] = None 
                
                row["journal"] = record.citation.get("sPubName")
            else: # No citation object for this record
                row["doi"] = None
                row["publication_year"] = None
                row["title"] = None
                row["author"] = None
                row["journal"] = None

            # Convert None values in citation fields to empty strings for DataFrame consistency
            citation_keys = ["doi", "publication_year", "title", "author", "journal"]
            for key in citation_keys:
                if row[key] is None:
                    row[key] = "" # Or use pd.NA if you prefer pandas' NA type

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
                        # REMOVED: all_records.append(row)
                        # REMOVED: continue
                        # active_components should be set based on current_record_active_elements or other logic if pymatgen not available
                        # The existing active_components_str logic before this try-except block handles this.
                    else:
                        # Pymatgen is available, proceed with normalization:
                        if mole_fracs:
                            defined_elements_for_material = set(el for el in record.component_id_map.values() if el and Element.is_valid_symbol(el))
                            current_mole_frac_elements = set(mole_fracs.keys()) # Defined before potential modification
                            total_frac = sum(mole_fracs.values()) # Sum before potential modification

                            if len(current_mole_frac_elements) < len(defined_elements_for_material) and defined_elements_for_material.issuperset(current_mole_frac_elements):
                                missing_elements_set = defined_elements_for_material - current_mole_frac_elements
                                if len(missing_elements_set) == 1 and (0 < total_frac < 1.0): # MODIFIED: Changed condition from (0.95 <= total_frac < 1.0)
                                    missing_element = list(missing_elements_set)[0]
                                    inferred_fraction = 1.0 - total_frac
                                    if inferred_fraction > 1e-5:
                                        mole_fracs[missing_element] = inferred_fraction
                                        current_record_active_elements.add(missing_element)
                                        active_components_str = ", ".join(sorted(list(current_record_active_elements))) # Update active_components_str
                            elif not (0.99 < total_frac < 1.01) and not (abs(total_frac - 0.0) < 1e-9 and not mole_fracs) : # Check if sum is not close to 1 (unless it\'s empty and sum is 0)
                                logger.warning(f"Mole fractions for {record.material_id} ({mole_fracs}) sum to {total_frac}, not close to 1. Normalization might be inexact.")
                        
                            # This block is now correctly indented to be part of 'if mole_fracs:'
                            normalized_formula_str = pretty_formula(mole_fracs)
                            if normalized_formula_str:
                                try:
                                    final_elements_in_formula = set(Composition(normalized_formula_str).get_el_amt_dict().keys())
                                    active_components_str = ", ".join(sorted(list(final_elements_in_formula))) # Update active_components_str
                                except Exception as e: # Catch issues with Composition parsing if pretty_formula is odd
                                    logger.warning(f"Could not parse formula \'{normalized_formula_str}\' with Pymatgen for active component update: {e}")
                        # End of 'if mole_fracs:' block
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
                                            # Update active_components_str if a new element is inferred and added
                                            current_record_active_elements.add(missing_element)
                                            active_components_str = ", ".join(sorted(list(current_record_active_elements)))
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
                                        active_components_str = ", ".join(sorted(list(final_elements_in_formula))) # Update active_components_str
                                    except Exception as e:
                                        logger.warning(f"Material ID {record.material_id}: Could not parse formula '{normalized_formula_str}' with Pymatgen for active component update: {e}")

                                elif valid_mass_fracs: 
                                     active_components_str = ", ".join(sorted(list(valid_mass_fracs.keys()))) # Update active_components_str
                            else:
                                normalized_formula_str = ""
                                logger.warning(f"Material ID {record.material_id}: Total moles effectively zero for mass_fracs: {valid_mass_fracs}")
                                if valid_mass_fracs:
                                    active_components_str = ", ".join(sorted(list(valid_mass_fracs.keys())))
                    
                    row["normalized_formula"] = normalized_formula_str
                    row["active_components"] = active_components_str # Ensure row reflects the final active_components_str from normalization path
                    logger.debug(
                        f"Material ID {record.material_id}: Set row normalized_formula='{row.get('normalized_formula', '')}', "
                        f"active_components='{row.get('active_components', '')}'"
                    )

                except ImportError: # Should be caught by _is_pymatgen_available, but as a fallback
                    logger.error(f"Pymatgen import error during normalization for {record.material_id}.")
                    row["normalized_formula"] = ""
                except Exception as e:
                    logger.error(f"Normalization failed for {record.material_id}: {e}")
                    row["normalized_formula"] = ""
            
            all_records.append(row) # Row is now complete

            # ADDED: Process compound metadata for this record (using the global compound_metadata dict)
            current_citation_info_for_compound = {
                "source_file": record.source_file,
                "doi": record.citation.get("sDOI") if record.citation else None,
                "publication_year": record.citation.get("yrPubYr") if record.citation else None,
                "title": record.citation.get("sTitle") if record.citation else None,
                "journal": record.citation.get("sPubName") if record.citation else None,
            }
            s_authors_list_comp = record.citation.get("sAuthor") if record.citation else None
            if s_authors_list_comp and isinstance(s_authors_list_comp, list) and len(s_authors_list_comp) > 0:
                first_author_comp_full = s_authors_list_comp[0]
                current_citation_info_for_compound["author"] = first_author_comp_full.split(';')[0].strip()
            else:
                current_citation_info_for_compound["author"] = None

            for comp_name, comp_formula in record.compound_formulas.items():
                if comp_formula and comp_formula not in compound_metadata: # Add only if new
                    compound_metadata[comp_formula] = {
                        "name": comp_name,
                        **current_citation_info_for_compound 
                    }
        
        # REMOVED: Old logic for populating all_compounds_data from per-file compound_metadata


    # Create DataFrames from the collected records
    df = pd.DataFrame(all_records)
    
    # REMOVED: Old global citation assignment for df (approx lines 240-263 in original)
    # This includes initialization of citation_cols_for_df and the subsequent assignment block.
        
    # ADDED: Build all_compounds_data from the populated global compound_metadata
    for formula, data in compound_metadata.items():
        all_compounds_data.append({
            "symbol": formula, 
            "name": data["name"],
            "source_file": data.get("source_file"),
            "doi": data.get("doi"),
            "publication_year": data.get("publication_year"),
            "title": data.get("title"),
            "author": data.get("author"),
            "journal": data.get("journal"),
        })
    
    compounds_df = pd.DataFrame(all_compounds_data)
    # REMOVED: Old global citation assignment for compounds_df (approx lines 265-281 in original)
    # This includes initialization of citation_cols_for_comp_df and the subsequent assignment block.
    
    # Deduplicate compounds_df if necessary, e.g., based on 'symbol'
    if not compounds_df.empty:
        compounds_df = compounds_df.drop_duplicates(subset=['symbol']).reset_index(drop=True)

    logger.debug(f"Final DataFrame columns: {df.columns.tolist()}")
    if normalize_alloys and not df.empty:
        if "normalized_formula" in df.columns:
            logger.debug(f"Sample of normalized_formula: {df['normalized_formula'].head().tolist()}")
        else:
            logger.debug("'normalized_formula' column not present in the final DataFrame.")
        if "active_components" in df.columns:
            logger.debug(f"Sample of active_components: {df['active_components'].head().tolist()}")
        else:
            logger.debug("'active_components' column not present in the final DataFrame.")

    logger.debug(f"Repository metadata included in output: {repository_metadata}")
    return {
        "data": df,
        "compounds": compounds_df,
        "repository_metadata": repository_metadata
    }


def pandas_dataframe(path: str) -> pd.DataFrame:
    try:
        result = pd.read_hdf(os.path.join(path, "data.h5"), key="data")
        if isinstance(result, pd.Series):
            result = result.to_frame().T
        return result
    except Exception as e:
        print(f"Failed to load DataFrame from HDF5: {e}")
        return pd.DataFrame()
