import importlib.util, sys
from pathlib import Path
parent = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('db', parent / 'db' / '__init__.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.modules[__name__] = module
