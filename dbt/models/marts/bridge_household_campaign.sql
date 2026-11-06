{{ config(materialized='view') }}

SELECT
    household_key,
    campaign_id
FROM {{ ref('stg_campaign_table') }}