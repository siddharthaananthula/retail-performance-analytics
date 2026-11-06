{{ config(materialized='table') }}

-- Relative reporting days only; the dataset has no verified calendar dates.
WITH observed_days AS (
    SELECT DISTINCT transaction_day, week_no
    FROM {{ ref('stg_transactions') }}
), week_span AS (
    SELECT
        week_no,
        MIN(transaction_day) AS week_start_day,
        MAX(transaction_day) AS week_end_day,
        COUNT(*) AS observed_days_in_week
    FROM observed_days
    GROUP BY week_no
)
SELECT
    d.transaction_day,
    d.week_no,
    ROW_NUMBER() OVER (
        PARTITION BY d.week_no ORDER BY d.transaction_day
    ) AS day_number_in_week,
    w.week_start_day,
    w.week_end_day,
    w.observed_days_in_week,
    (w.observed_days_in_week < 7) AS is_partial_week
FROM observed_days AS d
JOIN week_span AS w USING (week_no)
