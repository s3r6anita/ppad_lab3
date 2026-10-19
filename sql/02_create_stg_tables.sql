BEGIN;

CREATE TABLE IF NOT EXISTS stg.load_batches (
    batch_id UUID PRIMARY KEY,
    dag_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMPTZ,
    expected_repository_count INTEGER NOT NULL,
    error_message TEXT,

    CONSTRAINT load_batches_dag_run_uq
        UNIQUE (dag_id, run_id),

    CONSTRAINT load_batches_status_check
        CHECK (status IN ('running', 'success', 'failed')),

    CONSTRAINT load_batches_repository_count_check
        CHECK (expected_repository_count > 0),

    CONSTRAINT load_batches_finished_at_check
        CHECK (
            (status = 'running' AND finished_at IS NULL)
            OR
            (status IN ('success', 'failed') AND finished_at IS NOT NULL)
        ),

    CONSTRAINT load_batches_time_order_check
        CHECK (finished_at IS NULL OR finished_at >= started_at)
);

CREATE TABLE IF NOT EXISTS stg.repository_loads (
    batch_id UUID NOT NULL,
    repository_full_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMPTZ,
    repository_record_count INTEGER NOT NULL DEFAULT 0,
    issue_record_count INTEGER NOT NULL DEFAULT 0,
    issue_page_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,

    PRIMARY KEY (batch_id, repository_full_name),

    CONSTRAINT repository_loads_batch_fk
        FOREIGN KEY (batch_id)
        REFERENCES stg.load_batches (batch_id),

    CONSTRAINT repository_loads_status_check
        CHECK (status IN ('running', 'success', 'failed')),

    CONSTRAINT repository_loads_counts_check
        CHECK (
            repository_record_count >= 0
            AND issue_record_count >= 0
            AND issue_page_count >= 0
        ),

    CONSTRAINT repository_loads_finished_at_check
        CHECK (
            (status = 'running' AND finished_at IS NULL)
            OR
            (status IN ('success', 'failed') AND finished_at IS NOT NULL)
        ),

    CONSTRAINT repository_loads_time_order_check
        CHECK (finished_at IS NULL OR finished_at >= started_at),

    CONSTRAINT repository_loads_success_check
        CHECK (
            status <> 'success'
            OR (
                repository_record_count = 1
                AND issue_page_count >= 1
            )
        )
);

CREATE TABLE IF NOT EXISTS stg.github_repositories_raw (
    batch_id UUID NOT NULL,
    repository_full_name TEXT NOT NULL,
    payload JSONB NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_url TEXT NOT NULL,
    http_status INTEGER NOT NULL,

    PRIMARY KEY (batch_id, repository_full_name),

    CONSTRAINT github_repositories_raw_load_fk
        FOREIGN KEY (batch_id, repository_full_name)
        REFERENCES stg.repository_loads (batch_id, repository_full_name),

    CONSTRAINT github_repositories_raw_http_status_check
        CHECK (http_status = 200)
);

CREATE TABLE IF NOT EXISTS stg.github_issues_raw (
    batch_id UUID NOT NULL,
    repository_full_name TEXT NOT NULL,
    github_issue_id BIGINT NOT NULL,
    payload JSONB NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_url TEXT NOT NULL,
    http_status INTEGER NOT NULL,

    PRIMARY KEY (batch_id, repository_full_name, github_issue_id),

    CONSTRAINT github_issues_raw_load_fk
        FOREIGN KEY (batch_id, repository_full_name)
        REFERENCES stg.repository_loads (batch_id, repository_full_name),

    CONSTRAINT github_issues_raw_http_status_check
        CHECK (http_status = 200)
);

CREATE INDEX IF NOT EXISTS load_batches_success_order_idx
    ON stg.load_batches (started_at, batch_id)
    WHERE status = 'success';

COMMIT;
