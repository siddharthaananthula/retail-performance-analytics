SELECT basket_id, product_id
FROM {{ ref('fct_sales_promotion') }}
GROUP BY basket_id, product_id
HAVING COUNT(*) > 1
