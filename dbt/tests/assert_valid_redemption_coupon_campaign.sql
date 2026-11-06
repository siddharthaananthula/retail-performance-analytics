SELECT
    r.household_key,
    r.redemption_day,
    r.coupon_upc,
    r.campaign_id
FROM {{ ref('stg_coupon_redempt') }} AS r
WHERE NOT EXISTS (
    SELECT 1
    FROM {{ ref('stg_coupon') }} AS c
    WHERE c.coupon_upc = r.coupon_upc
      AND c.campaign_id = r.campaign_id
)