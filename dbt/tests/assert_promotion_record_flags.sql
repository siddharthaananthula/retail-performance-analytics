SELECT basket_id, product_id
FROM {{ ref('fct_sales_promotion') }}
WHERE has_promotion_record IS NULL
   OR has_display IS NULL
   OR has_mailer IS NULL
   OR has_conflicting_promotion_states IS NULL
   OR (
       NOT has_promotion_record
       AND (has_display OR has_mailer OR has_conflicting_promotion_states)
   )
