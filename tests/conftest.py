import pytest
from pathlib import Path


@pytest.fixture
def tmp_config_dir(tmp_path):
    """Provide a temporary config directory instead of ~/.clinstagram/"""
    return tmp_path / ".clinstagram"
