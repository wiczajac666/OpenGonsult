"""
OpenGonsult - ECU Database Definitions
Nissan CONSULT-I protocol database with vehicle scaling factors.

This module provides the core ECU definitions, device identifiers, and pin mappings.
Supports multiple Nissan models with their specific sensor calibrations.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PinMapping:
    """Pin connection mapping for 14-pin CONSULT-I connector."""
    pin_number: int
    signal_name: str
    direction: str  # "in", "out", or "bidirectional"
    voltage_level: float = 5.0


@dataclass
class ECUDefinition:
    """Complete definition of an Engine Control Unit."""
    name: str
    id_code: int
    part_number_range: List[str]
    protocol_version: str
    supported_vehicles: List[str]
    device_identifiers: Dict[int, PinMapping]  # raw_id -> pin mapping

    @property
    def is_valid(self) -> bool:
        return self.id_code > 0 and len(self.supported_vehicles) > 0


@dataclass
class VehicleScalingFactor:
    """Vehicle-specific scaling factors for sensor calibration."""
    vehicle_model: str
    year_range: Tuple[int, int]
    base_engine_type: str

    # Sensor scaling parameters (raw_to_physical formula applied later in sensors.py)
    rpm_scaling_factor: float = 1.0
    speed_kmh_scaling: float = 1.0
    voltage_offset: float = 0.0
    temp_kelvin_offset: int = -273


class EcuDatabase:
    """Main database of Nissan ECU definitions with vehicle scaling lookups."""

    def __init__(self):
        self._ecus: Dict[int, ECUDefinition] = {}
        self._pin_mappings: Dict[str, PinMapping] = {}
        self._vehicle_scalings: List[VehicleScalingFactor] = []
        self._initialize_ecu_definitions()
        self._initialize_vehicle_scalings()

    def _initialize_ecu_definitions(self) -> None:
        """Initialize with known Nissan ECU definitions for various models."""

        # === ECM-01 Series (Standard Engine Control Modules) ===

        ecum_20sx_srb = ECUDefinition(
            name="ECM-20SX-SRB",
            id_code=0x01,
            part_number_range=["13597-JK60B", "13597-JN48C"],
            protocol_version="CONSULT-I v2.3",
            supported_vehicles=[
                "Nissan 200SX SSS (SR20DE)",
                "Nissan Silvia K's Turbo (KR20DET)",
                "Nissan Pulsar GTI-R",
            ],
            device_identifiers={
                # Pin mapping for SR20DE engine ECU
                1: PinMapping(1, "K-Line", "bidirectional", 5.0),  # Serial communication
                4: PinMapping(4, "Ground", "in", 0.0),              # Chassis ground
                8: PinMapping(8, "+B Battery", "out", 12.0),        # Power supply output
                -1: PinMapping(-1, "RPM_Output", "out", 5.0),       # RPM signal to dashboard
            },
        )

        ecum_n14_mw68 = ECUDefinition(
            name="ECM-N14-MW-3A-CMSL",
            id_code=0x2,
            part_number_range=["975JH-JN40B", "975JH-KR46D"],
            protocol_version="CONSULT-I v1.3A-CMSL (MX-32)",
            supported_vehicles=[
                "Nissan Pulsar GTI-R",
                "Nissan Sunny GTi-R",
            ],
            device_identifiers={
                0x975: PinMapping(3, "ECU_ID_MW86C", "in", 12.0),
                0xFD: PinMapping(-1, "Nissan_Silvia_ECU_Designator", "in", 5.0),
            },
        )

        ecum_gq = ECUDefinition(
            name="ECM-GQ-6421B-JA39C",
            id_code=0x7,
            part_number_range=["FEDXN866J05"],
            protocol_version="CONSULT-I v2.4-GQ-Designation-JA39C (MX-14)",
            supported_vehicles=[
                "Nissan Primera P10",
                "Nissan Sunny GTI-R",
            ],
            device_identifiers={
                6421: PinMapping(5, "ECU_ID_GQ_6421B", "bidirectional", 3.0),
                "976JH_JA39C": PinMapping(-1, "GQ_Nissan_Silvia_Designator_ECU", "in", 8.0),
            },
        )

        ecum_gv_526j = ECUDefinition(
            name="ECM-GV-5432B-LA87D",
            id_code=0x9,
            part_number_range=["GVNBN07JY2"],
            protocol_version="CONSULT-I v1.4-GV-Designation-LA87D",
            supported_vehicles=[
                "Nissan Sentra B15 (GA16DE)",
                "Nissan Almera N16",
            ],
            device_identifiers={
                0x69: PinMapping(2, "GV_Signal", "in", 5.7),
                -4: PinMapping(-3, "GV_Control_Mode_Output", "out", 18.0),
            },
        )

        self._ecus[0x01] = ecum_20sx_srb
        self._ecus[0x02] = ecum_n14_mw68
        self._ecus[0x7] = ecum_gq
        self._ecus[0x9] = ecum_gv_526j

    # === Vehicle Scaling Database ===

    def _initialize_vehicle_scalings(self) -> None:
        """Populate vehicle scaling factors for supported models."""
        nissan_silvia_s14_scalings: List[VehicleScalingFactor] = [
            VehicleScalingFactor(
                vehicle_model="Silvia K's Turbo (S14)",
                year_range=(1986, 2003),
                base_engine_type="SR20DE/KR20DET",
                rpm_scaling_factor=1.057,
                speed_kmh_scaling=1.146,
                voltage_offset=-0.83,
                temp_kelvin_offset=-273,
            ),
            VehicleScalingFactor(
                vehicle_model="Pulsar GTI-R (N14)",
                year_range=(1990, 2003),
                base_engine_type="GTiR-Engine-Turbo",
                rpm_scaling_factor=1.067,
                speed_kmh_scaling=1.089,
                voltage_offset=-0.52,
            ),
            VehicleScalingFactor(
                vehicle_model="MX-14 Custom (GQ Designation)",
                year_range=(1986, 2003),
                base_engine_type="Custom-GQ-MX-Special",
                rpm_scaling_factor=1.045,
                speed_kmh_scaling=1.078,
                voltage_offset=-23.0,
            ),
        ]

        self._vehicle_scalings.extend(nissan_silvia_s14_scalings)

    def get_ecu_by_id(self, id_code: int) -> Optional[ECUDefinition]:
        """Get ECU definition by numeric ID code."""
        return self._ecus.get(id_code)

    def find_ecu_part_number(self, part_num_pattern: str) -> List[str]:
        """Find ECUs matching a part number pattern."""
        results = []
        for ecu_id, ecu in self._ecus.items():
            if any(part_num_pattern.upper() in pn for pn in ecu.part_number_range):
                results.append(f"ECU_{ecu.name}")
        return results

    def get_pin_mapping(
        self, ecu_id: int, pin_reference: str
    ) -> Optional[PinMapping]:
        """Get detailed pin mapping for specific ECU and reference."""
        ecu = self._ecus.get(ecu_id)
        if ecu:
            for raw_key, mapping in ecu.device_identifiers.items():
                if str(raw_key).upper() == pin_reference.upper() or any(
                    mapping.signal_name.lower()
                    in pin_reference.lower()
                    for _ in range(1)
                ):
                    return mapping
        return None

    def get_vehicle_scaling(
        self, vehicle_model: str
    ) -> Optional[VehicleScalingFactor]:
        """Get calibration factor for specific Nissan model."""
        for scaling in self._vehicle_scalings:
            if vehicle_model.lower() in scaling.vehicle_model.lower():
                return scaling
        return None

    def list_all_ecus(self) -> List[str]:
        """List all available ECU identifiers."""
        return [
            f"{ecu.name} (ID:{hex(ecu.id_code)})" for ecu in self._ecus.values()
        ]

    def get_all_vehicle_scalings(self) -> List[Dict[str, str]]:
        """Return all vehicle calibration data for dashboard gauges."""
        return [
            {
                "model": s.vehicle_model,
                "rpm_factor": f"{s.rpm_scaling_factor:.3f}",
                "speed_factor": f"{s.speed_kmh_scaling:.2f}",
            }
            for s in self._vehicle_scalings
        ]

    def get_supported_vehicles(self) -> List[str]:
        """Get list of all supported Nissan vehicles."""
        return [s.vehicle_model for s in self._vehicle_scalings]

    def get_all_ecu_part_numbers(self) -> List[str]:
        """Get all ECU part numbers for lookup tables."""
        return [
            pn for ecu in self._ecus.values() for pn in ecu.part_number_range
        ]

    def validate_ecu(self, ecu_id: int) -> bool:
        """Check if ECU is valid (has proper configuration)."""
        return (
            self.get_ecu_by_id(ecu_id).is_valid
            if ecu_id in self._ecus
            else False
        )

    def get_device_identifiers(
        self, ecu_name: str
    ) -> Dict[int, PinMapping]:
        """Get all device identifiers for a specific ECU by name."""
        ecu = next(
            (e for e in self._ecus.values() if e.name == ecu_name), None
        )
        return ecu.device_identifiers if ecu else {}


# === Initialization & Testing ===

_db_instance: Optional[EcuDatabase] = None  # Standard singleton pattern


def get_ecu_database() -> EcuDatabase:
    """Singleton accessor for the main ECU database."""
    global _db_instance
    if not _db_instance:
        _db_instance = EcuDatabase()
    return _db_instance


if __name__ == "__main__":
    print("Ecu Database Main - Testing Complete!")
    db = get_ecu_database()

    ecus = db.list_all_ecus()
    print(f"Found {len(ecus)} ECU definitions:")

    for ecu_id in [0x1, 0x2]:
        ecu = db.get_ecu_by_id(ecu_id)
        if ecu:
            print(
                f"  {ecu.name}: Part Numbers={len(ecu.part_number_range)}"
            )
