BEGIN;

DO $$
DECLARE
    source_id uuid := '00000000-0000-4000-8000-000000000003';
    target_id uuid := '00000000-0000-4000-8000-000000000004';

    batch_row stg.load_batches%ROWTYPE;
    load_row stg.repository_loads%ROWTYPE;
    repo_row stg.github_repositories_raw%ROWTYPE;
    issue_row stg.github_issues_raw%ROWTYPE;

    changed_repositories integer := 0;
    changed_issues integer := 0;
BEGIN
    IF current_database() <> 'ppad_dds_test' THEN
        RAISE EXCEPTION 'Run only in ppad_dds_test';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM dds.processed_batches
        WHERE batch_id = source_id
    ) THEN
        RAISE EXCEPTION 'Third batch must already be processed';
    END IF;

    SELECT *
    INTO STRICT batch_row
    FROM stg.load_batches
    WHERE batch_id = source_id;

    batch_row.batch_id := target_id;
    batch_row.run_id := 'dds_test_rollback_01';
    batch_row.started_at := batch_row.started_at + interval '1 hour';
    batch_row.finished_at := batch_row.finished_at + interval '1 hour';

    INSERT INTO stg.load_batches SELECT batch_row.*;

    FOR load_row IN
        SELECT *
        FROM stg.repository_loads
        WHERE batch_id = source_id
    LOOP
        load_row.batch_id := target_id;
        load_row.started_at := load_row.started_at + interval '1 hour';
        load_row.finished_at := load_row.finished_at + interval '1 hour';

        INSERT INTO stg.repository_loads SELECT load_row.*;
    END LOOP;

    FOR repo_row IN
        SELECT *
        FROM stg.github_repositories_raw
        WHERE batch_id = source_id
    LOOP
        repo_row.batch_id := target_id;
        repo_row.loaded_at := clock_timestamp();

        IF repo_row.repository_full_name = 'arkivanov/Decompose' THEN
            repo_row.payload := jsonb_set(
                repo_row.payload,
                '{description}',
                to_jsonb(
                    (repo_row.payload ->> 'description')
                    || ' [ROLLBACK TEST]'
                )
            );
            changed_repositories := changed_repositories + 1;
        END IF;

        INSERT INTO stg.github_repositories_raw SELECT repo_row.*;
    END LOOP;

    FOR issue_row IN
        SELECT *
        FROM stg.github_issues_raw
        WHERE batch_id = source_id
    LOOP
        issue_row.batch_id := target_id;
        issue_row.loaded_at := clock_timestamp();

        IF issue_row.github_issue_id = 1079462603 THEN
            issue_row.payload := jsonb_set(
                issue_row.payload,
                '{title}',
                to_jsonb(
                    (issue_row.payload ->> 'title')
                    || ' [ROLLBACK TEST]'
                )
            );
            changed_issues := changed_issues + 1;
        END IF;

        INSERT INTO stg.github_issues_raw SELECT issue_row.*;
    END LOOP;

    IF changed_repositories <> 1 OR changed_issues <> 1 THEN
        RAISE EXCEPTION 'Unexpected number of changed test objects';
    END IF;
END
$$;

CREATE FUNCTION dds.test_reject_processed_batch()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.batch_id = '00000000-0000-4000-8000-000000000004'::uuid THEN
        RAISE EXCEPTION 'DDS_TEST_FORCED_FAILURE';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER test_reject_processed_batch
BEFORE INSERT ON dds.processed_batches
FOR EACH ROW
EXECUTE FUNCTION dds.test_reject_processed_batch();

COMMIT;
