-- Query 08: Pearson correlation of each feature with Class
-- Includes V1-V28 and Amount; sorted by absolute correlation descending
SELECT feature, ROUND(corr_val, 6) AS corr_with_class, ROUND(ABS(corr_val), 6) AS abs_corr
FROM (
    SELECT 'V1'     AS feature, CORR(V1,     Class) AS corr_val FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V2',     CORR(V2,     Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V3',     CORR(V3,     Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V4',     CORR(V4,     Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V5',     CORR(V5,     Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V6',     CORR(V6,     Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V7',     CORR(V7,     Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V8',     CORR(V8,     Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V9',     CORR(V9,     Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V10',    CORR(V10,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V11',    CORR(V11,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V12',    CORR(V12,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V13',    CORR(V13,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V14',    CORR(V14,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V15',    CORR(V15,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V16',    CORR(V16,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V17',    CORR(V17,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V18',    CORR(V18,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V19',    CORR(V19,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V20',    CORR(V20,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V21',    CORR(V21,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V22',    CORR(V22,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V23',    CORR(V23,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V24',    CORR(V24,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V25',    CORR(V25,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V26',    CORR(V26,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V27',    CORR(V27,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'V28',         CORR(V28,    Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'log_amount',  CORR(LN(1 + Amount), Class) FROM 'data/creditcard.csv' UNION ALL
    SELECT 'hour_of_day', CORR((Time % 86400) / 3600.0, Class) FROM 'data/creditcard.csv'
) t
ORDER BY abs_corr DESC;
