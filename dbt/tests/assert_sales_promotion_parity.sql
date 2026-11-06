WITH baseline AS (
    SELECT COUNT(*) AS line_count, SUM(sales_value) AS sales_value
    FROM {{ ref('fct_sales') }}
), promoted AS (
    SELECT COUNT(*) AS line_count, SUM(sales_value) AS sales_value
    FROM {{ ref('fct_sales_promotion') }}
)
SELECT baseline.*, promoted.line_count AS promoted_line_count,
       promoted.sales_value AS promoted_sales_value
FROM baseline CROSS JOIN promoted
WHERE baseline.line_count <> promoted.line_count
   OR baseline.sales_value IS DISTINCT FROM promoted.sales_value
