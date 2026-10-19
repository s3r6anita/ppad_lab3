SELECT
    batch_id,
    run_id,
    status,
    expected_repository_count,
    started_at,
    finished_at,
    error_message
FROM stg.load_batches
WHERE dag_id = 'github_to_stg'
  AND run_id = 'first_stg_load';

SELECT
    r.repository_full_name,
    r.status,
    r.repository_record_count,
    r.issue_record_count,
    r.issue_page_count,
    (
        SELECT count(*)
        FROM stg.github_repositories_raw p
        WHERE p.batch_id = r.batch_id
          AND p.repository_full_name = r.repository_full_name
    ) AS actual_repository_count,
    (
        SELECT count(*)
        FROM stg.github_issues_raw i
        WHERE i.batch_id = r.batch_id
          AND i.repository_full_name = r.repository_full_name
    ) AS actual_issue_count,
    r.error_message
FROM stg.repository_loads r
JOIN stg.load_batches b USING (batch_id)
WHERE b.dag_id = 'github_to_stg'
  AND b.run_id = 'first_stg_load'
ORDER BY r.repository_full_name;

SELECT
    i.repository_full_name,
    count(*) AS total_items,
    count(*) FILTER (
        WHERE NOT (i.payload ? 'pull_request')
    ) AS issues_only,
    count(*) FILTER (
        WHERE i.payload ? 'pull_request'
    ) AS pull_requests
FROM stg.github_issues_raw i
JOIN stg.load_batches b USING (batch_id)
WHERE b.dag_id = 'github_to_stg'
  AND b.run_id = 'first_stg_load'
GROUP BY i.repository_full_name
ORDER BY i.repository_full_name;