CREATE TABLE attempts (
    match_id TEXT NOT NULL REFERENCES matches(match_id),
    round_number INTEGER NOT NULL CHECK (round_number BETWEEN 1 AND 10),
    attempt_number INTEGER NOT NULL CHECK (attempt_number BETWEEN 1 AND 2),
    record_json TEXT NOT NULL,
    PRIMARY KEY (match_id, round_number, attempt_number)
);
