SELECT
    campaign_id,
    start_day,
    end_day
FROM {{ ref('stg_campaign_desc') }}
WHERE end_day < start_day