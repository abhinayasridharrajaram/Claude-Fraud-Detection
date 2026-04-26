-- 07_feature_ranges.sql
-- Min, max, mean, stddev for V1..V28; flag |mean| > 0.1
SELECT feature, min_val, max_val, ROUND(mean_val, 6) AS mean_val, ROUND(std_val, 6) AS std_val,
       CASE WHEN ABS(mean_val) > 0.1 THEN 'FLAG' ELSE 'ok' END AS mean_flag
FROM (
    SELECT 'V1'  AS feature, MIN(V1)  AS min_val, MAX(V1)  AS max_val, AVG(V1)  AS mean_val, STDDEV(V1)  AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V2'  AS feature, MIN(V2)  AS min_val, MAX(V2)  AS max_val, AVG(V2)  AS mean_val, STDDEV(V2)  AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V3'  AS feature, MIN(V3)  AS min_val, MAX(V3)  AS max_val, AVG(V3)  AS mean_val, STDDEV(V3)  AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V4'  AS feature, MIN(V4)  AS min_val, MAX(V4)  AS max_val, AVG(V4)  AS mean_val, STDDEV(V4)  AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V5'  AS feature, MIN(V5)  AS min_val, MAX(V5)  AS max_val, AVG(V5)  AS mean_val, STDDEV(V5)  AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V6'  AS feature, MIN(V6)  AS min_val, MAX(V6)  AS max_val, AVG(V6)  AS mean_val, STDDEV(V6)  AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V7'  AS feature, MIN(V7)  AS min_val, MAX(V7)  AS max_val, AVG(V7)  AS mean_val, STDDEV(V7)  AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V8'  AS feature, MIN(V8)  AS min_val, MAX(V8)  AS max_val, AVG(V8)  AS mean_val, STDDEV(V8)  AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V9'  AS feature, MIN(V9)  AS min_val, MAX(V9)  AS max_val, AVG(V9)  AS mean_val, STDDEV(V9)  AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V10' AS feature, MIN(V10) AS min_val, MAX(V10) AS max_val, AVG(V10) AS mean_val, STDDEV(V10) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V11' AS feature, MIN(V11) AS min_val, MAX(V11) AS max_val, AVG(V11) AS mean_val, STDDEV(V11) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V12' AS feature, MIN(V12) AS min_val, MAX(V12) AS max_val, AVG(V12) AS mean_val, STDDEV(V12) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V13' AS feature, MIN(V13) AS min_val, MAX(V13) AS max_val, AVG(V13) AS mean_val, STDDEV(V13) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V14' AS feature, MIN(V14) AS min_val, MAX(V14) AS max_val, AVG(V14) AS mean_val, STDDEV(V14) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V15' AS feature, MIN(V15) AS min_val, MAX(V15) AS max_val, AVG(V15) AS mean_val, STDDEV(V15) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V16' AS feature, MIN(V16) AS min_val, MAX(V16) AS max_val, AVG(V16) AS mean_val, STDDEV(V16) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V17' AS feature, MIN(V17) AS min_val, MAX(V17) AS max_val, AVG(V17) AS mean_val, STDDEV(V17) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V18' AS feature, MIN(V18) AS min_val, MAX(V18) AS max_val, AVG(V18) AS mean_val, STDDEV(V18) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V19' AS feature, MIN(V19) AS min_val, MAX(V19) AS max_val, AVG(V19) AS mean_val, STDDEV(V19) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V20' AS feature, MIN(V20) AS min_val, MAX(V20) AS max_val, AVG(V20) AS mean_val, STDDEV(V20) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V21' AS feature, MIN(V21) AS min_val, MAX(V21) AS max_val, AVG(V21) AS mean_val, STDDEV(V21) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V22' AS feature, MIN(V22) AS min_val, MAX(V22) AS max_val, AVG(V22) AS mean_val, STDDEV(V22) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V23' AS feature, MIN(V23) AS min_val, MAX(V23) AS max_val, AVG(V23) AS mean_val, STDDEV(V23) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V24' AS feature, MIN(V24) AS min_val, MAX(V24) AS max_val, AVG(V24) AS mean_val, STDDEV(V24) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V25' AS feature, MIN(V25) AS min_val, MAX(V25) AS max_val, AVG(V25) AS mean_val, STDDEV(V25) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V26' AS feature, MIN(V26) AS min_val, MAX(V26) AS max_val, AVG(V26) AS mean_val, STDDEV(V26) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V27' AS feature, MIN(V27) AS min_val, MAX(V27) AS max_val, AVG(V27) AS mean_val, STDDEV(V27) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V28' AS feature, MIN(V28) AS min_val, MAX(V28) AS max_val, AVG(V28) AS mean_val, STDDEV(V28) AS std_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'log_amount' AS feature,
           MIN(LN(1 + Amount)) AS min_val, MAX(LN(1 + Amount)) AS max_val,
           AVG(LN(1 + Amount)) AS mean_val, STDDEV(LN(1 + Amount)) AS std_val
    FROM 'data/creditcard.csv' UNION ALL
    SELECT 'hour_of_day' AS feature,
           MIN((Time % 86400) / 3600.0) AS min_val, MAX((Time % 86400) / 3600.0) AS max_val,
           AVG((Time % 86400) / 3600.0) AS mean_val, STDDEV((Time % 86400) / 3600.0) AS std_val
    FROM 'data/creditcard.csv'
) t
ORDER BY feature;
