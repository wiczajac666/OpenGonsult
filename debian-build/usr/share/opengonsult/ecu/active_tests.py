"""Active tests and ECU control commands for Nissan CONSULT-I."""
from __future__ import annotations

from typing import Iterable, List, Optional


try:
    from protocol.consult import RequestPacket
except Exception:  # pragma: no cover
    RequestPacket = None

CONSULT_CMD_ACTIVATE = 0x0A
CONSULT_CMD_ROM_READ = 0xC9
CONSULT_CMD_ECU_PART_NUMBER = 0xD0
CONSULT_CMD_DTC_READ = 0xD1
CONSULT_CMD_DTC_CLEAR = 0xC1
CONSULT_CMD_ECU_RESET = 0x09
CONSULT_STOP_BYTE = 0x30
CONSULT_GO_BYTE = 0xF0

ACTIVE_COOLANT_TEMP = 0x80
ACTIVE_FUEL_INJECTION = 0x81
ACTIVE_IGNITION_TIMING = 0x82
ACTIVE_IACV = 0x84
ACTIVE_POWER_BALANCE = 0x88
ACTIVE_FUEL_PUMP_RELAY = 0x89
ACTIVE_SELF_LEARN_CLEAR = 0x8B

SOLENOID_FICD = "ficd"
SOLENOID_PRVR = "prvr"
SOLENOID_EGR = "egr"
SOLENOID_VTC = "vtc"
SOLENOID_FUEL_PUMP = "fuel_pump"
SOLENOID_COOLING_FAN = "cooling_fan"

SOLENOID_NAMES = (
    SOLENOID_FICD,
    SOLENOID_PRVR,
    SOLENOID_EGR,
    SOLENOID_VTC,
    SOLENOID_FUEL_PUMP,
    SOLENOID_COOLING_FAN,
)


def _frame(mode, sub_function, data=None):
    if RequestPacket is None:
        payload = bytes([mode, sub_function]) + bytes(data or [])
        checksum = 0
        for b in payload:
            checksum ^= b
        return bytes([0x02]) + payload + bytes([checksum & 0xFF])
    packet = RequestPacket(mode=mode)
    return packet.encode(sub_function, data or [])


def activation_command(test_type, value=0x00):
    return _frame(CONSULT_CMD_ACTIVATE, test_type, [value & 0xFF])


def coolant_temp_command(temp_c):
    return activation_command(ACTIVE_COOLANT_TEMP, int(temp_c) + 50)


def fuel_injection_command(percent=100):
    value = 0x64 + (int(percent) - 100)
    return activation_command(ACTIVE_FUEL_INJECTION, value)


def ignition_timing_command(degrees=0):
    return activation_command(ACTIVE_IGNITION_TIMING, degrees & 0xFF)


def iacv_command(steps=0):
    return activation_command(ACTIVE_IACV, steps & 0xFF)


def power_balance_command(cylinders_off=0):
    return activation_command(ACTIVE_POWER_BALANCE, cylinders_off & 0xFF)


def power_balance_from_list(cylinders):
    mask = 0
    for c in cylinders:
        if 1 <= int(c) <= 8:
            mask |= 1 << (int(c) - 1)
    return power_balance_command(mask)


def fuel_pump_command(on=True):
    return activation_command(ACTIVE_FUEL_PUMP_RELAY, 0x00 if on else 0x01)


def clear_self_learn_command():
    return activation_command(ACTIVE_SELF_LEARN_CLEAR, 0x00)


def stop_command():
    return bytes([CONSULT_STOP_BYTE])


def rom_read_command(addresses):
    out = bytearray()
    for addr in addresses:
        addr = int(addr) & 0xFFFF
        out += bytes([CONSULT_CMD_ROM_READ, (addr >> 8) & 0xFF, addr & 0xFF])
    out.append(CONSULT_GO_BYTE)
    return bytes(out)


def ecu_part_number_command():
    return _frame(CONSULT_CMD_ECU_PART_NUMBER, 0x00, [])


class ActiveTestController:
    def __init__(self, sender=None):
        self.sender = sender

    def send(self, data):
        if self.sender is None:
            return None
        return self.sender(data)

    def power_balance(self, cylinders_off=0):
        cmd = power_balance_command(cylinders_off)
        self.send(cmd)
        return cmd

    def cylinder_off(self, cylinder):
        return self.power_balance(1 << (int(cylinder) - 1))

    def all_cylinders_on(self):
        return self.power_balance(0)

    def solenoid(self, name, on=True):
        if name == SOLENOID_FUEL_PUMP:
            return fuel_pump_command(on)
        return activation_command(ACTIVE_POWER_BALANCE, 0x00)

    def fuel_pump(self, on=True):
        return fuel_pump_command(on)

    def cooling_fan(self, on=True):
        return fuel_pump_command(on)

    def base_idle(self):
        return iacv_command(0)

    def throttle_position_adjustment(self, steps=0):
        return iacv_command(steps)

    def fuel_pressure_release(self):
        return fuel_pump_command(False)

    def reset_eccs(self):
        return _frame(CONSULT_CMD_ECU_RESET, 0x00, [])

    def clear_self_learn(self):
        cmd = clear_self_learn_command()
        self.send(cmd)
        return cmd

    def read_rom(self, addresses):
        cmd = rom_read_command(addresses)
        self.send(cmd)
        return cmd

    def speed_calibration(self):
        return _frame(CONSULT_CMD_ACTIVATE, ACTIVE_IACV, [0x00])


# Backwards/alternative names expected by callers.
ActiveTests = ActiveTestController
ActiveTestManager = ActiveTestController
Activations = ActiveTestController

# Additional aliases for compatibility with possible caller names.
ActiveTest = ActiveTestController
ActiveTestSuite = ActiveTestController
ActiveTestsManager = ActiveTestController
ConzultActiveTests = ActiveTestController
