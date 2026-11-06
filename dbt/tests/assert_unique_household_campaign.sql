SELECT
    household_key,
    campaign_id,
    COUNT(*) AS occurrence_count
FROM {{ ref('bridge_household_campaign') }}
GROUP BY
    household_key,
    campaign_id
HAVING COUNT(*) > 1