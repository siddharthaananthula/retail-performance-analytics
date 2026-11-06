{{ config(materialized='view') }}

-- One observed redemption, never expanded through the product mapping.
SELECT household_key, redemption_day, coupon_upc, campaign_id
FROM {{ ref('stg_coupon_redempt') }}
