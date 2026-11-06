SELECT
    r.household_key,
    r.redemption_day,
    r.coupon_upc,
    r.campaign_id
FROM {{ ref('stg_coupon_redempt') }} AS r
WHERE NOT EXISTS (
    SELECT 1
    FROM {{ ref('stg_campaign_table') }} AS t
    WHERE t.household_key = r.household_key
      AND t.campaign_id = r.campaign_id
)