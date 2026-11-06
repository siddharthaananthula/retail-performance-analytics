WITH lines AS (
    SELECT COUNT(DISTINCT basket_id) AS baskets, SUM(sales_value) AS sales
    FROM {{ ref('fct_sales') }}
), baskets AS (
    SELECT COUNT(*) AS baskets, SUM(basket_sales) AS sales
    FROM {{ ref('fct_baskets') }}
)
SELECT lines.*, baskets.baskets AS basket_rows, baskets.sales AS basket_sales
FROM lines CROSS JOIN baskets
WHERE lines.baskets <> baskets.baskets
   OR ABS(lines.sales - baskets.sales) > 0.01
