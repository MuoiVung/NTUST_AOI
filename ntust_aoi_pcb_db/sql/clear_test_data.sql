-- CLEAR ALL BUSINESS DATA (Leaves system_configs untouched)
TRUNCATE TABLE images CASCADE;
TRUNCATE TABLE runs CASCADE;
TRUNCATE TABLE board_numbers CASCADE;
TRUNCATE TABLE orders CASCADE;

-- Optional: Restart sequences if any (though we use VARCHAR PKs mostly)
-- ALTER SEQUENCE runs_id_seq RESTART WITH 1;
