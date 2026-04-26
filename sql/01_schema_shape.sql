-- Query 01: Schema & shape
-- Returns column names, types, row count, and estimated disk size
SELECT
    column_name,
    data_type,
    (SELECT COUNT(*) FROM 'data/creditcard.csv') AS row_count
FROM information_schema.columns
WHERE table_name = 'creditcard'
ORDER BY ordinal_position;
