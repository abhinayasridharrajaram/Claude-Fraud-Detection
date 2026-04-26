-- 04_fraud_by_hour.sql
-- Fraud rate by integer hour_of_day (derived from Time mod 86400)
SELECT
    CAST(FLOOR((Time % 86400) / 3600) AS INTEGER) AS hour_of_day,
    COUNT(*)                                       AS n_transactions,
    SUM(Class)                                     AS n_fraud,
    ROUND(SUM(Class) * 100.0 / COUNT(*), 4)       AS fraud_rate_pct
FROM 'data/creditcard.csv'
GROUP BY hour_of_day
ORDER BY hour_of_day;
