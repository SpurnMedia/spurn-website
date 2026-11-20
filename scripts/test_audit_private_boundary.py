"""Standard-library tests for SPURN's public-site private material guard."""
import tempfile
import unittest
from pathlib import Path
from audit_private_boundary import check

class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='spurn-public-check-')
        self.root = Path(self.tmp.name)
        (self.root / 'index.html').write_text('<h1>Public page</h1>')
        (self.root / 'CNAME').write_text('spurnmedia.com')

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, relative, data='synthetic'):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)

    def test_normal_public_pages_allowed(self):
        self.add('trust/privacy.html', '<title>Privacy</title>')
        self.add('assets/optimized/photo.webp')
        self.assertEqual(check(self.root), [])

    def test_private_sqlite_rejected(self):
        self.add('newsroom.sqlite')
        self.assertTrue(check(self.root))

    def test_env_rejected(self):
        self.add('.env.production')
        self.assertTrue(check(self.root))

    def test_approval_json_rejected(self):
        self.add('approval-record.json', '{}')
        self.assertTrue(check(self.root))

    def test_private_directory_rejected(self):
        self.add('private/issue.json', '{}')
        self.assertTrue(check(self.root))

    def test_review_preview_rejected(self):
        self.add('demo.html', 'SPURN Daily Issue Review')
        self.assertTrue(check(self.root))

    def test_archive_rejected(self):
        self.add('newsroom-export.zip')
        self.assertTrue(check(self.root))

    def test_trust_policy_allowed(self):
        self.add('trust/ai-editorial-use.html', 'A public editorial disclosure.')
        self.assertEqual(check(self.root), [])

if __name__ == '__main__':
    unittest.main()
