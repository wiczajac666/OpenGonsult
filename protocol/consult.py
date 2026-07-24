"""
OpenConsult - CONSULT-I Protocol Implementation
Original open-source diagnostic tool for Nissan vehicles (14-pin connector)

This module implements the CONSULT-I communication protocol.
"""

import struct
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ConsultPacket:
    """Base class for CONSULT-I packets"""
    header: bytes = b'\x02'  # STX (Start of Text)
    payload: bytes = b''
    
    def to_bytes(self) -> bytes:
        """Convert packet to bytes with checksum"""
        data = self.header + self.payload
        checksum = calculate_checksum(data)
        return data + bytes([checksum])


@dataclass 
class RequestPacket(ConsultPacket):
    """Request packet to ECU"""
    mode: int = 0x81  # Default diagnostic mode
    
    def encode(self, sub_function: int, data: List[int] = None) -> bytes:
        """Encode request with sub-function and optional data"""
        if data is None:
            data = []
        
        payload = bytes([self.mode, sub_function]) + bytes(data)
        self.payload = payload
        return super().to_bytes()


@dataclass
class ResponsePacket(ConsultPacket):
    """Response packet from ECU"""
    response_code: int = 0x41
    
    def decode(self) -> Tuple[int, List[int]]:
        """Decode response to get sub-function and data"""
        if len(self.payload) < 2:
            raise ValueError("Invalid response format")
            
        sub_function = self.payload[0]
        data = list(self.payload[1:])
        return sub_function, data


@dataclass
class DiagnosticPacket(ConsultPacket):
    """Diagnostic mode packet"""
    
    def encode_diagnostic_request(self, diagnostic_mode: int, 
                                  address_high: int, address_low: int,
                                  length: int) -> bytes:
        """Encode diagnostic request with memory address and length"""
        payload = bytes([diagnostic_mode, 0x81]) + \
                  struct.pack('>H', (address_high << 8) | address_low) + \
                  bytes([length])
        self.payload = payload
        return super().to_bytes()


def calculate_checksum(data: bytes) -> int:
    """Calculate XOR checksum for CONSULT-I protocol"""
    checksum = 0x00
    for byte in data:
        checksum ^= byte
    return checksum & 0xFF


def validate_packet(packet_data: bytes) -> bool:
    """Validate packet integrity using checksum"""
    if len(packet_data) < 3:  # Minimum: header + at least one payload byte + checksum
        return False
    
    expected_checksum = packet_data[-1]
    actual_checksum = calculate_checksum(packet_data[:-1])
    
    return expected_checksum == actual_checksum


def format_hex(data: bytes) -> str:
    """Format bytes as hex string"""
    return ' '.join(f'{byte:02X}' for byte in data)


# Example usage and testing
if __name__ == "__main__":
    print("OpenConsult Protocol Implementation")
    print("=" * 40)
    
    # Test packet creation
    request = RequestPacket()
    encoded_request = request.encode(0x21, [0x00, 0x30])
    print(f"Encoded request: {format_hex(encoded_request)}")
    
    # Test checksum calculation
    test_data = b'\x02\x81\x21\x00\x30'
    checksum = calculate_checksum(test_data)
    print(f"Checksum for {format_hex(test_data)}: {checksum:02X}")
    
    # Test packet validation
    valid_packet = encoded_request + bytes([calculate_checksum(encoded_request)])
    is_valid = validate_packet(valid_packet)
    print(f"Packet validation: {'✓ Valid' if is_valid else '✗ Invalid'}")
    
    print("\nProtocol implementation ready!")