{{ config(materialized='view') }}

-- A coupon may cover many products and may occur in more than one campaign.
SELECT coupon_upc, product_id, campaign_id
FROM {{ ref('stg_coupon') }}
