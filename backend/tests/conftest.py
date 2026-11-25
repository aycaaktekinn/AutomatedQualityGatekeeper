import os
import shutil
import tempfile
from pathlib import Path

import pytest

# Keep test databases and clones out of the real data directory.
_TEST_DATA = Path(tempfile.mkdtemp(prefix="qg-test-"))
os.environ["QG_DATA_DIR"] = str(_TEST_DATA)
os.environ["QG_STATIC_DIR"] = str(_TEST_DATA / "no-static")

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """A small repository with known problems (the 'planted issues' reference repo)."""
    root = tmp_path / "sample"
    shutil.copytree(FIXTURES / "sample_repo", root)
    return root


@pytest.fixture
def copy_fetcher():
    """Replaces the GitHub fetcher: copies a local fixture instead of cloning."""

    def make(source: Path):
        def fetch(_ref, destination: Path, _checkpoint=None) -> str:
            shutil.copytree(source, destination)
            return "0123456789abcdef"

        return fetch

    return make
