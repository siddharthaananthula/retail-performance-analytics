SELECT household_key, redemption_day, coupon_upc, campaign_id
FROM {{ ref('fct_coupon_redemptions') }}
GROUP BY 1, 2, 3, 4
HAVING COUNT(*) > 1
