from pathlib import Path

import pytest

from patrol.vault import load_vault

DEMO = Path(__file__).resolve().parent.parent / "demo-vault"


@pytest.fixture
def demo_vault():
    return load_vault(DEMO)
