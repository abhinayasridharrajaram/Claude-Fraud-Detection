-- 06_zero_amount.sql
-- Count and fraud rate of Amount = 0 transactions
SELECT
    COUNT(*)                                     AS n_zero_amount,
    SUM(Class)                                   AS n_fraud,
    ROUND(SUM(Class) * 100.0 / COUNT(*), 4)     AS fraud_rate_pct
FROM 'data/creditcard.csv'
WHERE Amount = 0;
