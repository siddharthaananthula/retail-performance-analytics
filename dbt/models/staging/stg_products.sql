{{ config(materialized='view') }}

SELECT
    product_id,
    manufacturer AS manufacturer_id,
    NULLIF(TRIM(department), '') AS department,
    NULLIF(TRIM(brand), '') AS brand,
    NULLIF(TRIM(commodity_desc), '') AS commodity,
    NULLIF(TRIM(sub_commodity_desc), '') AS sub_commodity,
    NULLIF(TRIM(curr_size_of_product), '') AS product_size
FROM {{ source('retail_raw', 'product') }}