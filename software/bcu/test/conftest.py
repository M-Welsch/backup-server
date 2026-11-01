import importlib.util
import sys
from pathlib import Path

import pytest

BCU = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BCU))


@pytest.fixture
def bcu():
    spec = importlib.util.spec_from_file_location("bcu_main", BCU / "__main__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
