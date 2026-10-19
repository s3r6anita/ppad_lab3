SELECT tablename
FROM pg_tables
WHERE schemaname = 'stg'
ORDER BY tablename;

SELECT
    conrelid::regclass::text AS table_name,
    contype AS constraint_type,
    count(*) AS constraint_count
FROM pg_constraint
WHERE connamespace = 'stg'::regnamespace
GROUP BY conrelid, contype
ORDER BY 1, 2;

SELECT 'load_batches' AS table_name, count(*) AS row_count
FROM stg.load_batches
UNION ALL
SELECT 'repository_loads', count(*)
FROM stg.repository_loads
UNION ALL
SELECT 'github_repositories_raw', count(*)
FROM stg.github_repositories_raw
UNION ALL
SELECT 'github_issues_raw', count(*)
FROM stg.github_issues_raw
ORDER BY 1;
