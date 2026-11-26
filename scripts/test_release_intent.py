"""Synthetic checks for production-only Ed25519 release verifier."""
import base64
import datetime as dt
import os
import unittest
from unittest import mock
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from verify_release_intent import ReleaseIntentError, canonical_bytes, verify, main

UTC=dt.timezone.utc
NOW=dt.datetime(2026,11,26,12,0,tzinfo=UTC)
COMMIT='a'*40

def b64(raw):
    return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')

class ReleaseIntentTests(unittest.TestCase):
    def setUp(self):
        self.key=Ed25519PrivateKey.generate()
        self.public=b64(self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,format=serialization.PublicFormat.Raw))
        self.doc={
            'schema':'spurn.production.release-intent.v1','repository':'SpurnMedia/spurn-website',
            'commit_sha':COMMIT,'release_type':'editorial','issue_id':'spurn-2026-11-26',
            'frozen_manifest_sha256':'sha256:'+'1'*64,
            'human_approval_sha256':'sha256:'+'2'*64,
            'approval_schema':'spurn.private.production-approval.v1',
            'production_authority':True,
            'issued_at':'2026-11-26T11:59:00+00:00',
            'expires_at':'2026-11-26T12:04:00+00:00',
            'nonce':'0'*32}

    def check(self,doc=None,commit=COMMIT,now=NOW,key=None):
        payload=canonical_bytes(doc or self.doc)
        return verify(b64(payload),b64(self.key.sign(payload)),key or self.public,commit,now)

    def test_valid_synthetic_production_signature(self):
        self.assertEqual(len(self.check()),64)
    def test_modified_commit_refused(self):
        with self.assertRaises(ReleaseIntentError): self.check(commit='b'*40)
    def test_expired_intent_refused(self):
        with self.assertRaises(ReleaseIntentError): self.check(now=NOW+dt.timedelta(days=1))
    def test_invalid_signature_refused(self):
        payload=canonical_bytes(self.doc)
        other=Ed25519PrivateKey.generate()
        with self.assertRaises(ReleaseIntentError):
            verify(b64(payload),b64(other.sign(payload)),self.public,COMMIT,NOW)
    def test_shadow_decision_refused(self):
        with self.assertRaises(ReleaseIntentError):
            self.check(dict(self.doc,approval_schema='spurn.private.oidc-shadow-decision.v1.0'))
    def test_fake_production_boolean_refused(self):
        with self.assertRaises(ReleaseIntentError):
            self.check(dict(self.doc,production_authority=1))
    def test_modified_approval_hash_refused(self):
        payload=canonical_bytes(self.doc)
        changed=canonical_bytes(dict(self.doc,human_approval_sha256='sha256:'+'3'*64))
        with self.assertRaises(ReleaseIntentError):
            verify(b64(changed),b64(self.key.sign(payload)),self.public,COMMIT,NOW)
    def test_unsigned_or_wrong_key_refused(self):
        with self.assertRaises(ReleaseIntentError): self.check(key=b64(b'x'*32))
    def test_wrong_repo_refused(self):
        with self.assertRaises(ReleaseIntentError): self.check(dict(self.doc,repository='attacker/site'))
    def test_overlong_validity_refused(self):
        with self.assertRaises(ReleaseIntentError):
            self.check(dict(self.doc,expires_at='2026-11-26T12:44:00+00:00'))
    def test_extra_metadata_refused(self):
        with self.assertRaises(ReleaseIntentError): self.check(dict(self.doc,simulated=True))
    def test_timezone_missing_refused(self):
        with self.assertRaises(ReleaseIntentError):
            self.check(dict(self.doc,issued_at='2026-11-26T11:59:00'))
    def test_disabled_without_secret(self):
        with mock.patch.dict(os.environ,{},clear=True):
            self.assertEqual(main(),2)

if __name__=='__main__':
    unittest.main()
