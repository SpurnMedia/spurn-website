#!/usr/bin/env python3
"""Fail closed: only externally signed production approvals may authorize Pages."""
from __future__ import annotations
import base64
import binascii
import datetime as dt
import hashlib
import json
import os
import re
import sys

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT = re.compile(r"^[a-f0-9]{40}$")
ISSUE = re.compile(r"^spurn-[0-9]{4}-[0-9]{2}-[0-9]{2}(?:-[a-z0-9-]{1,30})?$")
NONCE = re.compile(r"^[a-f0-9]{32,64}$")
SCHEMA = "spurn.production.release-intent.v1"
REPOSITORY = "SpurnMedia/spurn-website"
KEYS = frozenset({"schema", "repository", "commit_sha", "release_type", "issue_id",
    "frozen_manifest_sha256", "human_approval_sha256", "approval_schema",
    "production_authority", "issued_at", "expires_at", "nonce"})
UTC = dt.timezone.utc

class ReleaseIntentError(ValueError):
    pass

def decode_urlsafe(text: str, limit: int) -> bytes:
    if not isinstance(text, str) or len(text)>limit or not text or not re.fullmatch(r"[A-Za-z0-9_\-]+=*",text):
        raise ReleaseIntentError("invalid base64 field")
    try:
        raw=base64.urlsafe_b64decode(text+"="*(-len(text)%4))
    except (binascii.Error,ValueError) as exc:
        raise ReleaseIntentError("invalid base64 field") from exc
    if not raw:
        raise ReleaseIntentError("empty base64 field")
    return raw

def canonical_bytes(doc: dict) -> bytes:
    return json.dumps(doc,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")

def parse_time(value: str) -> dt.datetime:
    if not isinstance(value,str) or len(value)>40:
        raise ReleaseIntentError("invalid timestamp")
    try:
        parsed=dt.datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise ReleaseIntentError("invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset()!=dt.timedelta(0):
        raise ReleaseIntentError("timestamp must be UTC and timezone-aware")
    return parsed.astimezone(UTC)

def verify_document(intent: dict, expected_commit: str, now: dt.datetime) -> None:
    if not isinstance(intent,dict) or set(intent)!=KEYS:
        raise ReleaseIntentError("unexpected intent fields")
    if intent["schema"]!=SCHEMA or intent["repository"]!=REPOSITORY:
        raise ReleaseIntentError("untrusted release schema or repository")
    if not isinstance(expected_commit,str) or not COMMIT.fullmatch(expected_commit):
        raise ReleaseIntentError("invalid target commit")
    if intent["commit_sha"]!=expected_commit:
        raise ReleaseIntentError("release not pinned to checked-out commit")
    if intent["production_authority"] is not True:
        raise ReleaseIntentError("shadow approval cannot authorize publication")
    if intent["approval_schema"]!="spurn.private.production-approval.v1":
        raise ReleaseIntentError("not a production approval")
    if intent["release_type"]!="editorial":
        raise ReleaseIntentError("only editorial releases accepted by this workflow")
    if not isinstance(intent["issue_id"],str) or not ISSUE.fullmatch(intent["issue_id"]):
        raise ReleaseIntentError("invalid issue identifier")
    if any(not isinstance(intent[k],str) or not SHA256.fullmatch(intent[k])
           for k in ("frozen_manifest_sha256","human_approval_sha256")):
        raise ReleaseIntentError("invalid manifest/approval digest")
    if not isinstance(intent["nonce"],str) or not NONCE.fullmatch(intent["nonce"]):
        raise ReleaseIntentError("invalid nonce")
    issued,expires=parse_time(intent["issued_at"]),parse_time(intent["expires_at"])
    if now.tzinfo is None:
        raise ReleaseIntentError("clock must be timezone-aware")
    now=now.astimezone(UTC)
    if not issued<=now<=expires:
        raise ReleaseIntentError("release intent is not currently valid")
    if expires-issued>dt.timedelta(minutes=15) or expires<=issued:
        raise ReleaseIntentError("release intent window exceeds 15 minutes")
    if issued-now>dt.timedelta(seconds=30):
        raise ReleaseIntentError("release intent issued in the future")

def verify(intent_b64: str, signature_b64: str, public_key_b64: str,
           expected_commit: str, now: dt.datetime|None=None) -> str:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    payload=decode_urlsafe(intent_b64,16000)
    if len(payload)>8192:
        raise ReleaseIntentError("release intent too large")
    signature=decode_urlsafe(signature_b64,250)
    key=decode_urlsafe(public_key_b64,250)
    if len(signature)!=64 or len(key)!=32:
        raise ReleaseIntentError("invalid signature or public key length")
    try:
        intent=json.loads(payload)
    except (UnicodeError,ValueError) as exc:
        raise ReleaseIntentError("invalid intent JSON") from exc
    if not isinstance(intent,dict) or payload!=canonical_bytes(intent):
        raise ReleaseIntentError("intent must use canonical JSON bytes")
    verify_document(intent,expected_commit,now or dt.datetime.now(UTC))
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(signature,payload)
    except (InvalidSignature,ValueError) as exc:
        raise ReleaseIntentError("invalid release signature") from exc
    return hashlib.sha256(payload).hexdigest()

def main() -> int:
    if os.environ.get("SPURN_PAGES_RELEASE_ENABLED","")!="true":
        print("NO-GO: production release control is not enabled",file=sys.stderr)
        return 2
    try:
        signature_hash=verify(
            os.environ.get("SPURN_RELEASE_INTENT_B64",""),
            os.environ.get("SPURN_RELEASE_SIGNATURE_B64",""),
            os.environ.get("SPURN_RELEASE_PUBLIC_KEY_B64",""),
            os.environ.get("SPURN_EXPECTED_COMMIT",""))
    except (ReleaseIntentError,ValueError) as exc:
        print("NO-GO: "+str(exc),file=sys.stderr)
        return 2
    print("GO: short-lived signed production attestation; sha256="+signature_hash)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
