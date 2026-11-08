import shutil
import pytest
from pathlib import Path
from saarthi.config import settings


@pytest.fixture(autouse=True)
def isolate_test_data_directory(tmp_path, monkeypatch):
    """Isolate test artifacts and cache to a temporary directory so tests never pollute data/."""
    test_data = tmp_path / "data"
    test_artifacts = test_data / "artifacts"
    test_cache = test_data / "cache"
    test_artifacts.mkdir(parents=True, exist_ok=True)
    test_cache.mkdir(parents=True, exist_ok=True)

    # Copy brands.json so brand lookups work in tests
    canonical_brands = settings.base_dir / "data" / "brands.json"
    if canonical_brands.exists():
        shutil.copy2(canonical_brands, test_data / "brands.json")

    monkeypatch.setattr(settings, "data_dir", test_data)
