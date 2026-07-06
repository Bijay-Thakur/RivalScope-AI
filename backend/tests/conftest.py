"""Point persistence at a throwaway temp DB so the test suite never writes to
the real dev run-history database. Must run before app.db.database is imported."""
import os
import tempfile
from pathlib import Path

_tmp_db = Path(tempfile.gettempdir()) / "rivalscope_test.db"
os.environ["RIVALSCOPE_DB_PATH"] = str(_tmp_db)

# Start each test session from a clean slate.
if _tmp_db.exists():
    try:
        _tmp_db.unlink()
    except OSError:
        pass
