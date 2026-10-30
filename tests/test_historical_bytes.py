"""Fixed-pin portability must not authorize modified historical content."""

import hashlib
import unittest

from labrepair.historical_bytes import pinned_historical_bytes


class HistoricalBytesTests(unittest.TestCase):
    def setUp(self):
        self.original = b'{"status":"BLOCKED"}\r\n'
        self.pin = hashlib.sha256(self.original).hexdigest()

    def test_original_is_preserved(self):
        self.assertEqual(pinned_historical_bytes(self.original, self.pin), self.original)

    def test_git_lf_restores_exact_historical_bytes(self):
        self.assertEqual(pinned_historical_bytes(self.original.replace(b"\r\n", b"\n"), self.pin), self.original)

    def test_content_or_whitespace_edits_are_rejected(self):
        for raw in (b'{"status":"ALLOW"}\n', b'{"status": "BLOCKED"}\n', b'{"status":"BLOCKED"}'):
            with self.assertRaises(ValueError):
                pinned_historical_bytes(raw, self.pin)

    def test_mixed_newlines_are_not_repaired(self):
        with self.assertRaises(ValueError):
            pinned_historical_bytes(b'{"status":"BLOCKED"}\r\n\n', self.pin)
