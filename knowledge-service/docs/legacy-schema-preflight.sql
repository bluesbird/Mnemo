DO $preflight$
DECLARE
    target_schema name := current_schema();
    expected_columns integer;
    constraint_mismatches integer;
BEGIN
    IF target_schema IS NULL THEN
        RAISE EXCEPTION 'No current schema; select the Knowledge service schema before running this check';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_class relation
        JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace
        WHERE namespace.nspname = target_schema
          AND relation.relkind IN ('r', 'p')
          AND relation.relname NOT IN ('note', 'tag', 'note_tags')
    ) OR (
        SELECT count(*)
        FROM pg_class relation
        JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace
        WHERE namespace.nspname = target_schema
          AND relation.relkind IN ('r', 'p')
    ) <> 3 THEN
        RAISE EXCEPTION 'Expected only note, tag, and note_tags tables in schema %, found a different table set',
            target_schema;
    END IF;

    WITH expected(table_name, column_name, data_type, is_nullable, char_length, is_identity) AS (
        VALUES
            ('note', 'id', 'bigint', 'NO', NULL::integer, 'YES'),
            ('note', 'title', 'character varying', 'YES', 255, 'NO'),
            ('note', 'content', 'text', 'YES', NULL::integer, 'NO'),
            ('note', 'summary', 'text', 'YES', NULL::integer, 'NO'),
            ('note', 'source_hash', 'character varying', 'NO', 64, 'NO'),
            ('note', 'created_at', 'timestamp without time zone', 'YES', NULL::integer, 'NO'),
            ('note', 'updated_at', 'timestamp without time zone', 'YES', NULL::integer, 'NO'),
            ('tag', 'id', 'bigint', 'NO', NULL::integer, 'YES'),
            ('tag', 'name', 'character varying', 'NO', 255, 'NO'),
            ('note_tags', 'note_id', 'bigint', 'NO', NULL::integer, 'NO'),
            ('note_tags', 'tag_id', 'bigint', 'NO', NULL::integer, 'NO')
    ), mismatches AS (
        SELECT expected.*
        FROM expected
        LEFT JOIN information_schema.columns actual
          ON actual.table_schema = target_schema
         AND actual.table_name = expected.table_name
         AND actual.column_name = expected.column_name
        WHERE actual.column_name IS NULL
           OR actual.data_type <> expected.data_type
           OR actual.is_nullable <> expected.is_nullable
           OR actual.character_maximum_length IS DISTINCT FROM expected.char_length
           OR actual.is_identity <> expected.is_identity
    )
    SELECT count(*) INTO expected_columns FROM mismatches;

    IF expected_columns <> 0 OR (
        SELECT count(*)
        FROM information_schema.columns
        WHERE table_schema = target_schema
          AND table_name IN ('note', 'tag', 'note_tags')
    ) <> 11 THEN
        RAISE EXCEPTION 'Knowledge service columns do not match the V1 schema in schema %', target_schema;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = target_schema
          AND table_name = 'note'
          AND column_name = 'source_hash'
          AND column_default ~ $pattern$^''(::character varying(\([0-9]+\))?)?$pattern$
    ) THEN
        RAISE EXCEPTION 'note.source_hash must retain its empty-string default in schema %', target_schema;
    END IF;

    WITH expected(table_name, constraint_type, definition) AS (
        VALUES
            ('note', 'p', 'PRIMARY KEY (id)'),
            ('tag', 'p', 'PRIMARY KEY (id)'),
            ('tag', 'u', 'UNIQUE (name)'),
            ('note_tags', 'p', 'PRIMARY KEY (note_id, tag_id)'),
            ('note_tags', 'f', 'FOREIGN KEY (note_id) REFERENCES note(id)'),
            ('note_tags', 'f', 'FOREIGN KEY (tag_id) REFERENCES tag(id)')
    ), actual(table_name, constraint_type, definition) AS (
        SELECT relation.relname, constraint_row.contype::text,
               pg_get_constraintdef(constraint_row.oid, true)
        FROM pg_constraint constraint_row
        JOIN pg_class relation ON relation.oid = constraint_row.conrelid
        JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace
        WHERE namespace.nspname = target_schema
          AND constraint_row.contype IN ('p', 'u', 'f')
    ), differences AS (
        SELECT expected.* FROM expected
        WHERE NOT EXISTS (
            SELECT 1 FROM actual
            WHERE actual.table_name = expected.table_name
              AND actual.constraint_type = expected.constraint_type
              AND actual.definition = expected.definition
        )
        UNION ALL
        SELECT actual.* FROM actual
        WHERE NOT EXISTS (
            SELECT 1 FROM expected
            WHERE expected.table_name = actual.table_name
              AND expected.constraint_type = actual.constraint_type
              AND expected.definition = actual.definition
        )
    )
    SELECT count(*) INTO constraint_mismatches FROM differences;

    IF constraint_mismatches <> 0 THEN
        RAISE EXCEPTION 'Knowledge service primary, unique, or foreign-key constraints do not match V1 in schema %',
            target_schema;
    END IF;

    RAISE NOTICE 'Knowledge service legacy schema in % matches the expected Flyway V1 column and constraint shape',
        target_schema;
END
$preflight$;
