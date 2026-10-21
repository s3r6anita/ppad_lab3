BEGIN;

CREATE SCHEMA IF NOT EXISTS cdm;

CREATE TABLE cdm.processed_batches (
    batch_id uuid PRIMARY KEY
        REFERENCES dds.processed_batches (batch_id),
    stg_started_at timestamptz NOT NULL,
    dds_processed_at timestamptz NOT NULL,
    processed_at timestamptz NOT NULL DEFAULT clock_timestamp(),

    repository_summary_count integer NOT NULL
        CHECK (repository_summary_count >= 0),
    repository_history_count integer NOT NULL
        CHECK (repository_history_count >= 0),
    activity_monthly_count integer NOT NULL
        CHECK (activity_monthly_count >= 0),
    contributor_activity_count integer NOT NULL
        CHECK (contributor_activity_count >= 0),
    label_analytics_count integer NOT NULL
        CHECK (label_analytics_count >= 0),
    issue_lifecycle_count integer NOT NULL
        CHECK (issue_lifecycle_count >= 0)
);

CREATE TABLE cdm.repository_summary (
    github_repository_id bigint PRIMARY KEY
        CHECK (github_repository_id > 0),
    full_name text NOT NULL UNIQUE,
    description text,
    language text,
    archived boolean NOT NULL,
    source_created_at timestamptz NOT NULL,
    source_updated_at timestamptz,

    stars_count bigint NOT NULL CHECK (stars_count >= 0),
    forks_count bigint NOT NULL CHECK (forks_count >= 0),
    open_issues_api_count bigint NOT NULL CHECK (open_issues_api_count >= 0),

    total_items_count integer NOT NULL CHECK (total_items_count >= 0),
    issues_total_count integer NOT NULL CHECK (issues_total_count >= 0),
    prs_total_count integer NOT NULL CHECK (prs_total_count >= 0),
    open_issues_count integer NOT NULL CHECK (open_issues_count >= 0),
    closed_issues_count integer NOT NULL CHECK (closed_issues_count >= 0),
    issue_close_rate_pct numeric(5,2) NOT NULL
        CHECK (issue_close_rate_pct BETWEEN 0 AND 100),
    open_prs_count integer NOT NULL CHECK (open_prs_count >= 0),
    closed_prs_count integer NOT NULL CHECK (closed_prs_count >= 0),
    pr_close_rate_pct numeric(5,2) NOT NULL
        CHECK (pr_close_rate_pct BETWEEN 0 AND 100),

    avg_issue_resolution_hours numeric(12,2)
        CHECK (avg_issue_resolution_hours IS NULL OR avg_issue_resolution_hours >= 0),
    median_issue_resolution_hours numeric(12,2)
        CHECK (median_issue_resolution_hours IS NULL OR median_issue_resolution_hours >= 0),
    avg_pr_resolution_hours numeric(12,2)
        CHECK (avg_pr_resolution_hours IS NULL OR avg_pr_resolution_hours >= 0),
    median_pr_resolution_hours numeric(12,2)
        CHECK (median_pr_resolution_hours IS NULL OR median_pr_resolution_hours >= 0),

    unique_authors_count integer NOT NULL CHECK (unique_authors_count >= 0),
    unassigned_open_items_count integer NOT NULL CHECK (unassigned_open_items_count >= 0),
    unlabeled_open_items_count integer NOT NULL CHECK (unlabeled_open_items_count >= 0),

    first_item_created_at timestamptz,
    last_item_created_at timestamptz,
    last_item_closed_at timestamptz,

    repository_versions_count integer NOT NULL CHECK (repository_versions_count >= 1),
    issue_versions_changed_count integer NOT NULL CHECK (issue_versions_changed_count >= 0),

    valid_from timestamptz NOT NULL,
    source_batch_id uuid NOT NULL
        REFERENCES dds.processed_batches (batch_id),
    cdm_loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX repository_summary_batch_idx
    ON cdm.repository_summary (source_batch_id);

CREATE TABLE cdm.repository_version_history (
    repository_version_id bigint PRIMARY KEY
        CHECK (repository_version_id > 0),
    github_repository_id bigint NOT NULL
        CHECK (github_repository_id > 0),
    full_name text NOT NULL,
    version_number integer NOT NULL
        CHECK (version_number >= 1),
    stars_count bigint NOT NULL CHECK (stars_count >= 0),
    stars_delta bigint NOT NULL,
    forks_count bigint NOT NULL CHECK (forks_count >= 0),
    forks_delta bigint NOT NULL,
    open_issues_count bigint NOT NULL CHECK (open_issues_count >= 0),
    open_issues_delta bigint NOT NULL,
    archived boolean NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    is_current boolean NOT NULL,
    source_batch_id uuid NOT NULL
        REFERENCES dds.processed_batches (batch_id),
    cdm_loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX repository_version_history_repo_idx
    ON cdm.repository_version_history (github_repository_id, version_number);

CREATE INDEX repository_version_history_batch_idx
    ON cdm.repository_version_history (source_batch_id);

CREATE TABLE cdm.activity_monthly (
    github_repository_id bigint NOT NULL
        CHECK (github_repository_id > 0),
    period_month date NOT NULL,
    item_type text NOT NULL
        CHECK (item_type IN ('issue', 'pull_request')),
    full_name text NOT NULL,
    created_count integer NOT NULL CHECK (created_count >= 0),
    closed_count integer NOT NULL CHECK (closed_count >= 0),
    net_open_delta integer NOT NULL,
    cumulative_created_count integer NOT NULL CHECK (cumulative_created_count >= 0),
    cumulative_closed_count integer NOT NULL CHECK (cumulative_closed_count >= 0),
    avg_resolution_hours numeric(12,2)
        CHECK (avg_resolution_hours IS NULL OR avg_resolution_hours >= 0),
    source_batch_id uuid NOT NULL
        REFERENCES dds.processed_batches (batch_id),
    cdm_loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(),

    PRIMARY KEY (github_repository_id, period_month, item_type)
);

CREATE INDEX activity_monthly_batch_idx
    ON cdm.activity_monthly (source_batch_id);

CREATE INDEX activity_monthly_period_idx
    ON cdm.activity_monthly (period_month);

CREATE TABLE cdm.contributor_activity (
    github_repository_id bigint NOT NULL
        CHECK (github_repository_id > 0),
    author_key text NOT NULL,
    full_name text NOT NULL,
    author_id bigint CHECK (author_id IS NULL OR author_id > 0),
    author_login text NOT NULL,
    total_items_count integer NOT NULL CHECK (total_items_count > 0),
    issues_created_count integer NOT NULL CHECK (issues_created_count >= 0),
    open_issues_count integer NOT NULL CHECK (open_issues_count >= 0),
    closed_issues_count integer NOT NULL CHECK (closed_issues_count >= 0),
    prs_created_count integer NOT NULL CHECK (prs_created_count >= 0),
    open_prs_count integer NOT NULL CHECK (open_prs_count >= 0),
    closed_prs_count integer NOT NULL CHECK (closed_prs_count >= 0),
    avg_resolution_hours numeric(12,2)
        CHECK (avg_resolution_hours IS NULL OR avg_resolution_hours >= 0),
    first_created_at timestamptz NOT NULL,
    last_created_at timestamptz NOT NULL,
    source_batch_id uuid NOT NULL
        REFERENCES dds.processed_batches (batch_id),
    cdm_loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(),

    PRIMARY KEY (github_repository_id, author_key)
);

CREATE INDEX contributor_activity_batch_idx
    ON cdm.contributor_activity (source_batch_id);

CREATE TABLE cdm.label_analytics (
    github_repository_id bigint NOT NULL
        CHECK (github_repository_id > 0),
    label_id bigint NOT NULL
        CHECK (label_id > 0),
    full_name text NOT NULL,
    label_name text NOT NULL,
    total_items_count integer NOT NULL CHECK (total_items_count > 0),
    issues_count integer NOT NULL CHECK (issues_count >= 0),
    prs_count integer NOT NULL CHECK (prs_count >= 0),
    open_items_count integer NOT NULL CHECK (open_items_count >= 0),
    closed_items_count integer NOT NULL CHECK (closed_items_count >= 0),
    close_rate_pct numeric(5,2) NOT NULL
        CHECK (close_rate_pct BETWEEN 0 AND 100),
    avg_resolution_hours numeric(12,2)
        CHECK (avg_resolution_hours IS NULL OR avg_resolution_hours >= 0),
    source_batch_id uuid NOT NULL
        REFERENCES dds.processed_batches (batch_id),
    cdm_loaded_at timestamptz NOT NULL DEFAULT clock_timestamp(),

    PRIMARY KEY (github_repository_id, label_id)
);

CREATE INDEX label_analytics_batch_idx
    ON cdm.label_analytics (source_batch_id);

CREATE TABLE cdm.issue_lifecycle_current (
    github_issue_id bigint PRIMARY KEY
        CHECK (github_issue_id > 0),
    github_repository_id bigint NOT NULL
        CHECK (github_repository_id > 0),
    repository_full_name text NOT NULL,
    issue_number bigint NOT NULL CHECK (issue_number > 0),
    item_type text NOT NULL
        CHECK (item_type IN ('issue', 'pull_request')),
    is_pull_request boolean NOT NULL,
    title text NOT NULL,
    state text NOT NULL
        CHECK (state IN ('open', 'closed')),
    author_id bigint CHECK (author_id IS NULL OR author_id > 0),
    author_login text,
    source_created_at timestamptz NOT NULL,
    source_updated_at timestamptz,
    source_closed_at timestamptz,
    resolution_hours numeric(12,2)
        CHECK (resolution_hours IS NULL OR resolution_hours >= 0),
    age_days numeric(10,2) NOT NULL CHECK (age_days >= 0),
    labels_count integer NOT NULL CHECK (labels_count >= 0),
    labels_csv text NOT NULL,
    assignees_count integer NOT NULL CHECK (assignees_count >= 0),
    assignees_csv text NOT NULL,
    scd2_versions_count integer NOT NULL CHECK (scd2_versions_count >= 1),
    valid_from timestamptz NOT NULL,
    source_batch_id uuid NOT NULL
        REFERENCES dds.processed_batches (batch_id),
    cdm_loaded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX issue_lifecycle_current_repo_idx
    ON cdm.issue_lifecycle_current (github_repository_id);

CREATE INDEX issue_lifecycle_current_batch_idx
    ON cdm.issue_lifecycle_current (source_batch_id);

CREATE INDEX issue_lifecycle_current_state_idx
    ON cdm.issue_lifecycle_current (state, item_type);

COMMIT;
