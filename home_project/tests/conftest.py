import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from main import app


@pytest.fixture
def client():
    return TestClient(app)
