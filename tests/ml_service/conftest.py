import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from services.ml.main import create_app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(create_app())
