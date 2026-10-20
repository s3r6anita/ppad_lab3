BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;

SET LOCAL TIME ZONE 'UTC';

SELECT
    'repositories_scd2' AS table_name,
    count(*) AS row_count,
    encode(
        sha256(
            convert_to(
                coalesce(
                    string_agg(
                        to_jsonb(r)::text,
                        E'\n' ORDER BY repository_version_id
                    ),
                    ''
                ),
                'UTF8'
            )
        ),
        'hex'
    ) AS table_fingerprint
FROM dds.repositories_scd2 r

UNION ALL

SELECT
    'issues_scd2',
    count(*),
    encode(
        sha256(
            convert_to(
                coalesce(
                    string_agg(
                        to_jsonb(i)::text,
                        E'\n' ORDER BY issue_version_id
                    ),
                    ''
                ),
                'UTF8'
            )
        ),
        'hex'
    )
FROM dds.issues_scd2 i

UNION ALL

SELECT
    'processed_batches',
    count(*),
    encode(
        sha256(
            convert_to(
                coalesce(
                    string_agg(
                        to_jsonb(p)::text,
                        E'\n' ORDER BY batch_id
                    ),
                    ''
                ),
                'UTF8'
            )
        ),
        'hex'
    )
FROM dds.processed_batches p

ORDER BY table_name;

COMMIT;
