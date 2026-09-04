import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ecu.dtc import Fault, NO_FAULT, FRAME_START, decode_faults, decode_dtc_codes, describe
from ecu.ecu_db import ECUDatabase


class TestDecodeFaults(unittest.TestCase):
    def test_empty_returns_no_faults(self):
        self.assertEqual(decode_faults(b""), [])

    def test_no_fault_sentinel_skipped(self):
        # 0x55 = no fault, paired with a starts count.
        self.assertEqual(decode_faults(bytes([NO_FAULT, 0x00])), [])

    def test_single_fault_pair(self):
        faults = decode_faults(bytes([0x13, 0x00]))
        self.assertEqual(len(faults), 1)
        self.assertEqual(faults[0].code, 0x13)
        self.assertEqual(faults[0].starts, 0)
        self.assertEqual(faults[0].display_code, "13")

    def test_two_fault_pairs(self):
        # Example from the Consult spec: (0x2e)(0xff)(0x04)(0x13)(0x00)(0x08)(0x03)
        faults = decode_faults(bytes([FRAME_START, 0x04, 0x13, 0x00, 0x08, 0x03]))
        self.assertEqual([f.code for f in faults], [0x13, 0x08])
        self.assertEqual([f.starts for f in faults], [0, 3])

    def test_counts_engine_starts(self):
        faults = decode_faults(bytes([0x08, 0x03]))
        self.assertEqual(faults[0].starts, 3)

    def test_odd_trailing_byte_ignored(self):
        faults = decode_faults(bytes([0x13, 0x00, 0x08]))
        self.assertEqual([f.code for f in faults], [0x13])

    def test_mixed_with_no_fault_padding(self):
        # Fault then a no-fault padding pair.
        faults = decode_faults(bytes([0x13, 0x00, NO_FAULT, 0x00]))
        self.assertEqual([f.code for f in faults], [0x13])


class TestDecodeCodes(unittest.TestCase):
    def test_returns_display_strings(self):
        codes = decode_dtc_codes(bytes([0x13, 0x00, 0x08, 0x03]))
        self.assertEqual(codes, ["13", "08"])

    def test_no_fault_gives_empty_list(self):
        self.assertEqual(decode_dtc_codes(bytes([NO_FAULT, 0x00])), [])

    def test_none_safe(self):
        self.assertEqual(decode_dtc_codes(None), [])


class TestDescribe(unittest.TestCase):
    def test_known_code_description(self):
        self.assertIn("misfire", describe(0x13).lower())

    def test_unknown_code_fallback(self):
        self.assertIn("not in local", describe(0xC0))

    def test_no_fault_described(self):
        self.assertIn("not in local", describe(NO_FAULT))


class TestDBTranslationFallback(unittest.TestCase):
    def setUp(self):
        self.db = ECUDatabase()

    def test_named_code_still_resolves(self):
        self.assertIsNotNone(self.db.get_dtc_definition("P0420"))
        self.assertIsNotNone(self.db.get_dtc_definition("P0171"))

    def test_numeric_code_translates_from_index(self):
        definition = self.db.get_dtc_definition("13")
        self.assertIsNotNone(definition)
        self.assertIn("misfire", definition.description.lower())

    def test_unknown_numeric_code_returns_none(self):
        self.assertIsNone(self.db.get_dtc_definition("CC"))

    def test_fault_object_display(self):
        f = Fault(code=0x08, starts=3)
        self.assertEqual(f.display_code, "08")
        self.assertFalse(f.is_no_fault)
        self.assertTrue(Fault(code=NO_FAULT).is_no_fault)


if __name__ == "__main__":
    unittest.main()
