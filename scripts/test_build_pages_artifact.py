"""Deny-by-default tests for public Pages artifact assembly."""
import tempfile
import unittest
from pathlib import Path
from build_pages_artifact import BuildError,assemble

class SiteArtifactTests(unittest.TestCase):
    def setUp(self):
        self.a=tempfile.TemporaryDirectory()
        self.b=tempfile.TemporaryDirectory()
        self.site=Path(self.a.name)
        self.out=Path(self.b.name)/'pages'
        (self.site/'index.html').write_text('<h1>SPURN</h1>')
        (self.site/'CNAME').write_text('spurnmedia.com\n')
    def tearDown(self):
        self.a.cleanup();self.b.cleanup()
    def add(self,path,value='synthetic'):
        f=self.site/path
        f.parent.mkdir(parents=True,exist_ok=True)
        f.write_text(value)
    def test_public_assets_only(self):
        self.add('latest/story.html')
        self.add('assets/image.webp')
        self.add('scripts/example.py')
        self.add('.github/workflows/x.yml')
        self.add('README.md')
        self.add('assets/home-tiles/.gitkeep')
        names=assemble(self.site,self.out)
        self.assertIn('latest/story.html',names)
        self.assertTrue((self.out/'.nojekyll').exists())
        self.assertFalse((self.out/'README.md').exists())
        self.assertFalse((self.out/'scripts').exists())
        self.assertFalse((self.out/'.github').exists())
    def test_env_denied(self):
        self.add('.env.production')
        with self.assertRaises(BuildError):assemble(self.site,self.out)
    def test_private_directory_denied(self):
        self.add('private/approval.json')
        with self.assertRaises(BuildError):assemble(self.site,self.out)
    def test_sqlite_denied(self):
        self.add('latest/newsroom.sqlite')
        with self.assertRaises(BuildError):assemble(self.site,self.out)
    def test_unknown_root_denied(self):
        self.add('release-intent.json')
        with self.assertRaises(BuildError):assemble(self.site,self.out)
    def test_output_must_not_exist(self):
        self.out.mkdir()
        with self.assertRaises(BuildError):assemble(self.site,self.out)
    def test_wrong_domain_denied_and_cleaned(self):
        (self.site/'CNAME').write_text('unapproved.example')
        with self.assertRaises(BuildError):assemble(self.site,self.out)
        self.assertFalse(self.out.exists())
    def test_symlink_denied(self):
        (self.site/'latest').mkdir()
        (self.site/'latest'/'x.html').symlink_to(self.site/'index.html')
        with self.assertRaises(BuildError):assemble(self.site,self.out)
    def test_destination_inside_source_denied(self):
        with self.assertRaises(BuildError):assemble(self.site,self.site/'build')
if __name__=='__main__':
    unittest.main()
