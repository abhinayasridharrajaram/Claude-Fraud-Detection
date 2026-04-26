-- 08_correlations.sql
-- Pearson correlation of V1..V28 and Amount with Class
-- Sorted by absolute correlation descending
SELECT feature, ROUND(corr_with_class, 6) AS corr_with_class,
       ROUND(ABS(corr_with_class), 6) AS abs_corr
FROM (
    SELECT 'V1'     AS feature, CORR(V1,     Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V2'     AS feature, CORR(V2,     Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V3'     AS feature, CORR(V3,     Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V4'     AS feature, CORR(V4,     Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V5'     AS feature, CORR(V5,     Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V6'     AS feature, CORR(V6,     Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V7'     AS feature, CORR(V7,     Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V8'     AS feature, CORR(V8,     Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V9'     AS feature, CORR(V9,     Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V10'    AS feature, CORR(V10,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V11'    AS feature, CORR(V11,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V12'    AS feature, CORR(V12,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V13'    AS feature, CORR(V13,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V14'    AS feature, CORR(V14,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V15'    AS feature, CORR(V15,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V16'    AS feature, CORR(V16,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V17'    AS feature, CORR(V17,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V18'    AS feature, CORR(V18,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V19'    AS feature, CORR(V19,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V20'    AS feature, CORR(V20,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V21'    AS feature, CORR(V21,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V22'    AS feature, CORR(V22,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V23'    AS feature, CORR(V23,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V24'    AS feature, CORR(V24,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V25'    AS feature, CORR(V25,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V26'    AS feature, CORR(V26,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V27'    AS feature, CORR(V27,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V28'    AS feature, CORR(V28,    Class) AS corr_with_class FROM 'data/creditcard.csv' UNION ALL
    SELECT 'Amount' AS feature, CORR(Amount, Class) AS corr_with_class FROM 'data/creditcard.csv'
) t
ORDER BY abs_corr DESC;
