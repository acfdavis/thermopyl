import xmlschema
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import argparse
import pprint

# === Data Models ===
@dataclass
class VariableValue:
    var_number: int
    var_type: str
    value: float

@dataclass
class PropertyValue:
    prop_number: int
    prop_name: str
    phase: str
    value: float
    uncertainty: Optional[float]

@dataclass
class NumValuesRecord:
    variable_values: List[VariableValue]
    property_values: List[PropertyValue]

@dataclass
class ThermoMLData:
    material_id: int
    components: List[str]
    values: List[NumValuesRecord]
    metadata: Dict[str, Any]


# === Loader ===
def load_thermoml_data(xml_path: str, xsd_path: str = "ThermoML.xsd") -> List[ThermoMLData]:
    schema = xmlschema.XMLSchema(xsd_path)
    data_dict = schema.to_dict(xml_path)
    ns = "{http://www.iupac.org/namespaces/ThermoML}"

    # Build compound map
    compound_map = {}
    for compound in data_dict.get(f"{ns}Compound", []):
        org_num = int(compound[f"{ns}RegNum"][f"{ns}nOrgNum"])
        name = compound[f"{ns}sCommonName"][0]
        formula = compound.get(f"{ns}sFormulaMolec", "")
        compound_map[org_num] = {"name": name, "formula": formula}

    pure_data = data_dict.get(f"{ns}PureOrMixtureData", [])
    if not isinstance(pure_data, list):
        pure_data = [pure_data]

    results = []
    for entry in pure_data:
        data_number = int(entry.get(f"{ns}nPureOrMixtureDataNumber", -1))
        components = []
        for comp in entry.get(f"{ns}Component", []):
            org_num = int(comp[f"{ns}RegNum"][f"{ns}nOrgNum"])
            name = compound_map.get(org_num, {}).get("name", f"Unknown-{org_num}")
            components.append(name)

        # Parse properties
        prop_name_map = {}
        prop_phase_map = {}
        for prop in entry.get(f"{ns}Property", []):
            num = int(prop.get(f"{ns}nPropNumber"))
            name = prop[f"{ns}Property-MethodID"][f"{ns}PropertyGroup"][f"{ns}TransportProp"][f"{ns}ePropName"]
            phase = prop.get(f"{ns}PropPhaseID", [{}])[0].get(f"{ns}ePropPhase", "")
            prop_name_map[num] = name
            prop_phase_map[num] = phase

        # Parse variables
        var_type_map = {}
        for var in entry.get(f"{ns}Variable", []):
            num = int(var[f"{ns}nVarNumber"])
            vtype = var[f"{ns}VariableID"][f"{ns}VariableType"][f"{ns}eComponentComposition"] if f"{ns}eComponentComposition" in var[f"{ns}VariableID"][f"{ns}VariableType"] else var[f"{ns}VariableID"][f"{ns}VariableType"][f"{ns}eTemperature"]
            var_type_map[num] = vtype

        num_values = entry.get(f"{ns}NumValues", [])
        if not isinstance(num_values, list):
            num_values = [num_values]

        records = []
        for nv in num_values:
            var_vals = []
            for vv in nv.get(f"{ns}VariableValue", []):
                if not isinstance(vv, dict): continue
                try:
                    var_number = int(vv.get(f"{ns}nVarNumber"))
                    var_value = float(vv.get(f"{ns}nVarValue"))
                    vtype = var_type_map.get(var_number, "")
                    var_vals.append(VariableValue(var_number, vtype, var_value))
                except (TypeError, ValueError):
                    continue

            prop_vals = []
            for pv in nv.get(f"{ns}PropertyValue", []):
                if not isinstance(pv, dict): continue
                try:
                    prop_number = int(pv.get(f"{ns}nPropNumber"))
                    prop_value = float(pv.get(f"{ns}nPropValue"))
                    uncertainty = pv.get(f"{ns}CombinedUncertainty", {}).get(f"{ns}nCombExpandUncertValue")
                    uncertainty = float(uncertainty) if uncertainty is not None else None
                    prop_vals.append(PropertyValue(
                        prop_number=prop_number,
                        prop_name=prop_name_map.get(prop_number, "unknown"),
                        phase=prop_phase_map.get(prop_number, ""),
                        value=prop_value,
                        uncertainty=uncertainty
                    ))
                except (TypeError, ValueError):
                    continue

            records.append(NumValuesRecord(variable_values=var_vals, property_values=prop_vals))

        metadata = {
            "sCompiler": entry.get(f"{ns}sCompiler", ""),
            "sContributor": entry.get(f"{ns}sContributor", ""),
            "dateDateAdded": entry.get(f"{ns}dateDateAdded", ""),
            "eExpPurpose": entry.get(f"{ns}eExpPurpose", "")
        }

        results.append(ThermoMLData(
            material_id=data_number,
            components=components,
            values=records,
            metadata=metadata
        ))

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
