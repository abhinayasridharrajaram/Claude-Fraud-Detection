-- 09_fraud_distributions.sql
-- Per-class mean and stddev for V1..V28, log_amount, hour_of_day
-- Used to compute normalized mean difference (separation score)
SELECT
    Class,
    ROUND(AVG(V1),  6) AS V1_mean,  ROUND(STDDEV(V1),  6) AS V1_std,
    ROUND(AVG(V2),  6) AS V2_mean,  ROUND(STDDEV(V2),  6) AS V2_std,
    ROUND(AVG(V3),  6) AS V3_mean,  ROUND(STDDEV(V3),  6) AS V3_std,
    ROUND(AVG(V4),  6) AS V4_mean,  ROUND(STDDEV(V4),  6) AS V4_std,
    ROUND(AVG(V5),  6) AS V5_mean,  ROUND(STDDEV(V5),  6) AS V5_std,
    ROUND(AVG(V6),  6) AS V6_mean,  ROUND(STDDEV(V6),  6) AS V6_std,
    ROUND(AVG(V7),  6) AS V7_mean,  ROUND(STDDEV(V7),  6) AS V7_std,
    ROUND(AVG(V8),  6) AS V8_mean,  ROUND(STDDEV(V8),  6) AS V8_std,
    ROUND(AVG(V9),  6) AS V9_mean,  ROUND(STDDEV(V9),  6) AS V9_std,
    ROUND(AVG(V10), 6) AS V10_mean, ROUND(STDDEV(V10), 6) AS V10_std,
    ROUND(AVG(V11), 6) AS V11_mean, ROUND(STDDEV(V11), 6) AS V11_std,
    ROUND(AVG(V12), 6) AS V12_mean, ROUND(STDDEV(V12), 6) AS V12_std,
    ROUND(AVG(V13), 6) AS V13_mean, ROUND(STDDEV(V13), 6) AS V13_std,
    ROUND(AVG(V14), 6) AS V14_mean, ROUND(STDDEV(V14), 6) AS V14_std,
    ROUND(AVG(V15), 6) AS V15_mean, ROUND(STDDEV(V15), 6) AS V15_std,
    ROUND(AVG(V16), 6) AS V16_mean, ROUND(STDDEV(V16), 6) AS V16_std,
    ROUND(AVG(V17), 6) AS V17_mean, ROUND(STDDEV(V17), 6) AS V17_std,
    ROUND(AVG(V18), 6) AS V18_mean, ROUND(STDDEV(V18), 6) AS V18_std,
    ROUND(AVG(V19), 6) AS V19_mean, ROUND(STDDEV(V19), 6) AS V19_std,
    ROUND(AVG(V20), 6) AS V20_mean, ROUND(STDDEV(V20), 6) AS V20_std,
    ROUND(AVG(V21), 6) AS V21_mean, ROUND(STDDEV(V21), 6) AS V21_std,
    ROUND(AVG(V22), 6) AS V22_mean, ROUND(STDDEV(V22), 6) AS V22_std,
    ROUND(AVG(V23), 6) AS V23_mean, ROUND(STDDEV(V23), 6) AS V23_std,
    ROUND(AVG(V24), 6) AS V24_mean, ROUND(STDDEV(V24), 6) AS V24_std,
    ROUND(AVG(V25), 6) AS V25_mean, ROUND(STDDEV(V25), 6) AS V25_std,
    ROUND(AVG(V26), 6) AS V26_mean, ROUND(STDDEV(V26), 6) AS V26_std,
    ROUND(AVG(V27), 6) AS V27_mean, ROUND(STDDEV(V27), 6) AS V27_std,
    ROUND(AVG(V28), 6) AS V28_mean, ROUND(STDDEV(V28), 6) AS V28_std,
    ROUND(AVG(LN(1 + Amount)), 6) AS log_amount_mean,
    ROUND(STDDEV(LN(1 + Amount)), 6) AS log_amount_std,
    ROUND(AVG((Time % 86400) / 3600.0), 6) AS hour_of_day_mean,
    ROUND(STDDEV((Time % 86400) / 3600.0), 6) AS hour_of_day_std
FROM 'data/creditcard.csv'
GROUP BY Class
ORDER BY Class;
