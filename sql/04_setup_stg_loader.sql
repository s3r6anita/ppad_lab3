\set ON_ERROR_STOP on
\getenv loader_password STG_LOADER_PASSWORD

BEGIN;

SELECT 'CREATE ROLE ppad_loader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION'
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = 'ppad_loader'
)
\gexec

ALTER ROLE ppad_loader
    WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
    PASSWORD :'loader_password';

SELECT format(
    'GRANT CONNECT ON DATABASE %I TO ppad_loader',
    current_database()
)
\gexec

GRANT USAGE ON SCHEMA stg TO ppad_loader;

GRANT SELECT, INSERT, UPDATE
ON TABLE
    stg.load_batches,
    stg.repository_loads,
    stg.github_repositories_raw,
    stg.github_issues_raw
TO ppad_loader;

COMMIT;
