BEGIN READ ONLY;

SET LOCAL ROLE ppad_dds_loader;

SELECT current_database(), current_user;

SELECT
    rolname,
    rolsuper,
    rolcreatedb,
    rolcreaterole,
    rolreplication,
    rolbypassrls
FROM pg_roles
WHERE rolname = current_user;

SELECT
    schema_name,
    has_schema_privilege(
        current_user, schema_name, 'USAGE'
    ) AS can_use,
    has_schema_privilege(
        current_user, schema_name, 'CREATE'
    ) AS can_create
FROM (
    VALUES ('stg'), ('dds')
) AS schemas(schema_name);

SELECT
    table_schema,
    table_name,
    has_table_privilege(
        current_user,
        format('%I.%I', table_schema, table_name),
        'SELECT'
    ) AS can_select,
    has_table_privilege(
        current_user,
        format('%I.%I', table_schema, table_name),
        'INSERT'
    ) AS can_insert,
    has_any_column_privilege(
        current_user,
        format('%I.%I', table_schema, table_name),
        'UPDATE'
    ) AS can_update_any_column,
    has_table_privilege(
        current_user,
        format('%I.%I', table_schema, table_name),
        'DELETE'
    ) AS can_delete,
    has_table_privilege(
        current_user,
        format('%I.%I', table_schema, table_name),
        'TRUNCATE'
    ) AS can_truncate
FROM information_schema.tables
WHERE table_schema IN ('stg', 'dds')
  AND table_type = 'BASE TABLE'
ORDER BY table_schema, table_name;

SELECT
    table_name,
    column_name,
    has_column_privilege(
        current_user,
        format('dds.%I', table_name),
        column_name,
        'UPDATE'
    ) AS can_update
FROM information_schema.columns
WHERE table_schema = 'dds'
  AND table_name IN ('repositories_scd2', 'issues_scd2')
ORDER BY table_name, ordinal_position;

ROLLBACK;