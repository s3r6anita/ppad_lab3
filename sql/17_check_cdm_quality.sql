BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;

SET LOCAL TIME ZONE 'UTC';

WITH repo_check AS (
    SELECT
        (SELECT count(*) FROM dds.repositories_scd2 WHERE is_current) AS dds_current_repos,
        (SELECT count(*) FROM cdm.repository_summary) AS cdm_summary_repos,
        (
            SELECT count(*)
            FROM dds.repositories_scd2 d
            LEFT JOIN cdm.repository_summary c
                ON d.github_repository_id = c.github_repository_id
            WHERE d.is_current AND c.github_repository_id IS NULL
        ) AS missing_repos
),
item_counts AS (
    SELECT
        (SELECT count(*) FROM dds.issues_scd2 WHERE is_current) AS dds_items,
        (SELECT coalesce(sum(total_items_count), 0) FROM cdm.repository_summary) AS summary_items,
        (SELECT count(*) FROM cdm.issue_lifecycle_current) AS lifecycle_items
),
open_issues AS (
    SELECT
        (
            SELECT count(*)
            FROM dds.issues_scd2
            WHERE is_current AND NOT is_pull_request AND state = 'open'
        ) AS dds_count,
        (SELECT coalesce(sum(open_issues_count), 0) FROM cdm.repository_summary) AS summary_count,
        (
            SELECT count(*)
            FROM cdm.issue_lifecycle_current
            WHERE NOT is_pull_request AND state = 'open'
        ) AS lifecycle_count
),
closed_issues AS (
    SELECT
        (
            SELECT count(*)
            FROM dds.issues_scd2
            WHERE is_current AND NOT is_pull_request AND state = 'closed'
        ) AS dds_count,
        (SELECT coalesce(sum(closed_issues_count), 0) FROM cdm.repository_summary) AS summary_count,
        (
            SELECT count(*)
            FROM cdm.issue_lifecycle_current
            WHERE NOT is_pull_request AND state = 'closed'
        ) AS lifecycle_count
),
open_prs AS (
    SELECT
        (
            SELECT count(*)
            FROM dds.issues_scd2
            WHERE is_current AND is_pull_request AND state = 'open'
        ) AS dds_count,
        (SELECT coalesce(sum(open_prs_count), 0) FROM cdm.repository_summary) AS summary_count,
        (
            SELECT count(*)
            FROM cdm.issue_lifecycle_current
            WHERE is_pull_request AND state = 'open'
        ) AS lifecycle_count
),
closed_prs AS (
    SELECT
        (
            SELECT count(*)
            FROM dds.issues_scd2
            WHERE is_current AND is_pull_request AND state = 'closed'
        ) AS dds_count,
        (SELECT coalesce(sum(closed_prs_count), 0) FROM cdm.repository_summary) AS summary_count,
        (
            SELECT count(*)
            FROM cdm.issue_lifecycle_current
            WHERE is_pull_request AND state = 'closed'
        ) AS lifecycle_count
),
version_check AS (
    SELECT
        (SELECT count(*) FROM dds.repositories_scd2) AS dds_total_versions,
        (SELECT count(*) FROM cdm.repository_version_history) AS cdm_history_rows
),
monthly_check AS (
    SELECT
        (SELECT count(*) FROM dds.issues_scd2 WHERE is_current) AS expected_created,
        (SELECT coalesce(sum(created_count), 0) FROM cdm.activity_monthly) AS monthly_created
),
contributor_check AS (
    SELECT
        (SELECT count(*) FROM dds.issues_scd2 WHERE is_current) AS expected_items,
        (SELECT coalesce(sum(total_items_count), 0) FROM cdm.contributor_activity) AS contributor_items
)
SELECT
    'check_1_repository_coverage' AS check_name,
    dds_current_repos::text AS dds_value,
    cdm_summary_repos::text AS cdm_value,
    CASE
        WHEN dds_current_repos = cdm_summary_repos AND missing_repos = 0 THEN 'OK'
        ELSE 'FAIL'
    END AS status
FROM repo_check

UNION ALL

SELECT
    'check_2_total_items_count' AS check_name,
    dds_items::text AS dds_value,
    format('summary=%s; lifecycle=%s', summary_items, lifecycle_items) AS cdm_value,
    CASE
        WHEN dds_items = summary_items AND dds_items = lifecycle_items THEN 'OK'
        ELSE 'FAIL'
    END AS status
FROM item_counts

UNION ALL

SELECT
    'check_3_open_issues_count' AS check_name,
    dds_count::text AS dds_value,
    format('summary=%s; lifecycle=%s', summary_count, lifecycle_count) AS cdm_value,
    CASE
        WHEN dds_count = summary_count AND dds_count = lifecycle_count THEN 'OK'
        ELSE 'FAIL'
    END AS status
FROM open_issues

UNION ALL

SELECT
    'check_4_closed_issues_count' AS check_name,
    dds_count::text AS dds_value,
    format('summary=%s; lifecycle=%s', summary_count, lifecycle_count) AS cdm_value,
    CASE
        WHEN dds_count = summary_count AND dds_count = lifecycle_count THEN 'OK'
        ELSE 'FAIL'
    END AS status
FROM closed_issues

UNION ALL

SELECT
    'check_5_open_prs_count' AS check_name,
    dds_count::text AS dds_value,
    format('summary=%s; lifecycle=%s', summary_count, lifecycle_count) AS cdm_value,
    CASE
        WHEN dds_count = summary_count AND dds_count = lifecycle_count THEN 'OK'
        ELSE 'FAIL'
    END AS status
FROM open_prs

UNION ALL

SELECT
    'check_6_closed_prs_count' AS check_name,
    dds_count::text AS dds_value,
    format('summary=%s; lifecycle=%s', summary_count, lifecycle_count) AS cdm_value,
    CASE
        WHEN dds_count = summary_count AND dds_count = lifecycle_count THEN 'OK'
        ELSE 'FAIL'
    END AS status
FROM closed_prs

UNION ALL

SELECT
    'check_7_version_history_count' AS check_name,
    dds_total_versions::text AS dds_value,
    cdm_history_rows::text AS cdm_value,
    CASE
        WHEN dds_total_versions = cdm_history_rows THEN 'OK'
        ELSE 'FAIL'
    END AS status
FROM version_check

UNION ALL

SELECT
    'check_8_monthly_created_sum' AS check_name,
    expected_created::text AS dds_value,
    monthly_created::text AS cdm_value,
    CASE
        WHEN expected_created = monthly_created THEN 'OK'
        ELSE 'FAIL'
    END AS status
FROM monthly_check

UNION ALL

SELECT
    'check_9_contributor_items_sum' AS check_name,
    expected_items::text AS dds_value,
    contributor_items::text AS cdm_value,
    CASE
        WHEN expected_items = contributor_items THEN 'OK'
        ELSE 'FAIL'
    END AS status
FROM contributor_check

ORDER BY check_name;

COMMIT;
