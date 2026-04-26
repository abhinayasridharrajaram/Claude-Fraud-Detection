-- 02_class_balance.sql
-- Class distribution: counts and percentages
SELECT
    Class,
    COUNT(*)                                          AS n_rows,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 4) AS pct
FROM 'data/creditcard.csv'
GROUP BY Class
ORDER BY Class;
