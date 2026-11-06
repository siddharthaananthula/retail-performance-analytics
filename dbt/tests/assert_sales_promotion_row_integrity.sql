-- Check each original line, not just grand totals.
SELECT s.basket_id, s.product_id
FROM {{ ref('fct_sales') }} AS s
LEFT JOIN {{ ref('fct_sales_promotion') }} AS p
    ON s.basket_id = p.basket_id AND s.product_id = p.product_id
WHERE p.basket_id IS NULL
   OR ROW(
       s.household_key, s.transaction_day, s.quantity, s.sales_value,
       s.store_id, s.retail_discount, s.transaction_time, s.week_no,
       s.coupon_discount, s.coupon_match_discount,
       s.is_zero_qty_positive_sale, s.is_high_quantity
   ) IS DISTINCT FROM ROW(
       p.household_key, p.transaction_day, p.quantity, p.sales_value,
       p.store_id, p.retail_discount, p.transaction_time, p.week_no,
       p.coupon_discount, p.coupon_match_discount,
       p.is_zero_qty_positive_sale, p.is_high_quantity
   )
