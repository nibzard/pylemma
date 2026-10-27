CREATE TABLE matches (
    match_id TEXT PRIMARY KEY,
    parent_match_id TEXT REFERENCES matches(match_id),
    settings_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','running','completed','failed','interrupted')),
    completed_rounds INTEGER NOT NULL DEFAULT 0 CHECK (completed_rounds BETWEEN 0 AND 10),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error_category TEXT,
    trace_id TEXT,
    public_trace_url TEXT,
    CHECK ((status = 'completed') = (completed_rounds = 10))
);
CREATE TABLE rounds (
    match_id TEXT NOT NULL REFERENCES matches(match_id),
    round_number INTEGER NOT NULL CHECK (round_number BETWEEN 1 AND 10),
    record_json TEXT NOT NULL,
    PRIMARY KEY (match_id, round_number)
);
