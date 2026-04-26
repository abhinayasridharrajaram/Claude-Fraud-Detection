-- 01_schema.sql
-- Schema: column names, dtypes, row count, approximate disk size
-- DuckDB reads the CSV directly; use DESCRIBE to get column info.
DESCRIBE SELECT * FROM 'data/creditcard.csv' LIMIT 1;
