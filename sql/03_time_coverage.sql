-- 03_time_coverage.sql
-- Time range, span in hours, and fraud rate by hour_of_day
SELECT
    MIN(Time)                              AS min_time_sec,
    MAX(Time)                              AS max_time_sec,
    ROUND((MAX(Time) - MIN(Time)) / 3600.0, 2) AS span_hours
FROM 'data/creditcard.csv';
