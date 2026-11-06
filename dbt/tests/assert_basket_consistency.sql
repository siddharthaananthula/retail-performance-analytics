SELECT
    basket_id,
    COUNT(DISTINCT household_key) AS household_count,
    COUNT(DISTINCT transaction_day) AS day_count,
    COUNT(DISTINCT store_id) AS store_count
FROM {{ ref('stg_transactions') }}
GROUP BY basket_id
HAVING
    COUNT(DISTINCT household_key) > 1
    OR COUNT(DISTINCT transaction_day) > 1
    OR COUNT(DISTINCT store_id) > 1