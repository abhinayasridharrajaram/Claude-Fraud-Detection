-- 01_schema_shape.sql
-- Schema, dtypes, row count via DESCRIBE (works for CSV sources in DuckDB)
DESCRIBE SELECT * FROM 'data/creditcard.csv';
