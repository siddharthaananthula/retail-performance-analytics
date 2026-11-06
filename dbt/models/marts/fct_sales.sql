{{ config(materialized='view') }}

SELECT
    household_key,
    basket_id,
    transaction_day,
    product_id,
    quantity,
    sales_value,
    store_id,
    retail_discount,
    transaction_time,
    week_no,
    coupon_discount,
    coupon_match_discount,
    is_zero_qty_positive_sale,
    is_high_quantity
FROM {{ ref('stg_transactions') }}