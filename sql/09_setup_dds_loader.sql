\set ON_ERROR_STOP on
\getenv dds_password DDS_LOADER_PASSWORD

BEGIN;

SELECT
    'CREATE ROLE ppad_dds_loader LOGIN
     NOSUPERUSER NOCREATEDB NOCREATEROLE
     NOREPLICATION NOBYPASSRLS'
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = 'ppad_dds_loader'
)
\gexec

ALTER ROLE ppad_dds_loader
    WITH LOGIN
    NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS
    PASSWORD :'dds_password';

SELECT format(
    'GRANT CONNECT ON DATABASE %I TO ppad_dds_loader',
    current_database()
)
\gexec

GRANT USAGE ON SCHEMA stg, dds
TO ppad_dds_loader;

GRANT SELECT
ON TABLE
    stg.load_batches,
    stg.repository_loads,
    stg.github_repositories_raw,
    stg.github_issues_raw
TO ppad_dds_loader;

GRANT SELECT, INSERT
ON TABLE
    dds.repositories_scd2,
    dds.issues_scd2,
    dds.processed_batches
TO ppad_dds_loader;

GRANT UPDATE (valid_to, is_current)
ON TABLE dds.repositories_scd2
TO ppad_dds_loader;

GRANT UPDATE (valid_to, is_current)
ON TABLE dds.issues_scd2
TO ppad_dds_loader;

GRANT USAGE
ON SEQUENCE
    dds.repositories_scd2_repository_version_id_seq,
    dds.issues_scd2_issue_version_id_seq
TO ppad_dds_loader;

COMMIT;