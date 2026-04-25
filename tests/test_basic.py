import tempfile, unittest
import sys
from agent_black_box.cli import record

class Tests(unittest.TestCase):
    def test_records_command(self):
        with tempfile.TemporaryDirectory() as d:
            manifest, outdir = record([sys.executable, '-c', 'print(123)'], d)
            self.assertEqual(manifest['exit_code'], 0)
            self.assertTrue((outdir/'stdout.txt').exists())
