"""Central limits and settings.

Every number here comes from a requirement in the Phase 2 document,
so the code and the requirement can be traced to each other.
"""

import os
import tempfile
from pathlib import Path

# FR-03: repositories larger than this are rejected.
MAX_REPO_SIZE_MB = int(os.getenv("QG_MAX_REPO_SIZE_MB", "200"))

# R2 mitigation: limits on what we read from an untrusted repository.
MAX_FILE_SIZE_BYTES = 1_000_000
MAX_FILES = 50_000

# SR-01 / R2: hard time limits for external processes (seconds).
CLONE_TIMEOUT_S = 120
ANALYSER_TIMEOUT_S = 300
# Hard limit for one whole analysis, queue time excluded (FR-14 / SR-01).
ANALYSIS_TIMEOUT_S = int(os.getenv("QG_ANALYSIS_TIMEOUT_S", "600"))

# SR-05: rate limit and queue cap.
MAX_ANALYSES_PER_HOUR = int(os.getenv("QG_MAX_ANALYSES_PER_HOUR", "5"))
MAX_QUEUED_JOBS = 20
MAX_PARALLEL_ANALYSES = 2

# Directories that never contain the project's own source code.
EXCLUDED_DIRS = frozenset(
    {".git", "node_modules", "venv", ".venv", "env", "dist", "build", "vendor",
     "__pycache__", ".tox", ".mypy_cache", ".pytest_cache", "site-packages"}
)

PYTHON_EXTENSIONS = frozenset({".py"})
JS_EXTENSIONS = frozenset({".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"})

DATA_DIR = Path(os.getenv("QG_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DB_PATH = DATA_DIR / "gatekeeper.sqlite3"
# Clones go to the system temp folder, never inside the source tree: a file watcher
# (uvicorn --reload) would otherwise restart the server in the middle of an analysis.
WORK_DIR = Path(os.getenv("QG_WORK_DIR", Path(tempfile.gettempdir()) / "quality-gatekeeper"))
STATIC_DIR = Path(os.getenv("QG_STATIC_DIR", Path(__file__).resolve().parent.parent / "static"))
