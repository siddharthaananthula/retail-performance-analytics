{{ config(materialized='view') }}

SELECT
    household_key,
    day AS redemption_day,
    coupon_upc,
    campaign AS campaign_id
FROM {{ source('retail_raw', 'coupon_redempt') }}