{{ config(materialized='table') }}

-- Store identifiers observed in sales; no inferred names or locations.
SELECT DISTINCT store_id
FROM {{ ref('stg_transactions') }}
