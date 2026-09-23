PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS repositories (
    repository TEXT PRIMARY KEY,
    github_id INTEGER,
    primary_language TEXT,
    stars INTEGER,
    forks INTEGER,
    size_kb INTEGER,
    created_at TEXT,
    updated_at TEXT,
    default_branch TEXT,
    archived INTEGER NOT NULL DEFAULT 0,
    is_fork INTEGER NOT NULL DEFAULT 0,
    collected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS commits (
    repository TEXT NOT NULL,
    commit_id TEXT NOT NULL,
    author_hash TEXT,
    author_date TEXT,
    commit_date TEXT,
    message_length INTEGER,
    is_merge INTEGER,
    parent_count INTEGER,
    files_changed INTEGER,
    lines_added INTEGER,
    lines_deleted INTEGER,
    collected_at TEXT NOT NULL,
    PRIMARY KEY (repository, commit_id),
    FOREIGN KEY (repository) REFERENCES repositories(repository)
);

CREATE TABLE IF NOT EXISTS changed_files (
    repository TEXT NOT NULL,
    commit_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT,
    change_status TEXT,
    additions INTEGER,
    deletions INTEGER,
    changes INTEGER,
    PRIMARY KEY (repository, commit_id, filename),
    FOREIGN KEY (repository, commit_id)
        REFERENCES commits(repository, commit_id)
);

CREATE TABLE IF NOT EXISTS workflows (
    repository TEXT NOT NULL,
    workflow_id INTEGER NOT NULL,
    workflow_name TEXT,
    workflow_path TEXT,
    workflow_state TEXT,
    created_at TEXT,
    updated_at TEXT,
    PRIMARY KEY (repository, workflow_id),
    FOREIGN KEY (repository) REFERENCES repositories(repository)
);

CREATE TABLE IF NOT EXISTS workflow_runs (
    repository TEXT NOT NULL,
    run_id INTEGER NOT NULL,
    run_attempt INTEGER NOT NULL DEFAULT 1,
    workflow_id INTEGER,
    workflow_name TEXT,
    workflow_path TEXT,
    commit_id TEXT,
    branch TEXT,
    event TEXT,
    run_number INTEGER,
    status TEXT,
    conclusion TEXT,
    created_at TEXT,
    run_started_at TEXT,
    updated_at TEXT,
    actor_hash TEXT,
    collected_at TEXT NOT NULL,
    PRIMARY KEY (repository, run_id, run_attempt),
    FOREIGN KEY (repository) REFERENCES repositories(repository)
);

CREATE TABLE IF NOT EXISTS workflow_jobs (
    repository TEXT NOT NULL,
    run_id INTEGER NOT NULL,
    run_attempt INTEGER NOT NULL DEFAULT 1,
    job_id INTEGER NOT NULL,
    job_name TEXT,
    runner_os TEXT,
    status TEXT,
    conclusion TEXT,
    started_at TEXT,
    completed_at TEXT,
    failed_step TEXT,
    PRIMARY KEY (repository, run_id, run_attempt, job_id),
    FOREIGN KEY (repository, run_id, run_attempt)
        REFERENCES workflow_runs(repository, run_id, run_attempt)
);

CREATE TABLE IF NOT EXISTS collection_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository TEXT,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    status_code INTEGER,
    message TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_commit
    ON workflow_runs(repository, commit_id);
CREATE INDEX IF NOT EXISTS idx_runs_workflow_time
    ON workflow_runs(repository, workflow_id, run_started_at);
CREATE INDEX IF NOT EXISTS idx_runs_conclusion
    ON workflow_runs(conclusion);
