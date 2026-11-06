SELECT
    coupon_upc,
    product_id,
    campaign_id,
    COUNT(*) AS occurrence_count
FROM {{ ref('stg_coupon') }}
GROUP BY
    coupon_upc,
    product_id,
    campaign_id
HAVING COUNT(*) > 1