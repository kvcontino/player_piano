import json
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


def start_session(host: str, db_path: Path = DEFAULT_DB_PATH) -> int:
    with connect(db_path) as conn:
        cur = conn.execute("INSERT INTO sessions (host) VALUES (?)", (host,))
        return cur.lastrowid


def end_session(session_id: int, db_path: Path = DEFAULT_DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE sessions SET ended_at = datetime('now') WHERE id = ?",
            (session_id,),
        )


def insert_phrase(
    session_id: int,
    notes: list[dict],
    params: dict,
    mood: dict,
    text_repr: str,
    profile_id: int | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    with connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO phrases (session_id, profile_id, notes_json, params_json, mood_snapshot, text_repr)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                profile_id,
                json.dumps(notes),
                json.dumps(params),
                json.dumps(mood),
                text_repr,
            ),
        )
        return cur.lastrowid


def latest_phrase(db_path: Path = DEFAULT_DB_PATH) -> dict | None:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, session_id, profile_id, created_at, notes_json, params_json,
                   mood_snapshot, rating, rated_at, text_repr
            FROM phrases ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["notes"] = json.loads(d.pop("notes_json"))
        d["params"] = json.loads(d.pop("params_json"))
        d["mood"] = json.loads(d.pop("mood_snapshot"))
        tags = conn.execute(
            "SELECT tag FROM phrase_tags WHERE phrase_id = ? ORDER BY tag",
            (d["id"],),
        ).fetchall()
        d["tags"] = [t["tag"] for t in tags]
        return d


def rate_latest_phrase(rating: int, db_path: Path = DEFAULT_DB_PATH) -> int | None:
    if not (1 <= rating <= 5):
        raise ValueError("rating must be 1-5")
    with connect(db_path) as conn:
        row = conn.execute("SELECT id FROM phrases ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE phrases SET rating = ?, rated_at = datetime('now') WHERE id = ?",
            (rating, row["id"]),
        )
        return row["id"]


def tag_latest_phrase(tag: str, remove: bool = False, db_path: Path = DEFAULT_DB_PATH) -> int | None:
    with connect(db_path) as conn:
        row = conn.execute("SELECT id FROM phrases ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            return None
        phrase_id = row["id"]
        if remove:
            conn.execute("DELETE FROM phrase_tags WHERE phrase_id = ? AND tag = ?", (phrase_id, tag))
        else:
            conn.execute(
                "INSERT OR IGNORE INTO phrase_tags (phrase_id, tag) VALUES (?, ?)",
                (phrase_id, tag),
            )
        return phrase_id


def insert_profile(
    name: str,
    description: str,
    traits: dict,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    with connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO musician_profiles (name, description, traits_json) VALUES (?, ?, ?)",
            (name, description, json.dumps(traits)),
        )
        return cur.lastrowid


def upsert_profile(
    name: str,
    description: str,
    traits: dict,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM musician_profiles WHERE name = ?", (name,)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE musician_profiles SET description = ?, traits_json = ? WHERE name = ?",
                (description, json.dumps(traits), name),
            )
            return row["id"]
        cur = conn.execute(
            "INSERT INTO musician_profiles (name, description, traits_json) VALUES (?, ?, ?)",
            (name, description, json.dumps(traits)),
        )
        return cur.lastrowid


def get_profile(name: str, db_path: Path = DEFAULT_DB_PATH) -> dict | None:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT id, name, description, traits_json FROM musician_profiles WHERE name = ?",
            (name,),
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["traits"] = json.loads(d.pop("traits_json"))
        return d


if __name__ == "__main__":
    init_db()
    print(f"Initialized: {DEFAULT_DB_PATH}")
