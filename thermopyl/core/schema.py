from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class VariableValue:
    var_type: str
    values: List[float]
    var_number: Optional[int] = None  # New field


@dataclass
class PropertyValue:
    prop_name: str
    values: List[str]
    uncertainties: List[Optional[str]]

@dataclass
class ThermoMLRecord:
    material_id: str
    components: List[str]
    compound_formulas: Dict[str, str]
    variable_values: List[VariableValue]
    property_values: List[PropertyValue]

