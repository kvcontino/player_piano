import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent / "data" / "phrases.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text()
    with connect(db_path) as conn:
        conn.executescript(schema)


if __name__ == "__main__":
    init_db()
    print(f"Initialized: {DEFAULT_DB_PATH}")
