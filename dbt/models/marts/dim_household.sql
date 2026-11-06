{{ config(materialized='view') }}

WITH transaction_households AS (

    SELECT DISTINCT
        household_key
    FROM {{ ref('stg_transactions') }}

)

SELECT
    h.household_key,
    d.age_group,
    d.marital_status_code,
    d.income_group,
    d.homeowner_status,
    d.household_composition,
    d.household_size_group,
    d.kids_category,
    (d.household_key IS NOT NULL) AS has_demographics

FROM transaction_households AS h

LEFT JOIN {{ ref('stg_hh_demographic') }} AS d
    ON h.household_key = d.household_key