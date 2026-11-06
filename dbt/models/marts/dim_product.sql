{{ config(materialized='view') }}

SELECT
    product_id,
    manufacturer_id,
    department,
    brand,
    commodity,
    sub_commodity,
    product_size
FROM {{ ref('stg_products') }}