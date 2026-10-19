-- Два отдельных батча.
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
ORDER BY started_at, batch_id;

-- Фактические количества строк в каждом батче.
SELECT
    b.run_id,
    r.repository_full_name,
    r.status,
    r.issue_page_count,
    r.issue_record_count,
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
    ) AS actual_issue_count
FROM stg.repository_loads r
JOIN stg.load_batches b USING (batch_id)
WHERE b.dag_id = 'github_to_stg'
ORDER BY b.started_at, b.batch_id, r.repository_full_name;

-- Сколько объектов присутствует в обоих снимках.
SELECT
    first_snapshot.repository_full_name,
    count(*) AS items_in_both_snapshots
FROM stg.github_issues_raw first_snapshot
JOIN stg.load_batches first_batch
    ON first_batch.batch_id = first_snapshot.batch_id
JOIN stg.github_issues_raw second_snapshot
    ON second_snapshot.repository_full_name =
       first_snapshot.repository_full_name
   AND second_snapshot.github_issue_id =
       first_snapshot.github_issue_id
JOIN stg.load_batches second_batch
    ON second_batch.batch_id = second_snapshot.batch_id
WHERE first_batch.dag_id = 'github_to_stg'
  AND first_batch.run_id = 'first_stg_load'
  AND second_batch.dag_id = 'github_to_stg'
  AND second_batch.run_id = 'second_stg_load'
GROUP BY first_snapshot.repository_full_name
ORDER BY first_snapshot.repository_full_name;