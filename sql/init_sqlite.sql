PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    real_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'staff', 'viewer')),
    password_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sample_types (
    type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS storage_locations (
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS projects (
    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT NOT NULL UNIQUE,
    principal_investigator TEXT,
    start_date TEXT,
    end_date TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS samples (
    sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_code TEXT NOT NULL UNIQUE,
    sample_name TEXT NOT NULL,
    type_id INTEGER NOT NULL,
    project_id INTEGER,
    location_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'borrowed', 'disposed')),
    collected_date TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (type_id) REFERENCES sample_types(type_id),
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (location_id) REFERENCES storage_locations(location_id)
);

CREATE TABLE IF NOT EXISTS borrow_records (
    borrow_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    borrow_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expected_return_time TEXT,
    actual_return_time TEXT,
    status TEXT NOT NULL DEFAULT 'borrowed' CHECK (status IN ('borrowed', 'returned', 'overdue')),
    purpose TEXT,
    note TEXT,
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS sample_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_id INTEGER NOT NULL,
    user_id INTEGER,
    action_type TEXT NOT NULL CHECK (action_type IN ('CREATE', 'BORROW', 'RETURN', 'MOVE', 'DISPOSE')),
    from_location_id INTEGER,
    to_location_id INTEGER,
    action_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    remark TEXT,
    FOREIGN KEY (sample_id) REFERENCES samples(sample_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (from_location_id) REFERENCES storage_locations(location_id),
    FOREIGN KEY (to_location_id) REFERENCES storage_locations(location_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    actor_user_id INTEGER,
    actor_username TEXT,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('success', 'failure', 'denied', 'error')),
    detail TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_samples_status ON samples(status);
CREATE INDEX IF NOT EXISTS idx_samples_type ON samples(type_id);
CREATE INDEX IF NOT EXISTS idx_borrow_status ON borrow_records(status);
CREATE INDEX IF NOT EXISTS idx_transactions_action_time ON sample_transactions(action_time);
CREATE INDEX IF NOT EXISTS idx_audit_event_created ON audit_logs(event_type, created_at);

CREATE VIEW IF NOT EXISTS v_sample_detail AS
SELECT
    s.sample_id,
    s.sample_code,
    s.sample_name,
    st.type_name,
    p.project_name,
    sl.location_name,
    s.status,
    s.collected_date,
    s.created_at
FROM samples s
JOIN sample_types st ON s.type_id = st.type_id
LEFT JOIN projects p ON s.project_id = p.project_id
JOIN storage_locations sl ON s.location_id = sl.location_id;

CREATE VIEW IF NOT EXISTS v_current_borrowed_samples AS
SELECT
    br.borrow_id,
    s.sample_id,
    s.sample_code,
    s.sample_name,
    u.real_name AS borrower_name,
    br.borrow_time,
    br.expected_return_time,
    br.status,
    br.purpose,
    br.note
FROM borrow_records br
JOIN samples s ON br.sample_id = s.sample_id
JOIN users u ON br.user_id = u.user_id
WHERE br.status IN ('borrowed', 'overdue');

CREATE VIEW IF NOT EXISTS v_project_sample_statistics AS
SELECT
    p.project_id,
    p.project_name,
    COUNT(s.sample_id) AS sample_count
FROM projects p
LEFT JOIN samples s ON p.project_id = s.project_id
GROUP BY p.project_id, p.project_name;
