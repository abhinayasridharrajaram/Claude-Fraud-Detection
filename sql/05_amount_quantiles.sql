-- 05_amount_quantiles.sql
-- Amount quantiles at 0.01, 0.10, 0.50, 0.90, 0.99, 0.999 split by Class
SELECT
    Class,
    COUNT(*)                                    AS n,
    ROUND(APPROX_QUANTILE(Amount, 0.01),  2)   AS p01,
    ROUND(APPROX_QUANTILE(Amount, 0.10),  2)   AS p10,
    ROUND(APPROX_QUANTILE(Amount, 0.50),  2)   AS p50,
    ROUND(APPROX_QUANTILE(Amount, 0.90),  2)   AS p90,
    ROUND(APPROX_QUANTILE(Amount, 0.99),  2)   AS p99,
    ROUND(APPROX_QUANTILE(Amount, 0.999), 2)   AS p999,
    ROUND(AVG(Amount), 2)                       AS mean_amount,
    ROUND(MAX(Amount), 2)                       AS max_amount
FROM 'data/creditcard.csv'
GROUP BY Class
ORDER BY Class;
