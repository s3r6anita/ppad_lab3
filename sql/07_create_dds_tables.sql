BEGIN;

CREATE SCHEMA IF NOT EXISTS dds;
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE dds.processed_batches (
    batch_id uuid PRIMARY KEY
        REFERENCES stg.load_batches (batch_id),
    stg_started_at timestamptz NOT NULL,
    processed_at timestamptz NOT NULL DEFAULT clock_timestamp(),

    repository_record_count integer NOT NULL
        CHECK (repository_record_count >= 0),
    issue_record_count integer NOT NULL
        CHECK (issue_record_count >= 0),

    repository_versions_inserted integer NOT NULL
        CHECK (repository_versions_inserted >= 0),
    repository_versions_closed integer NOT NULL
        CHECK (repository_versions_closed >= 0),
    issue_versions_inserted integer NOT NULL
        CHECK (issue_versions_inserted >= 0),
    issue_versions_closed integer NOT NULL
        CHECK (issue_versions_closed >= 0)
);

CREATE TABLE dds.repositories_scd2 (
    repository_version_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    github_repository_id bigint NOT NULL
        CHECK (github_repository_id > 0),

    full_name text NOT NULL,
    description text,
    language text,
    stars_count bigint NOT NULL CHECK (stars_count >= 0),
    forks_count bigint NOT NULL CHECK (forks_count >= 0),
    open_issues_count bigint NOT NULL CHECK (open_issues_count >= 0),
    archived boolean NOT NULL,
    source_created_at timestamptz NOT NULL,
    source_updated_at timestamptz,

    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    is_current boolean NOT NULL DEFAULT true,
    hash_diff text NOT NULL
        CHECK (hash_diff ~ '^[0-9a-f]{64}$'),
    source_batch_id uuid NOT NULL
        REFERENCES stg.load_batches (batch_id),
    dds_loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(),

    CONSTRAINT repositories_scd2_current_ck
        CHECK (is_current = (valid_to IS NULL)),
    CONSTRAINT repositories_scd2_interval_ck
        CHECK (valid_to IS NULL OR valid_to > valid_from),

    CONSTRAINT repositories_scd2_no_overlap
        EXCLUDE USING gist (
            github_repository_id WITH =,
            tstzrange(valid_from, valid_to, '[)') WITH &&
        )
);

CREATE UNIQUE INDEX repositories_scd2_current_uq
    ON dds.repositories_scd2 (github_repository_id)
    WHERE is_current;

CREATE INDEX repositories_scd2_batch_idx
    ON dds.repositories_scd2 (source_batch_id);

CREATE TABLE dds.issues_scd2 (
    issue_version_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    github_issue_id bigint NOT NULL CHECK (github_issue_id > 0),
    github_repository_id bigint NOT NULL
        CHECK (github_repository_id > 0),

    issue_number bigint NOT NULL CHECK (issue_number > 0),
    title text NOT NULL,
    state text NOT NULL CHECK (state IN ('open', 'closed')),
    is_pull_request boolean NOT NULL,

    author_id bigint CHECK (author_id > 0),
    author_login text,
    source_created_at timestamptz NOT NULL,
    source_updated_at timestamptz,
    source_closed_at timestamptz,

    labels jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(labels) = 'array'),
    assignees jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(assignees) = 'array'),

    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    is_current boolean NOT NULL DEFAULT true,
    hash_diff text NOT NULL
        CHECK (hash_diff ~ '^[0-9a-f]{64}$'),
    source_batch_id uuid NOT NULL
        REFERENCES stg.load_batches (batch_id),
    dds_loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(),

    CONSTRAINT issues_scd2_current_ck
        CHECK (is_current = (valid_to IS NULL)),
    CONSTRAINT issues_scd2_interval_ck
        CHECK (valid_to IS NULL OR valid_to > valid_from),

    CONSTRAINT issues_scd2_no_overlap
        EXCLUDE USING gist (
            github_issue_id WITH =,
            tstzrange(valid_from, valid_to, '[)') WITH &&
        )
);

CREATE UNIQUE INDEX issues_scd2_current_uq
    ON dds.issues_scd2 (github_issue_id)
    WHERE is_current;

CREATE INDEX issues_scd2_repository_idx
    ON dds.issues_scd2 (github_repository_id);

CREATE INDEX issues_scd2_batch_idx
    ON dds.issues_scd2 (source_batch_id);

CREATE INDEX processed_batches_order_idx
    ON dds.processed_batches (stg_started_at, batch_id);

COMMIT;
