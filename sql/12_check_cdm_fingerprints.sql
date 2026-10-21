BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;

SET LOCAL TIME ZONE 'UTC';

SELECT
    'activity_monthly' AS table_name,
    count(*) AS row_count,
    encode(
        sha256(
            convert_to(
                coalesce(
                    string_agg(
                        to_jsonb(t)::text,
                        E'\n' ORDER BY github_repository_id, period_month, item_type
                    ),
                    ''
                ),
                'UTF8'
            )
        ),
        'hex'
    ) AS table_fingerprint
FROM cdm.activity_monthly t

UNION ALL

SELECT
    'contributor_activity',
    count(*),
    encode(
        sha256(
            convert_to(
                coalesce(
                    string_agg(
                        to_jsonb(t)::text,
                        E'\n' ORDER BY github_repository_id, author_key
                    ),
                    ''
                ),
                'UTF8'
            )
        ),
        'hex'
    )
FROM cdm.contributor_activity t

UNION ALL

SELECT
    'issue_lifecycle_current',
    count(*),
    encode(
        sha256(
            convert_to(
                coalesce(
                    string_agg(
                        to_jsonb(t)::text,
                        E'\n' ORDER BY github_issue_id
                    ),
                    ''
                ),
                'UTF8'
            )
        ),
        'hex'
    )
FROM cdm.issue_lifecycle_current t

UNION ALL

SELECT
    'label_analytics',
    count(*),
    encode(
        sha256(
            convert_to(
                coalesce(
                    string_agg(
                        to_jsonb(t)::text,
                        E'\n' ORDER BY github_repository_id, label_id
                    ),
                    ''
                ),
                'UTF8'
            )
        ),
        'hex'
    )
FROM cdm.label_analytics t

UNION ALL

SELECT
    'processed_batches',
    count(*),
    encode(
        sha256(
            convert_to(
                coalesce(
                    string_agg(
                        to_jsonb(t)::text,
                        E'\n' ORDER BY batch_id
                    ),
                    ''
                ),
                'UTF8'
            )
        ),
        'hex'
    )
FROM cdm.processed_batches t

UNION ALL

SELECT
    'repository_summary',
    count(*),
    encode(
        sha256(
            convert_to(
                coalesce(
                    string_agg(
                        to_jsonb(t)::text,
                        E'\n' ORDER BY github_repository_id
                    ),
                    ''
                ),
                'UTF8'
            )
        ),
        'hex'
    )
FROM cdm.repository_summary t

UNION ALL

SELECT
    'repository_version_history',
    count(*),
    encode(
        sha256(
            convert_to(
                coalesce(
                    string_agg(
                        to_jsonb(t)::text,
                        E'\n' ORDER BY repository_version_id
                    ),
                    ''
                ),
                'UTF8'
            )
        ),
        'hex'
    )
FROM cdm.repository_version_history t

ORDER BY table_name;

COMMIT;
