SELECT current_database();

SELECT
    'repositories_scd2' AS table_name,
    count(*) AS total_versions,
    count(*) FILTER (WHERE is_current) AS current_versions,
    count(*) FILTER (WHERE NOT is_current) AS closed_versions
FROM dds.repositories_scd2

UNION ALL

SELECT
    'issues_scd2',
    count(*),
    count(*) FILTER (WHERE is_current),
    count(*) FILTER (WHERE NOT is_current)
FROM dds.issues_scd2;

SELECT
    b.run_id,
    p.repository_versions_inserted,
    p.repository_versions_closed,
    p.issue_versions_inserted,
    p.issue_versions_closed
FROM dds.processed_batches p
JOIN stg.load_batches b USING (batch_id)
ORDER BY p.stg_started_at, p.batch_id;

-- Проверка непрерывности соседних версий.
WITH versions AS (
    SELECT
        'repository' AS entity_type,
        github_repository_id AS entity_id,
        valid_from,
        valid_to,
        lead(valid_from) OVER (
            PARTITION BY github_repository_id
            ORDER BY valid_from
        ) AS next_valid_from
    FROM dds.repositories_scd2

    UNION ALL

    SELECT
        'issue',
        github_issue_id,
        valid_from,
        valid_to,
        lead(valid_from) OVER (
            PARTITION BY github_issue_id
            ORDER BY valid_from
        )
    FROM dds.issues_scd2
)
SELECT count(*) AS broken_version_boundaries
FROM versions
WHERE valid_to IS DISTINCT FROM next_valid_from;
