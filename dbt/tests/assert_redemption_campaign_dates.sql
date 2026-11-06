SELECT r.*
FROM {{ ref('fct_coupon_redemptions') }} AS r
JOIN {{ ref('dim_campaign') }} AS c USING (campaign_id)
WHERE r.redemption_day < c.start_day OR r.redemption_day > c.end_day
