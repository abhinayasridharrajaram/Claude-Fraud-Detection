-- 10_fraud_by_day.sql
-- Transaction count, fraud count, and fraud rate by day (0 or 1)
SELECT
    CAST(FLOOR(Time / 86400) AS INTEGER) AS day,
    COUNT(*)                              AS n_transactions,
    SUM(Class)                            AS n_fraud,
    ROUND(SUM(Class) * 100.0 / COUNT(*), 4) AS fraud_rate_pct
FROM 'data/creditcard.csv'
GROUP BY day
ORDER BY day;
