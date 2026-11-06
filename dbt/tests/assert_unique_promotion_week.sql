SELECT product_id, store_id, week_no
FROM {{ ref('fct_promotion_week') }}
GROUP BY 1, 2, 3
HAVING COUNT(*) > 1
