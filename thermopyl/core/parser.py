import xmlschema
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import argparse
import json

# === Data Models ===

@dataclass
class VariableValue:
    """Represents a single variable measurement (e.g., temperature)"""
    var_number: int
    var_type: str
    value: float

@dataclass
class PropertyValue:
    """Represents a single property measurement (e.g., density)"""
    prop_number: int
    prop_name: str
    phase: str
    value: float
    uncertainty: Optional[float]

@dataclass
class NumValuesRecord:
    """Represents a single measurement record containing variable and property values"""
    variable_values: List[VariableValue]
    property_values: List[PropertyValue]

@dataclass
class ThermoMLData:
    """Encapsulates all data from one PureOrMixtureData entry"""
    material_id: int
    components: List[str]
    values: List[NumValuesRecord]
    metadata: Dict[str, Any]
    compound_formulas: Dict[str, str]

# === Helper Functions ===

def get_tag(d: dict, key: str, ns: str) -> Any:
    """Bracket-aware tag lookup with namespace fallback"""
    return d.get(key) or d.get(f"{ns}{key}") or d.get(key.replace(f"{ns}", ""))

# === XML Parser ===

def load_thermoml_data(xml_path: str, xsd_path: str = "ThermoML.xsd") -> List[ThermoMLData]:
    schema = xmlschema.XMLSchema(xsd_path)
    data_dict = schema.to_dict(xml_path)
    ns = "{http://www.iupac.org/namespaces/ThermoML}"

    # Unwrap root if necessary
    if len(data_dict) == 1:
        data_dict = list(data_dict.values())[0]

    print(f"Top-level keys in parsed XML: {list(data_dict.keys())}")

    # Locate top-level sections
    compounds_section = data_dict.get("Compound") or data_dict.get(f"{ns}Compound") or []
    pure_data_section = data_dict.get("PureOrMixtureData") or data_dict.get(f"{ns}PureOrMixtureData") or []

    print(f"Found {len(compounds_section) if compounds_section else 0} compounds")
    print(f"Found {len(pure_data_section) if isinstance(pure_data_section, list) else 1 if pure_data_section else 0} PureOrMixtureData entries")

    compound_map = {}
    for compound in compounds_section:
        try:
            regnum = get_tag(compound, "RegNum", ns)
            org_num = int(get_tag(regnum, "nOrgNum", ns))
            name_entry = get_tag(compound, "sCommonName", ns)
            name = name_entry[0] if isinstance(name_entry, list) else name_entry
            formula = get_tag(compound, "sFormulaMolec", ns)
            compound_map[org_num] = {"name": name, "formula": formula}
        except Exception as e:
            print(f"Warning: Skipping compound due to error: {e}")
            continue

    # Normalize data structure
    pure_data = pure_data_section if isinstance(pure_data_section, list) else [pure_data_section]

    results = []
    for entry in pure_data:
        try:
            data_number = int(get_tag(entry, "nPureOrMixtureDataNumber", ns) or -1)
            components = []
            compound_formulas = {}

            # Extract components
            for comp in get_tag(entry, "Component", ns) or []:
                try:
                    regnum = get_tag(comp, "RegNum", ns)
                    org_num = int(get_tag(regnum, "nOrgNum", ns))
                    cdata = compound_map.get(org_num, {})
                    name = cdata.get("name", f"Unknown-{org_num}")
                    formula = cdata.get("formula", "")
                    components.append(name)
                    compound_formulas[name] = formula
                except Exception:
                    continue

            # Build property/phase maps
            prop_name_map = {}
            prop_phase_map = {}
            for prop in get_tag(entry, "Property", ns) or []:
                try:
                    num = int(get_tag(prop, "nPropNumber", ns))
                    group = get_tag(get_tag(prop, "Property-MethodID", ns), "PropertyGroup", ns)
                    group = get_tag(group, "VolumetricProp", ns) or get_tag(group, "TransportProp", ns) or {}
                    name = get_tag(group, "ePropName", ns) or "unknown"
                    phase_entry = get_tag(prop, "PropPhaseID", ns)
                    phase = phase_entry[0].get(f"{ns}ePropPhase") if isinstance(phase_entry, list) else ""
                    prop_name_map[num] = name
                    prop_phase_map[num] = phase
                except Exception:
                    continue

            # Variable mapping
            var_type_map = {}
            for var in get_tag(entry, "Variable", ns) or []:
                try:
                    num = int(get_tag(var, "nVarNumber", ns))
                    vtype_entry = get_tag(get_tag(var, "VariableID", ns), "VariableType", ns)
                    vtype = next((v for k, v in vtype_entry.items() if k.startswith(f"{ns}e")), "")
                    var_type_map[num] = vtype
                except Exception:
                    continue

            # Data records
            num_values = get_tag(entry, "NumValues", ns) or []
            num_values = num_values if isinstance(num_values, list) else [num_values]
            records = []

            for nv in num_values:
                var_vals = []
                for vv in get_tag(nv, "VariableValue", ns) or []:
                    try:
                        var_number = int(get_tag(vv, "nVarNumber", ns))
                        var_value = float(get_tag(vv, "nVarValue", ns))
                        vtype = var_type_map.get(var_number, "")
                        var_vals.append(VariableValue(var_number, vtype, var_value))
                    except Exception:
                        continue

                prop_vals = []
                for pv in get_tag(nv, "PropertyValue", ns) or []:
                    try:
                        prop_number = int(get_tag(pv, "nPropNumber", ns))
                        prop_value = float(get_tag(pv, "nPropValue", ns))

                        # Handle uncertainty from list or dict
                        uncertainty_block = get_tag(pv, "PropUncertainty", ns)
                        uncertainty = None
                        if isinstance(uncertainty_block, list):
                            uncertainty = float(get_tag(uncertainty_block[0], "nStdUncertValue", ns) or 0.0)
                        elif isinstance(uncertainty_block, dict):
                            uncertainty = float(get_tag(uncertainty_block, "nStdUncertValue", ns) or 0.0)

                        prop_vals.append(PropertyValue(
                            prop_number=prop_number,
                            prop_name=prop_name_map.get(prop_number, "unknown"),
                            phase=prop_phase_map.get(prop_number, ""),
                            value=prop_value,
                            uncertainty=uncertainty
                        ))
                    except Exception:
                        continue

                records.append(NumValuesRecord(variable_values=var_vals, property_values=prop_vals))

            metadata = {
                "sCompiler": get_tag(entry, "sCompiler", ns),
                "sContributor": get_tag(entry, "sContributor", ns),
                "dateDateAdded": get_tag(entry, "dateDateAdded", ns),
                "eExpPurpose": get_tag(entry, "eExpPurpose", ns)
            }

            results.append(ThermoMLData(
                material_id=data_number,
                components=components,
                values=records,
                metadata=metadata,
                compound_formulas=compound_formulas
            ))

        except Exception as e:
            print(f"Warning: Skipping entry due to error: {e}")
            continue

    return results

# === CLI Entrypoint ===

def main():
    parser = argparse.ArgumentParser(description="Extract data from ThermoML XML file.")
    parser.add_argument("--file", required=True, help="Path to ThermoML XML file")
    parser.add_argument("--schema", default="ThermoML.xsd", help="Path to ThermoML XSD file")
    args = parser.parse_args()

    data = load_thermoml_data(args.file, args.schema)
    for record in data:
        print(f"\nMaterial ID: {record.material_id}")
        print(f"Components: {', '.join(record.components)}")
        print(f"Metadata: {record.metadata}")
        for val in record.values[:3]:
            print("  Variables:")
            for v in val.variable_values:
                print(f"    {v.var_type} = {v.value}")
            print("  Properties:")
            for p in val.property_values:
                print(f"    {p.prop_name} ({p.phase}): {p.value} ± {p.uncertainty}")

if __name__ == "__main__":
    main()
