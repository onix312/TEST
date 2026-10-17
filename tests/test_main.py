import tempfile
import unittest
from pathlib import Path

try:
    from main import validate_project, prepare, codex_args
    IMPORTED = True
except ImportError:
    IMPORTED = False

@unittest.skipUnless(IMPORTED, 'PySide6 must be installed')
class CoreTests(unittest.TestCase):
    def test_project_and_prompt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                validate_project(str(root))
            (root / 'Assets').mkdir()
            (root / 'ProjectSettings').mkdir()
            self.assertEqual(validate_project(str(root)), root)
            prepare(root)
            (root / '.ai-office' / 'gdd' / 'approved.md').write_text('test', encoding='utf-8')
            args = codex_args('codex', root, 'Implement gameplay')
            self.assertEqual(args[1], 'exec')
            self.assertIn('approved.md', args[-1])

if __name__ == '__main__':
    unittest.main()
