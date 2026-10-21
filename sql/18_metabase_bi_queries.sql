-- Card 1: KPI Summary (cdm.repository_summary)
SELECT
    count(*)::bigint AS total_repositories,
    sum(total_items_count)::bigint AS total_items,
    sum(issues_total_count)::bigint AS total_issues,
    sum(prs_total_count)::bigint AS total_prs,
    sum(open_issues_count + open_prs_count)::bigint AS total_open_items,
    sum(closed_issues_count + closed_prs_count)::bigint AS total_closed_items,
    round(
        sum(closed_issues_count + closed_prs_count)::numeric * 100.0 /
        nullif(sum(total_items_count), 0),
        2
    ) AS overall_close_rate_pct,
    round(avg(avg_issue_resolution_hours), 2) AS avg_issue_sla_hours,
    round(avg(avg_pr_resolution_hours), 2) AS avg_pr_sla_hours,
    sum(unique_authors_count)::bigint AS total_active_authors
FROM cdm.repository_summary;

-- Card 2: Repository Overview Table (cdm.repository_summary)
SELECT
    full_name AS repository,
    stars_count AS stars,
    forks_count AS forks,
    open_issues_count AS open_issues,
    closed_issues_count AS closed_issues,
    issue_close_rate_pct,
    open_prs_count AS open_prs,
    closed_prs_count AS closed_prs,
    pr_close_rate_pct,
    median_issue_resolution_hours,
    avg_issue_resolution_hours,
    unique_authors_count,
    unassigned_open_items_count,
    unlabeled_open_items_count,
    repository_versions_count AS scd2_versions
FROM cdm.repository_summary
ORDER BY stars_count DESC, full_name;

-- Card 3: Monthly Activity Dynamics (cdm.activity_monthly)
SELECT
    to_char(period_month, 'YYYY-MM') AS month,
    item_type,
    sum(created_count)::bigint AS items_created,
    sum(closed_count)::bigint AS items_closed,
    sum(net_open_delta)::bigint AS net_delta,
    max(cumulative_created_count)::bigint AS cumulative_created
FROM cdm.activity_monthly
GROUP BY period_month, item_type
ORDER BY period_month, item_type;

-- Card 4: Issues vs PRs Breakdown (cdm.repository_summary)
SELECT
    full_name AS repository,
    issues_total_count AS total_issues,
    closed_issues_count AS closed_issues,
    open_issues_count AS open_issues,
    prs_total_count AS total_prs,
    closed_prs_count AS closed_prs,
    open_prs_count AS open_prs,
    round(
        prs_total_count::numeric * 100.0 / nullif(total_items_count, 0),
        2
    ) AS pr_share_pct
FROM cdm.repository_summary
ORDER BY total_items_count DESC;

-- Card 5: Resolution Time & Age Distribution (cdm.issue_lifecycle_current, cdm.repository_summary)
SELECT
    r.full_name AS repository,
    i.is_pull_request,
    count(*) AS items_count,
    round(avg(i.resolution_hours), 2) AS avg_resolution_hours,
    percentile_cont(0.50) WITHIN GROUP (ORDER BY i.resolution_hours) AS p50_resolution_hours,
    percentile_cont(0.90) WITHIN GROUP (ORDER BY i.resolution_hours) AS p90_resolution_hours,
    round(avg(i.age_days), 2) AS avg_age_days,
    max(i.age_days) AS max_age_days
FROM cdm.issue_lifecycle_current i
JOIN cdm.repository_summary r
    ON i.github_repository_id = r.github_repository_id
GROUP BY r.full_name, i.is_pull_request
ORDER BY r.full_name, i.is_pull_request;

-- Card 6: Top Contributors (cdm.contributor_activity)
SELECT
    author_login,
    full_name AS repository,
    total_items_count,
    issues_created_count,
    prs_created_count,
    closed_issues_count,
    closed_prs_count,
    avg_resolution_hours
FROM cdm.contributor_activity
ORDER BY total_items_count DESC, prs_created_count DESC, author_login
LIMIT 20;

-- Card 7: Label Analytics (cdm.label_analytics)
SELECT
    label_name,
    full_name AS repository,
    total_items_count,
    open_items_count,
    closed_items_count,
    close_rate_pct,
    avg_resolution_hours
FROM cdm.label_analytics
ORDER BY total_items_count DESC, close_rate_pct DESC
LIMIT 25;

-- Card 8: SCD2 Repository Version History (cdm.repository_version_history)
SELECT
    full_name AS repository,
    version_number,
    stars_count,
    stars_delta,
    forks_count,
    forks_delta,
    open_issues_count,
    open_issues_delta,
    valid_from,
    valid_to,
    is_current
FROM cdm.repository_version_history
ORDER BY github_repository_id, version_number;
