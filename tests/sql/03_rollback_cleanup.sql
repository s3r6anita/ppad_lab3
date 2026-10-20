BEGIN;

DO $$
BEGIN
    IF current_database() <> 'ppad_dds_test' THEN
        RAISE EXCEPTION 'Run only in ppad_dds_test';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM dds.processed_batches
        WHERE batch_id = '00000000-0000-4000-8000-000000000004'
    ) THEN
        RAISE EXCEPTION 'Fourth batch was unexpectedly processed';
    END IF;
END
$$;

DROP TRIGGER test_reject_processed_batch
    ON dds.processed_batches;

DROP FUNCTION dds.test_reject_processed_batch();

COMMIT;
