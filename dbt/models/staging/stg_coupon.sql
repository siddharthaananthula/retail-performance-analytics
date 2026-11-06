{{ config(materialized='view') }}

SELECT DISTINCT
    coupon_upc,
    product_id,
    campaign AS campaign_id
FROM {{ source('retail_raw', 'coupon') }}