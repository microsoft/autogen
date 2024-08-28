import importlib.util
import os
import sys
from types import ModuleType


def load_module(module_path: str) -> ModuleType:
    module_name = os.path.basename(module_path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None:
        raise ValueError(f"Could not load module from path: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
