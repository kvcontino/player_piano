-- Foreign keys must be enabled per-connection — SQLite quirk
PRAGMA foreign_keys = ON;

-- sessions: one row per generator run (start to stop)
CREATE TABLE sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),  -- ISO 8601 UTC
    ended_at    TEXT,                                     -- NULL while active
    host        TEXT NOT NULL                             -- 'kevadk' | 'laptop'
);

-- musician_profiles: trait JSON for biased generation
CREATE TABLE musician_profiles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    description  TEXT,
    traits_json  TEXT NOT NULL CHECK (json_valid(traits_json)),
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- phrases: the atomic unit (8-12 notes)
CREATE TABLE phrases (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id     INTEGER NOT NULL REFERENCES sessions(id),
    profile_id     INTEGER REFERENCES musician_profiles(id),  -- nullable
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    notes_json     TEXT NOT NULL CHECK (json_valid(notes_json)),
        -- [{pitch, velocity, time_ms, duration_ms}, ...]
    params_json    TEXT NOT NULL CHECK (json_valid(params_json)),
        -- generator settings at emit time (scale, root, tempo, etc.)
    mood_snapshot  TEXT NOT NULL CHECK (json_valid(mood_snapshot)),
        -- copy of current_mood.json at emit time
    rating         INTEGER CHECK (rating BETWEEN 1 AND 5),
    rated_at       TEXT,                                  -- when rating was last set
    text_repr      TEXT NOT NULL
        -- concatenated forms for FTS5: note names + intervals + Parsons + description
);

CREATE INDEX idx_phrases_session ON phrases(session_id);
CREATE INDEX idx_phrases_profile ON phrases(profile_id);
CREATE INDEX idx_phrases_created ON phrases(created_at);
CREATE INDEX idx_phrases_rating  ON phrases(rating) WHERE rating IS NOT NULL;
    -- partial index: skip unrated rows (most phrases initially)

-- phrase_tags: many-to-many; one phrase can be 'meditative' AND 'minor'
CREATE TABLE phrase_tags (
    phrase_id  INTEGER NOT NULL REFERENCES phrases(id) ON DELETE CASCADE,
    tag        TEXT NOT NULL,
    PRIMARY KEY (phrase_id, tag)
);

CREATE INDEX idx_phrase_tags_tag ON phrase_tags(tag);

-- FTS5 virtual table over text_repr; 'content=phrases' avoids duplicating storage
CREATE VIRTUAL TABLE phrases_fts USING fts5(
    text_repr,
    content=phrases,
    content_rowid=id
);

-- Triggers keep FTS index in sync. The 'delete' / 'rowid' INSERT pattern is
-- the SQLite-prescribed way to signal an FTS deletion from a contentless table.
CREATE TRIGGER phrases_ai AFTER INSERT ON phrases BEGIN
    INSERT INTO phrases_fts(rowid, text_repr) VALUES (new.id, new.text_repr);
END;

CREATE TRIGGER phrases_ad AFTER DELETE ON phrases BEGIN
    INSERT INTO phrases_fts(phrases_fts, rowid, text_repr)
        VALUES ('delete', old.id, old.text_repr);
END;

CREATE TRIGGER phrases_au AFTER UPDATE ON phrases BEGIN
    INSERT INTO phrases_fts(phrases_fts, rowid, text_repr)
        VALUES ('delete', old.id, old.text_repr);
    INSERT INTO phrases_fts(rowid, text_repr) VALUES (new.id, new.text_repr);
END;
