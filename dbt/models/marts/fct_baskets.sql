{{ config(materialized='view') }}

SELECT
    basket_id,
    household_key,
    transaction_day,
    store_id,
    COUNT(*) AS transaction_line_count,
    COUNT(DISTINCT product_id) AS distinct_products,
    SUM(sales_value) AS basket_sales
FROM {{ ref('fct_sales') }}
GROUP BY
    basket_id,
    household_key,
    transaction_day,
    store_id