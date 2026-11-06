WITH source_days AS (
    SELECT DISTINCT transaction_day, week_no
    FROM {{ ref('stg_transactions') }}
), missing_or_changed AS (
    SELECT transaction_day, week_no FROM source_days
    EXCEPT
    SELECT transaction_day, week_no FROM {{ ref('dim_day') }}
), invented AS (
    SELECT transaction_day, week_no FROM {{ ref('dim_day') }}
    EXCEPT
    SELECT transaction_day, week_no FROM source_days
), ambiguous_source_days AS (
    SELECT transaction_day, MIN(week_no) AS week_no
    FROM source_days
    GROUP BY transaction_day
    HAVING COUNT(*) > 1
)
SELECT * FROM missing_or_changed
UNION ALL SELECT * FROM invented
UNION ALL SELECT * FROM ambiguous_source_days
