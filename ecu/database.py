"""
OpenConsult - ECU Database
Original open-source diagnostic tool for Nissan vehicles (14-pin connector)

This module provides the ECU definitions, sensor tables, and DTC database.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SensorDefinition:
    """Definition of an ECU sensor"""
    name: str
    unit: str
    min_value: float
    max_value: float
    scaling_factor: float = 1.0
    offset: float = 0.0
    
    def decode(self, raw_value: int) -> float:
        """Decode raw value to physical value"""
        return (raw_value * self.scaling_factor) + self.offset


@dataclass
class DTCDefinition:
    """Definition of a Diagnostic Trouble Code"""
    code: str
    description: str
    severity: str  # "warning", "critical", "info"
    possible_causes: List[str]
    recommended_actions: List[str]


@dataclass
class ECUDefinition:
    """Definition of an Engine Control Unit"""
    name: str
    id_code: int
    protocol_version: str
    sensors: Dict[str, SensorDefinition]
    dtc_codes: Dict[str, DTCDefinition]


class ECUDatabase:
    """Database of Nissan ECU definitions for CONSULT-I protocol"""
    
    def __init__(self):
        self.ecus = {}
        self._initialize_ecu_definitions()
        
    def _initialize_ecu_definitions(self):
        """Initialize with known Nissan ECU definitions"""
        # Example ECU definition - would be expanded in real implementation
        ecu1 = ECUDefinition(
            name="ECM-01",
            id_code=0x01,
            protocol_version="CONSULT-I v2.3",
            sensors={
                "engine_rpm": SensorDefinition("Engine RPM", "RPM", 0, 8000),
                "vehicle_speed": SensorDefinition("Vehicle Speed", "km/h", 0, 250),
                "throttle_position": SensorDefinition("Throttle Position", "%", 0, 100),
                "coolant_temp": SensorDefinition("Coolant Temperature", "°C", -40, 150),
                "intake_air_temp": SensorDefinition("Intake Air Temp", "°C", -40, 120),
                "maf_sensor": SensorDefinition("MAF Sensor", "g/s", 0, 500),
                "oxygen_sensor": SensorDefinition("O2 Sensor", "V", 0, 1.5),
                # v0.69+ additions: Battery voltage monitoring for dashboard gauges
                "battery_voltage": SensorDefinition("Battery Voltage", "V", 8.0, 16.0),
            },
            dtc_codes={
                "P0300": DTCDefinition(
                    code="P0300",
                    description="Random/Multiple Cylinder Misfire Detected",
                    severity="critical",
                    possible_causes=[
                        "Faulty spark plugs",
                        "Ignition coil issues", 
                        "Fuel injector problems",
                        "Compression loss"
                    ],
                    recommended_actions=[
                        "Check spark plugs and wires",
                        "Test ignition coils",
                        "Verify fuel pressure",
                        "Perform compression test"
                    ]
                ),
                "P0420": DTCDefinition(
                    code="P0420", 
                    description="Catalyst System Efficiency Below Threshold (Bank 1)",
                    severity="warning",
                    possible_causes=[
                        "Failing catalytic converter",
                        "Oxygen sensor malfunction",
                        "Exhaust leak"
                    ],
                    recommended_actions=[
                        "Test oxygen sensors",
                        "Check for exhaust leaks",
                        "Inspect catalytic converter",
                        "Clear codes and test drive"
                    ]
                ),
                "P0171": DTCDefinition(
                    code="P0171",
                    description="System Too Lean (Bank 1)",
                    severity="warning", 
                    possible_causes=[
                        "Vacuum leak",
                        "Faulty MAF sensor",
                        "Low fuel pressure",
                        "Fuel filter clogged"
                    ],
                    recommended_actions=[
                        "Check for vacuum leaks",
                        "Test MAF sensor",
                        "Verify fuel pressure",
                        "Inspect fuel system"
                    ]
                ),
            }
        )
        
        self.ecus[ecu1.id_code] = ecu1
        
    def get_ecu(self, id_code: int) -> Optional[ECUDefinition]:
        """Get ECU definition by ID code"""
        return self.ecus.get(id_code)
    
    def get_sensor_definition(self, ecu_id: int, sensor_name: str) -> Optional[SensorDefinition]:
        """Get sensor definition for a specific ECU"""
        ecu = self.ecus.get(ecu_id)
        if ecu and sensor_name in ecu.sensors:
            return ecu.sensors[sensor_name]
        return None
    
    def get_dtc_definition(self, dtc_code: str) -> Optional[DTCDefinition]:
        """Get DTC definition by code"""
        for ecu in self.ecus.values():
            if dtc_code in ecu.dtc_codes:
                return ecu.dtc_codes[dtc_code]
        return None
    
    def list_ecus(self) -> List[str]:
        """List all available ECU names"""
        return [ecu.name for ecu in self.ecus.values()]
    
    def list_sensors(self, ecu_id: int) -> List[str]:
        """List all sensors for a specific ECU"""
        ecu = self.ecus.get(ecu_id)
        if ecu:
            return list(ecu.sensors.keys())
        return []
    
    def list_dtc_codes(self, ecu_id: int) -> List[str]:
        """List all DTC codes for a specific ECU"""
        ecu = self.ecus.get(ecu_id)
        if ecu:
            return list(ecu.dtc_codes.keys())
        return []


# Example usage and testing
if __name__ == "__main__":
    print("ECU Database")
    print("=" * 40)
    
    db = ECUDatabase()
    
    # List available ECUs
    ecus = db.list_ecus()
    print(f"Available ECUs: {ecus}")
    
    # Get sensor definitions for first ECU
    if ecus:
        first_ecu_id = 1  # Assuming first ECU has ID 1
        sensors = db.list_sensors(first_ecu_id)
        print(f"Sensors for {ecus[0]}: {sensors}")
        
        # Get specific sensor definition
        rpm_sensor = db.get_sensor_definition(first_ecu_id, "engine_rpm")
        if rpm_sensor:
            print(f"Engine RPM range: {rpm_sensor.min_value} - {rpm_sensor.max_value} {rpm_sensor.unit}")
    
    # List DTC codes
    dtc_codes = db.list_dtc_codes(1)
    print(f"DTC codes for ECM-01: {dtc_codes}")
    
    # Get specific DTC definition
    p0300_def = db.get_dtc_definition("P0300")
    if p0300_def:
        print(f"P0300 Description: {p0300_def.description}")
        print(f"Severity: {p0300_def.severity}")
    
    print("\nECU database ready!")