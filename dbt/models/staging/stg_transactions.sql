{{ config(materialized='view') }}

SELECT
    household_key,
    basket_id,
    day AS transaction_day,
    product_id,
    quantity,
    sales_value,
    store_id,
    retail_disc AS retail_discount,
    trans_time AS transaction_time,
    week_no,
    coupon_disc AS coupon_discount,
    coupon_match_disc AS coupon_match_discount,

    (quantity = 0 AND sales_value > 0)
        AS is_zero_qty_positive_sale,

    (quantity > 100)
        AS is_high_quantity

FROM {{ source('retail_raw', 'transaction_data') }}