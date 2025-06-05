import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import xmlschema
from collections import Counter


from thermopyl.core.schema import ThermoMLRecord, VariableValue, PropertyValue

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_tag(d: dict, key: str, ns: str) -> Any:
    return d.get(key) or d.get(f"{ns}{key}") or d.get(key.replace(f"{ns}", ""))

def parse_thermoml_xml(file_path: str, xsd_path: str = "thermopyl/data/ThermoML.xsd") -> List[ThermoMLRecord]:
    """
    Parse a ThermoML XML file into a list of ThermoMLRecord instances.

    Parameters
    ----------
    file_path : str
        Path to the XML file.
    xsd_path : str
        Path to the XML Schema Definition (XSD) file for validation.

    Returns
    -------
    List[ThermoMLRecord]
        List of parsed records with compounds, variables, and properties.
    """

    
    schema = xmlschema.XMLSchema(xsd_path)
    if not schema.is_valid(file_path):
        raise ValueError(f"{file_path} is not valid against the provided ThermoML schema.")

    data_dict = schema.to_dict(file_path)
    ns = "{http://www.iupac.org/namespaces/ThermoML}"

    # Unwrap root
    if len(data_dict) == 1:
        data_dict = list(data_dict.values())[0]

    compounds_section = get_tag(data_dict, "Compound", ns) or []
    pure_data_section = get_tag(data_dict, "PureOrMixtureData", ns) or []
    if not isinstance(pure_data_section, list):
        pure_data_section = [pure_data_section]

    compound_map = {}
    for compound in compounds_section:
        try:
            org_num = int(get_tag(get_tag(compound, "RegNum", ns), "nOrgNum", ns))
            name_entry = get_tag(compound, "sCommonName", ns)
            name = name_entry[0] if isinstance(name_entry, list) else name_entry
            formula = get_tag(compound, "sFormulaMolec", ns)
            compound_map[org_num] = {"name": name, "formula": formula}
            for k, v in compound_map.items():
                logger.debug(f"Compound {k}: name={v.get('name')}, formula={v.get('formula')}")
                    
        except Exception as e:
            logger.warning(f"Skipping invalid compound: {e}")
    
    for k, v in compound_map.items():
        logger.debug(f"Compound {k}: name={v.get('name')}, formula={v.get('formula')}")    

    results = []
    for entry in pure_data_section:
        try:
            component_ids = [
                str(get_tag(get_tag(c, "RegNum", ns), "nOrgNum", ns))
                for c in get_tag(entry, "Component", ns) or []
            ]
            material_id = "__".join(component_ids) if component_ids else "unknown"         
            components = []
            compound_formulas = {}

            for comp in get_tag(entry, "Component", ns) or []:
                regnum = get_tag(comp, "RegNum", ns)
                org_num = int(get_tag(regnum, "nOrgNum", ns))
                info = compound_map.get(org_num, {})
                name = info.get("name", f"Unknown-{org_num}")
                components.append(name)
                compound_formulas[name] = info.get("formula", "")

            prop_name_map = {}
            prop_phase_map = {}
            for prop in get_tag(entry, "Property", ns) or []:
                try:
                    num = int(get_tag(prop, "nPropNumber", ns))
                    group = get_tag(get_tag(prop, "Property-MethodID", ns), "PropertyGroup", ns)                    
                    group = (
                        get_tag(group, "VolumetricProp", ns)
                        or get_tag(group, "TransportProp", ns)
                        or get_tag(group, "ThermodynProp", ns)
                        or {}
                    )
                    name = get_tag(group, "ePropName", ns)
                    phase_entry = get_tag(prop, "PropPhaseID", ns)
                    phase = ""
                    if isinstance(phase_entry, list) and phase_entry:
                        phase = get_tag(phase_entry[0], "ePropPhase", ns)
                    prop_name_map[num] = name or "unknown"
                    prop_phase_map[num] = phase
                except Exception as e:
                    logger.debug(f"Skipping property due to: {e}")
                    continue

            var_type_map = {}
            for var in get_tag(entry, "Variable", ns) or []:
                try:
                    num = int(get_tag(var, "nVarNumber", ns))
                    vtype_entry = get_tag(get_tag(var, "VariableID", ns), "VariableType", ns)                  
                    if isinstance(vtype_entry, dict):
                        vtype = next((v for k, v in vtype_entry.items() if k.endswith("e")), "UnknownType")
                    else:
                        vtype = "UnknownType"                   
                    var_type_map[num] = vtype
                except Exception as e:
                    logger.debug(f"Skipping property due to: {e}")
                    continue

            variable_values = []
            property_values = []
            num_values = get_tag(entry, "NumValues", ns) or []
            num_values = num_values if isinstance(num_values, list) else [num_values]
           
            # Count occurrences of each variable type
            vtype_counts = Counter(var_type_map.values())

            for nv in num_values:
                for vv in get_tag(nv, "VariableValue", ns) or []:
                    try:
                        var_number = int(get_tag(vv, "nVarNumber", ns))
                        var_value = float(get_tag(vv, "nVarValue", ns))
                        vtype = var_type_map.get(var_number, "")
                        # Append variable number only if the variable type is not unique
                        if vtype_counts[vtype] > 1:
                            var_label = f"{vtype}_{var_number}"
                        else:
                            var_label = vtype                          
                        variable_values.append(VariableValue(var_type=var_label, values=[var_value], var_number=var_number))

                    except Exception as e:
                        logger.debug(f"Skipping property due to: {e}")
                        continue

                for pv in get_tag(nv, "PropertyValue", ns) or []:
                    try:
                        prop_number = int(get_tag(pv, "nPropNumber", ns))
                        prop_value = float(get_tag(pv, "nPropValue", ns))

                        uncertainty = None
                        u_block = get_tag(pv, "PropUncertainty", ns)
                        if isinstance(u_block, list) and u_block:
                            uncertainty = float(get_tag(u_block[0], "nStdUncertValue", ns) or 0.0)
                        elif isinstance(u_block, dict):
                            uncertainty = float(get_tag(u_block, "nStdUncertValue", ns) or 0.0)

                        property_values.append(PropertyValue(
                            prop_name=prop_name_map.get(prop_number, "unknown"),
                            values=[prop_value],
                            uncertainties=[uncertainty] if uncertainty is not None else []
                        ))
                    except Exception as e:
                        logger.debug(f"Skipping property due to: {e}")
                        continue

            record = ThermoMLRecord(
                material_id=str(material_id),
                components=components,
                compound_formulas=compound_formulas,
                variable_values=variable_values,
                property_values=property_values,
            )
            results.append(record)

        except Exception as e:
            logger.warning(f"Skipping entry due to error: {e}")
            continue

    return results
