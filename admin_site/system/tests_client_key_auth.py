"""Tests for client-key authentication behavior on machine-scoped RPC calls.

Verified policy:
- Incoming client_key is normalized and hashed.
- If a PC has no stored key and a non-empty key is provided, store hash and allow.
- If a PC has no stored key and key is missing, allow (legacy compatibility).
- If a PC has a stored key and incoming key is missing, reject.
- If a PC has a stored key and incoming key does not match, reject.
- Malformed keys are rejected early.
- Existing endpoint activation checks still apply (inactive PCs do not receive instructions).
"""

import hashlib

from django.test import TestCase

from system.models import Configuration, PC, Site
from system.rpc import get_instructions


class ClientKeyAuthTests(TestCase):
    def setUp(self):
        self.site_config = Configuration.objects.create(name="site-config")
        self.site = Site.objects.create(
            name="Test Site",
            uid="test-site",
            configuration=self.site_config,
        )

    def _create_pc(self, uid, is_activated=True, client_key_hash=None):
        pc_config = Configuration.objects.create(name=f"pc-config-{uid}")
        return PC.objects.create(
            name=f"PC-{uid}",
            uid=uid,
            mac="00:11:22:33:44:55",
            site=self.site,
            configuration=pc_config,
            is_activated=is_activated,
            client_key_hash=client_key_hash,
        )

    def test_stores_hash_when_missing_and_key_present(self):
        pc = self._create_pc(uid="pc-store-hash", client_key_hash=None)

        result = get_instructions(pc.uid, "A" * 64)

        pc.refresh_from_db()
        expected_hash = hashlib.sha256(("a" * 64).encode("ascii")).hexdigest()

        self.assertEqual(pc.client_key_hash, expected_hash)
        self.assertEqual(result["configuration"]["uid"], pc.uid)

    def test_allows_when_hash_missing_and_key_missing(self):
        pc = self._create_pc(uid="pc-legacy", client_key_hash=None)

        result = get_instructions(pc.uid)

        pc.refresh_from_db()
        self.assertIsNone(pc.client_key_hash)
        self.assertEqual(result["configuration"]["uid"], pc.uid)

    def test_rejects_when_hash_exists_and_key_missing(self):
        stored_hash = hashlib.sha256(("a" * 64).encode("ascii")).hexdigest()
        pc = self._create_pc(uid="pc-missing-key", client_key_hash=stored_hash)

        with self.assertRaisesRegex(Exception, "missing client_key"):
            get_instructions(pc.uid)

    def test_rejects_when_hash_exists_and_key_mismatch(self):
        stored_hash = hashlib.sha256(("a" * 64).encode("ascii")).hexdigest()
        pc = self._create_pc(uid="pc-mismatch", client_key_hash=stored_hash)

        with self.assertRaisesRegex(Exception, "mismatched client_key"):
            get_instructions(pc.uid, "b" * 64)

    def test_allows_when_hash_exists_and_key_matches(self):
        stored_hash = hashlib.sha256(("a" * 64).encode("ascii")).hexdigest()
        pc = self._create_pc(uid="pc-match", client_key_hash=stored_hash)

        result = get_instructions(pc.uid, "A" * 64)

        self.assertEqual(result["configuration"]["uid"], pc.uid)

    def test_rejects_malformed_client_key_values(self):
        pc = self._create_pc(uid="pc-malformed", client_key_hash=None)

        malformed_values = [
            "short",
            "z" * 64,
            1234,
        ]

        for value in malformed_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(Exception, "malformed client_key"):
                    get_instructions(pc.uid, value)

    def test_inactive_pc_is_rejected_by_existing_endpoint_behavior(self):
        pc = self._create_pc(uid="pc-inactive", is_activated=False)

        result = get_instructions(pc.uid, "a" * 64)

        self.assertEqual(result, {})
