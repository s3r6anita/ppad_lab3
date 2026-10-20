BEGIN;

-- Защита от запуска в рабочей базе разработки.
DO $$
BEGIN
    IF current_database() <> 'ppad_dds_test' THEN
        RAISE EXCEPTION 'Run this fixture only in ppad_dds_test';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM dds.processed_batches
        WHERE batch_id = '438e5824-f52e-50bf-a631-7c30618c6770'
    ) THEN
        RAISE EXCEPTION 'Baseline second batch is not processed';
    END IF;
END
$$;

-- Синтетический батч: время на час позже второго.
INSERT INTO stg.load_batches (
    batch_id,
    dag_id,
    run_id,
    status,
    started_at,
    finished_at,
    expected_repository_count
)
SELECT
    '00000000-0000-4000-8000-000000000003'::uuid,
    dag_id,
    'dds_test_change_01',
    'success',
    started_at + interval '1 hour',
    finished_at + interval '1 hour',
    expected_repository_count
FROM stg.load_batches
WHERE batch_id = '438e5824-f52e-50bf-a631-7c30618c6770';

INSERT INTO stg.repository_loads (
    batch_id,
    repository_full_name,
    status,
    started_at,
    finished_at,
    repository_record_count,
    issue_record_count,
    issue_page_count
)
SELECT
    '00000000-0000-4000-8000-000000000003'::uuid,
    repository_full_name,
    status,
    started_at + interval '1 hour',
    finished_at + interval '1 hour',
    repository_record_count,
    issue_record_count,
    issue_page_count
FROM stg.repository_loads
WHERE batch_id = '438e5824-f52e-50bf-a631-7c30618c6770';

INSERT INTO stg.github_repositories_raw (
    batch_id,
    repository_full_name,
    payload,
    source_url,
    http_status
)
SELECT
    '00000000-0000-4000-8000-000000000003'::uuid,
    repository_full_name,
    payload,
    source_url,
    http_status
FROM stg.github_repositories_raw
WHERE batch_id = '438e5824-f52e-50bf-a631-7c30618c6770';

INSERT INTO stg.github_issues_raw (
    batch_id,
    repository_full_name,
    github_issue_id,
    payload,
    source_url,
    http_status
)
SELECT
    '00000000-0000-4000-8000-000000000003'::uuid,
    repository_full_name,
    github_issue_id,
    payload,
    source_url,
    http_status
FROM stg.github_issues_raw
WHERE batch_id = '438e5824-f52e-50bf-a631-7c30618c6770';

-- Меняем ровно один репозиторий и один issue.
DO $$
DECLARE
    affected integer;
BEGIN
    UPDATE stg.github_repositories_raw
    SET payload = jsonb_set(
        payload,
        '{description}',
        to_jsonb(
            coalesce(payload ->> 'description', '')
            || ' [SYNTHETIC DDS TEST]'
        )
    )
    WHERE batch_id = '00000000-0000-4000-8000-000000000003'
      AND repository_full_name = 'arkivanov/Decompose';

    GET DIAGNOSTICS affected = ROW_COUNT;
    IF affected <> 1 THEN
        RAISE EXCEPTION 'Expected one repository, got %', affected;
    END IF;

    UPDATE stg.github_issues_raw
    SET payload = jsonb_set(
        payload,
        '{title}',
        to_jsonb(
            (payload ->> 'title') || ' [SYNTHETIC DDS TEST]'
        )
    )
    WHERE batch_id = '00000000-0000-4000-8000-000000000003'
      AND github_issue_id = 1079462603;

    GET DIAGNOSTICS affected = ROW_COUNT;
    IF affected <> 1 THEN
        RAISE EXCEPTION 'Expected one issue, got %', affected;
    END IF;
END
$$;

COMMIT;
