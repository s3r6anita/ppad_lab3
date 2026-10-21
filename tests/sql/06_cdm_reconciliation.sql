BEGIN;

-- Защита от запуска в рабочей базе разработки.
DO $$
BEGIN
    IF current_database() NOT LIKE '%test%' AND current_database() NOT LIKE '%verify%' THEN
        RAISE EXCEPTION 'Run this fixture only in test or verify databases (e.g. ppad_cdm_verify, ppad_dds_test)';
    END IF;
END
$$;

DO $$
DECLARE
    batch1_id uuid := '11111111-1111-1111-1111-111111111111'::uuid;
    batch2_id uuid := '22222222-2222-2222-2222-222222222222'::uuid;
    batch3_id uuid := '33333333-3333-3333-3333-333333333333'::uuid;
BEGIN
    IF EXISTS (
        SELECT 1
        FROM stg.load_batches
        WHERE batch_id = batch1_id
    ) THEN
        RAISE NOTICE 'Baseline verification batches already exist in %', current_database();
        RETURN;
    END IF;

    -- =========================================================================
    -- BATCH 1: Базовое состояние 3 репозиториев и 8 issues/PR
    -- =========================================================================
    INSERT INTO stg.load_batches (
        batch_id, dag_id, run_id, status, started_at, finished_at, expected_repository_count
    ) VALUES (
        batch1_id,
        'github_to_stg',
        'manual__2026-10-18T10:00:00',
        'success',
        '2026-10-18 10:00:00+00',
        '2026-10-18 10:05:00+00',
        3
    );

    INSERT INTO stg.repository_loads (
        batch_id, repository_full_name, status, started_at, finished_at,
        repository_record_count, issue_record_count, issue_page_count
    ) VALUES
    (batch1_id, 'arkivanov/Decompose', 'success', '2026-10-18 10:00:00+00', '2026-10-18 10:05:00+00', 1, 4, 1),
    (batch1_id, 'arkivanov/MVIKotlin', 'success', '2026-10-18 10:00:00+00', '2026-10-18 10:05:00+00', 1, 2, 1),
    (batch1_id, 'arkivanov/Essenty',   'success', '2026-10-18 10:00:00+00', '2026-10-18 10:05:00+00', 1, 2, 1);

    INSERT INTO stg.github_repositories_raw (
        batch_id, repository_full_name, payload, source_url, http_status
    ) VALUES
    (
        batch1_id,
        'arkivanov/Decompose',
        '{
            "id": 298403335,
            "full_name": "arkivanov/Decompose",
            "description": "Kotlin Multiplatform library for breaking down your code into tree-structured lifecycle-aware business logic components",
            "language": "Kotlin",
            "stargazers_count": 3450,
            "forks_count": 210,
            "open_issues_count": 15,
            "archived": false,
            "created_at": "2020-09-24T18:30:00Z",
            "updated_at": "2026-10-18T09:00:00Z",
            "has_issues": true
        }'::jsonb,
        'https://api.github.com/repos/arkivanov/Decompose',
        200
    ),
    (
        batch1_id,
        'arkivanov/MVIKotlin',
        '{
            "id": 239088481,
            "full_name": "arkivanov/MVIKotlin",
            "description": "Kotlin Multiplatform MVI framework",
            "language": "Kotlin",
            "stargazers_count": 1850,
            "forks_count": 120,
            "open_issues_count": 8,
            "archived": false,
            "created_at": "2020-02-07T12:00:00Z",
            "updated_at": "2026-10-18T09:00:00Z",
            "has_issues": true
        }'::jsonb,
        'https://api.github.com/repos/arkivanov/MVIKotlin',
        200
    ),
    (
        batch1_id,
        'arkivanov/Essenty',
        '{
            "id": 423984021,
            "full_name": "arkivanov/Essenty",
            "description": "Essential Kotlin Multiplatform libraries: Lifecycle, StateKeeper, InstanceKeeper, BackHandler",
            "language": "Kotlin",
            "stargazers_count": 920,
            "forks_count": 45,
            "open_issues_count": 4,
            "archived": false,
            "created_at": "2021-11-02T15:00:00Z",
            "updated_at": "2026-10-18T09:00:00Z",
            "has_issues": true
        }'::jsonb,
        'https://api.github.com/repos/arkivanov/Essenty',
        200
    );

    INSERT INTO stg.github_issues_raw (
        batch_id, repository_full_name, github_issue_id, payload, source_url, http_status
    ) VALUES
    (
        batch1_id, 'arkivanov/Decompose', 501,
        '{
            "id": 501, "number": 1, "title": "Navigation backstack animation glitch on iOS",
            "state": "closed", "user": {"id": 101, "login": "arkivanov"},
            "created_at": "2026-02-01T10:00:00Z", "updated_at": "2026-02-03T18:00:00Z", "closed_at": "2026-02-03T18:00:00Z",
            "labels": [{"id": 10, "name": "bug"}, {"id": 20, "name": "ios"}],
            "assignees": [{"id": 101, "login": "arkivanov"}]
        }'::jsonb,
        'https://api.github.com/repos/arkivanov/Decompose/issues/1', 200
    ),
    (
        batch1_id, 'arkivanov/Decompose', 502,
        '{
            "id": 502, "number": 2, "title": "Support Compose Multiplatform 1.8",
            "state": "closed", "user": {"id": 102, "login": "alex_kmp"},
            "created_at": "2026-02-05T12:00:00Z", "updated_at": "2026-02-06T12:00:00Z", "closed_at": "2026-02-06T12:00:00Z",
            "labels": [{"id": 30, "name": "enhancement"}],
            "assignees": [{"id": 101, "login": "arkivanov"}],
            "pull_request": {"url": "https://api.github.com/repos/arkivanov/Decompose/pulls/2"}
        }'::jsonb,
        'https://api.github.com/repos/arkivanov/Decompose/issues/2', 200
    ),
    (
        batch1_id, 'arkivanov/Decompose', 503,
        '{
            "id": 503, "number": 3, "title": "Add retainInstance documentation for JVM desktop",
            "state": "open", "user": {"id": 103, "login": "elena_dev"},
            "created_at": "2026-03-01T14:00:00Z", "updated_at": "2026-03-01T14:00:00Z", "closed_at": null,
            "labels": [{"id": 40, "name": "documentation"}],
            "assignees": []
        }'::jsonb,
        'https://api.github.com/repos/arkivanov/Decompose/issues/3', 200
    ),
    (
        batch1_id, 'arkivanov/Decompose', 504,
        '{
            "id": 504, "number": 4, "title": "Fix memory leak in ChildStack router",
            "state": "open", "user": {"id": 104, "login": "john_doe"},
            "created_at": "2026-03-10T09:00:00Z", "updated_at": "2026-03-10T09:00:00Z", "closed_at": null,
            "labels": [{"id": 10, "name": "bug"}],
            "assignees": [{"id": 101, "login": "arkivanov"}]
        }'::jsonb,
        'https://api.github.com/repos/arkivanov/Decompose/issues/4', 200
    ),
    (
        batch1_id, 'arkivanov/MVIKotlin', 601,
        '{
            "id": 601, "number": 10, "title": "Coroutines executor thread safety issue",
            "state": "closed", "user": {"id": 101, "login": "arkivanov"},
            "created_at": "2026-02-10T11:00:00Z", "updated_at": "2026-02-12T15:00:00Z", "closed_at": "2026-02-12T15:00:00Z",
            "labels": [{"id": 10, "name": "bug"}],
            "assignees": [{"id": 101, "login": "arkivanov"}]
        }'::jsonb,
        'https://api.github.com/repos/arkivanov/MVIKotlin/issues/10', 200
    ),
    (
        batch1_id, 'arkivanov/MVIKotlin', 602,
        '{
            "id": 602, "number": 11, "title": "Add TimeTravelServer sample for Android",
            "state": "open", "user": {"id": 105, "login": "sergey_p"},
            "created_at": "2026-03-05T16:00:00Z", "updated_at": "2026-03-05T16:00:00Z", "closed_at": null,
            "labels": [{"id": 30, "name": "enhancement"}],
            "assignees": [],
            "pull_request": {"url": "https://api.github.com/repos/arkivanov/MVIKotlin/pulls/11"}
        }'::jsonb,
        'https://api.github.com/repos/arkivanov/MVIKotlin/issues/11', 200
    ),
    (
        batch1_id, 'arkivanov/Essenty', 701,
        '{
            "id": 701, "number": 20, "title": "Lifecycle owner hierarchy validation",
            "state": "closed", "user": {"id": 101, "login": "arkivanov"},
            "created_at": "2026-01-15T10:00:00Z", "updated_at": "2026-01-16T10:00:00Z", "closed_at": "2026-01-16T10:00:00Z",
            "labels": [{"id": 50, "name": "lifecycle"}],
            "assignees": [{"id": 101, "login": "arkivanov"}]
        }'::jsonb,
        'https://api.github.com/repos/arkivanov/Essenty/issues/20', 200
    ),
    (
        batch1_id, 'arkivanov/Essenty', 702,
        '{
            "id": 702, "number": 21, "title": "BackHandler predictive back gesture support",
            "state": "open", "user": {"id": 106, "login": "maria_k"},
            "created_at": "2026-03-12T13:00:00Z", "updated_at": "2026-03-12T13:00:00Z", "closed_at": null,
            "labels": [{"id": 30, "name": "enhancement"}],
            "assignees": []
        }'::jsonb,
        'https://api.github.com/repos/arkivanov/Essenty/issues/21', 200
    );

    -- =========================================================================
    -- BATCH 2: Идентичное состояние (проверка идемпотентности SCD2 в DDS)
    -- =========================================================================
    INSERT INTO stg.load_batches (
        batch_id, dag_id, run_id, status, started_at, finished_at, expected_repository_count
    ) VALUES (
        batch2_id,
        'github_to_stg',
        'manual__2026-10-19T10:00:00',
        'success',
        '2026-10-19 10:00:00+00',
        '2026-10-19 10:05:00+00',
        3
    );

    INSERT INTO stg.repository_loads (
        batch_id, repository_full_name, status, started_at, finished_at,
        repository_record_count, issue_record_count, issue_page_count
    )
    SELECT
        batch2_id,
        repository_full_name,
        status,
        '2026-10-19 10:00:00+00',
        '2026-10-19 10:05:00+00',
        repository_record_count,
        issue_record_count,
        issue_page_count
    FROM stg.repository_loads
    WHERE batch_id = batch1_id;

    INSERT INTO stg.github_repositories_raw (
        batch_id, repository_full_name, payload, source_url, http_status
    )
    SELECT
        batch2_id,
        repository_full_name,
        payload,
        source_url,
        http_status
    FROM stg.github_repositories_raw
    WHERE batch_id = batch1_id;

    INSERT INTO stg.github_issues_raw (
        batch_id, repository_full_name, github_issue_id, payload, source_url, http_status
    )
    SELECT
        batch2_id,
        repository_full_name,
        github_issue_id,
        payload,
        source_url,
        http_status
    FROM stg.github_issues_raw
    WHERE batch_id = batch1_id;

    -- =========================================================================
    -- BATCH 3: SCD2 изменения в Decompose:
    --   - Звезды: 3450 -> 3485 (+35)
    --   - Форки: 210 -> 215 (+5)
    --   - Issue 504 закрыт (2026-10-20T08:00:00Z)
    --   - Новый PR 505 (Wasm targets support)
    -- =========================================================================
    INSERT INTO stg.load_batches (
        batch_id, dag_id, run_id, status, started_at, finished_at, expected_repository_count
    ) VALUES (
        batch3_id,
        'github_to_stg',
        'manual__2026-10-20T10:00:00',
        'success',
        '2026-10-20 10:00:00+00',
        '2026-10-20 10:05:00+00',
        3
    );

    INSERT INTO stg.repository_loads (
        batch_id, repository_full_name, status, started_at, finished_at,
        repository_record_count, issue_record_count, issue_page_count
    ) VALUES
    (batch3_id, 'arkivanov/Decompose', 'success', '2026-10-20 10:00:00+00', '2026-10-20 10:05:00+00', 1, 5, 1),
    (batch3_id, 'arkivanov/MVIKotlin', 'success', '2026-10-20 10:00:00+00', '2026-10-20 10:05:00+00', 1, 2, 1),
    (batch3_id, 'arkivanov/Essenty',   'success', '2026-10-20 10:00:00+00', '2026-10-20 10:05:00+00', 1, 2, 1);

    INSERT INTO stg.github_repositories_raw (
        batch_id, repository_full_name, payload, source_url, http_status
    )
    SELECT
        batch3_id,
        repository_full_name,
        CASE
            WHEN repository_full_name = 'arkivanov/Decompose' THEN
                payload
                || jsonb_build_object(
                    'stargazers_count', 3485,
                    'forks_count', 215,
                    'open_issues_count', 14,
                    'updated_at', '2026-10-20T09:30:00Z'
                )
            ELSE payload
        END,
        source_url,
        http_status
    FROM stg.github_repositories_raw
    WHERE batch_id = batch1_id;

    INSERT INTO stg.github_issues_raw (
        batch_id, repository_full_name, github_issue_id, payload, source_url, http_status
    )
    SELECT
        batch3_id,
        repository_full_name,
        github_issue_id,
        CASE
            WHEN repository_full_name = 'arkivanov/Decompose' AND github_issue_id = 504 THEN
                payload
                || jsonb_build_object(
                    'state', 'closed',
                    'closed_at', '2026-10-20T08:00:00Z',
                    'updated_at', '2026-10-20T08:00:00Z'
                )
            ELSE payload
        END,
        source_url,
        http_status
    FROM stg.github_issues_raw
    WHERE batch_id = batch1_id;

    -- Добавляем новый PR 505 в Batch 3
    INSERT INTO stg.github_issues_raw (
        batch_id, repository_full_name, github_issue_id, payload, source_url, http_status
    ) VALUES (
        batch3_id,
        'arkivanov/Decompose',
        505,
        '{
            "id": 505, "number": 5, "title": "Add WebAssembly (Wasm) targets support",
            "state": "open", "user": {"id": 107, "login": "wasm_guru"},
            "created_at": "2026-10-20T09:00:00Z", "updated_at": "2026-10-20T09:00:00Z", "closed_at": null,
            "labels": [{"id": 30, "name": "enhancement"}, {"id": 60, "name": "wasm"}],
            "assignees": [{"id": 101, "login": "arkivanov"}],
            "pull_request": {"url": "https://api.github.com/repos/arkivanov/Decompose/pulls/5"}
        }'::jsonb,
        'https://api.github.com/repos/arkivanov/Decompose/issues/5',
        200
    );

    IF (SELECT count(*) FROM stg.load_batches WHERE batch_id IN (batch1_id, batch2_id, batch3_id)) <> 3 THEN
        RAISE EXCEPTION 'CDM reconciliation fixture: expected 3 batches';
    END IF;
END
$$;

COMMIT;
