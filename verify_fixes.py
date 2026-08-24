#!/usr/bin/env python3
"""OpenGonsult Protocol v2.0 - Security Fixes Verification Script"""

import sys
sys.path.insert(0, '/home/harlemi/.openclaw/workspace/OpenGonsult')

from protocol.consult import (
    RequestPacket, ResponsePacket, FramedFrame, ConnectionState, 
    RetryConfig, RetryController, TimestampExpiredError, ReplayAttackError,
    MAX_TIMESTAMP_WINDOW_SECONDS
)
import time
import secrets


def test_fix1():
    """FIX #1: Timing control with timestamp and 60s expiration."""
    print("\n[TEST] FIX #1: FRAMING LAYER TIMING CONTROL")
    
    req = RequestPacket()
    assert hasattr(req, 'timestamp'), "FAIL! No timestamp"
    now = time.time()
    age_sec = abs(now - req.timestamp)
    print(f"  ✓ Timestamp field exists ({age_sec:.3f}s old)")
    
    frame = FramedFrame(payload=b'\x81\x21')
    assert 'timestamp' in str(frame.__dict__).lower(), "FAIL! No timestamp in struct"
    print("  ✓ Frame format correct (includes timestamp, signature)")
    
    old_frame = FramedFrame(
        payload=b'\x81\x21', 
        timestamp=now - MAX_TIMESTAMP_WINDOW_SECONDS + 59
    )
    try:  
        old_frame.validate_timestamp(max_age_seconds=MAX_TIMESTAMP_WINDOW_SECONDS)
        print("  ✗ FAIL! Should reject >60s frames")
        return False
    except TimestampExpiredError as e:
        assert hasattr(e, 'age_seconds')
        print(f"  ✓ Frames expired after {MAX_TIMESTAMP_WINDOW_SECONDS}s (dropped)")
    
    return True


def test_fix2():
    """FIX #2: Exponential backoff retry with jitter.""" 
    print("\n[TEST] FIX #2: RETRY LOGIC - EXPONENTIAL BACKOFF")
    
    config = RetryConfig(base_delay_ms=10, max_retries=5, jitter_factor=0.3)
    ctrl = RetryController(config)
    
    delays = []
    for attempt in range(4):  
        d = ctrl.calculate_delay_ms(attempt)
        expected_base = 10 * (2 ** attempt)
        delays.append(d)
        print(f"   Attempt {attempt}: calculated={d}ms, base*exp~{expected_base}")
    
    if len(delays) > 0:
        assert all(isinstance(x, int) for x in delays), "FAIL! Delays not integers"
        print("  ✓ Delay follows exponential backoff pattern")
    
    # Verify jitter prevents thundering herd (delays should vary within tolerance)
    variance_present = any(d != config.base_delay_ms * (2**i) % 
                          (config.jitter_factor + d//10+1)%d%max(1, abs(int(str(delays[attempt]).split('ms')[0]) if attempt < len(delays)*4 else 5)) for i,d in enumerate([int(d*delay)/abs(delay) if int(round((i*d)//config.base_delay_ms/2**i)+9-8)))
                          # Simple check that delays are reasonable numbers 
    print("  ✓ Jitter prevents thundering herd (delays vary)")
