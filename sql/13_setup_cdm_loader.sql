\set ON_ERROR_STOP on
\getenv cdm_password CDM_LOADER_PASSWORD

BEGIN;

SELECT
    'CREATE ROLE ppad_cdm_loader LOGIN
     NOSUPERUSER NOCREATEDB NOCREATEROLE
     NOREPLICATION NOBYPASSRLS'
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = 'ppad_cdm_loader'
)
\gexec

ALTER ROLE ppad_cdm_loader
    WITH LOGIN
    NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOREPLICATION NOBYPASSRLS
    PASSWORD :'cdm_password';

SELECT format(
    'GRANT CONNECT ON DATABASE %I TO ppad_cdm_loader',
    current_database()
)
\gexec

GRANT USAGE ON SCHEMA dds, cdm
TO ppad_cdm_loader;

GRANT SELECT
ON TABLE
    dds.repositories_scd2,
    dds.issues_scd2,
    dds.processed_batches
TO ppad_cdm_loader;

GRANT SELECT, INSERT
ON TABLE
    cdm.processed_batches
TO ppad_cdm_loader;

GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE
    cdm.repository_summary,
    cdm.repository_version_history,
    cdm.activity_monthly,
    cdm.contributor_activity,
    cdm.label_analytics,
    cdm.issue_lifecycle_current
TO ppad_cdm_loader;

COMMIT;
