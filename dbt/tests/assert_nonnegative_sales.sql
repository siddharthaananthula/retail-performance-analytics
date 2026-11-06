SELECT
    household_key,
    basket_id,
    product_id,
    sales_value
FROM {{ ref('stg_transactions') }}
WHERE sales_value < 0