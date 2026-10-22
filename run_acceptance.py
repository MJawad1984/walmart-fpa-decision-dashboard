"""Run the project's acceptance checks using Python's standard unittest engine."""
import importlib.util
import inspect
from pathlib import Path
import unittest

root = Path(__file__).resolve().parent
suite = unittest.TestSuite()
for path in sorted((root / 'tests').glob('test_*.py')):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    for name, value in inspect.getmembers(module, inspect.isfunction):
        if name.startswith('test_'):
            suite.addTest(unittest.FunctionTestCase(value, description=name))
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
