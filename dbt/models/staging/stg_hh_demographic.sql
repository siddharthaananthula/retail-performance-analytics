{{ config(materialized='view') }}

SELECT
    household_key,
    TRIM(age_desc) AS age_group,
    TRIM(marital_status_code) AS marital_status_code,
    TRIM(income_desc) AS income_group,
    TRIM(homeowner_desc) AS homeowner_status,
    TRIM(hh_comp_desc) AS household_composition,
    TRIM(household_size_desc) AS household_size_group,
    TRIM(kid_category_desc) AS kids_category
FROM {{ source('retail_raw', 'hh_demographic') }}