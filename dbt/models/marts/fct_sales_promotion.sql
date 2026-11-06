{{ config(materialized='table') }}

-- Product/store/week is unique in fct_promotion_week, so this preserves line grain.
SELECT
    s.*,
    (p.product_id IS NOT NULL) AS has_promotion_record,
    COALESCE(p.has_display, FALSE) AS has_display,
    COALESCE(p.has_mailer, FALSE) AS has_mailer,
    COALESCE(p.display_state_count > 1 OR p.mailer_state_count > 1, FALSE)
        AS has_conflicting_promotion_states
FROM {{ ref('fct_sales') }} AS s
LEFT JOIN {{ ref('fct_promotion_week') }} AS p
    ON s.product_id = p.product_id
    AND s.store_id = p.store_id
    AND s.week_no = p.week_no
