#!/usr/bin/env python3
"""Detect private newsroom artifacts in the public SPURN Pages tree.

Defense-in-depth only. This is NOT authenticated approval verification.
"""
from pathlib import Path
import sys

SENSITIVE_SUFFIXES = {'.db', '.sqlite', '.sqlite3', '.pem', '.key', '.p12', '.pfx', '.zip', '.whl'}
SENSITIVE_FILES = {'approval.json', 'approval-record.json', 'daily-decisions.json',
                   'source-ledger.json', 'source_ledger.json', 'newsroom.db'}
SENSITIVE_DIRS = {'private', '.private', 'previews', '.secrets', 'secrets'}
PRIVATE_HTML_MARKERS = ('PRIVATE PREVIEW — NOT APPROVED', 'PRIVATE PREVIEW',
                        'SPURN Daily Issue Review', 'PRIVATE · READ ONLY · SHADOW')

def check(root: Path) -> list[str]:
    root = root.resolve()
    flagged = []
    for path in root.rglob('*'):
        if not path.is_file() and not path.is_symlink():
            continue
        rel = path.relative_to(root)
        parts = [p.lower() for p in rel.parts]
        if '.git' in parts:
            continue
        fname = path.name.lower()
        reason = None
        if any(d in SENSITIVE_DIRS for d in parts[:-1]):
            reason = 'private directory'
        elif fname in SENSITIVE_FILES or fname.startswith('.env'):
            reason = 'private file name'
        elif path.suffix.lower() in SENSITIVE_SUFFIXES:
            reason = 'private/binary archive extension'
        elif path.is_symlink():
            reason = 'symlink is not allowed in public site'
        elif path.suffix.lower() in ('.html', '.htm'):
            content = path.read_text(encoding='utf-8', errors='ignore')
            if any(marker in content for marker in PRIVATE_HTML_MARKERS):
                reason = 'private preview marker'
        if reason:
            flagged.append(f'{rel.as_posix()}: {reason}')
    return sorted(flagged)

if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    issues = check(root)
    if issues:
        print('FAIL: private materials in public site checkout')
        for issue in issues:
            print(' -', issue)
        raise SystemExit(1)
    print('PASS: no flagged private newsroom artifacts')
