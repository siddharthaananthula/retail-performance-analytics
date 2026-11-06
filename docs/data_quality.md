# Data quality and validation

## Verified local dbt run

The ignored local `dbt/target/run_results.json` artefact records **73 tests passed, zero failed**, generated on 2 November 2026 at 05:52 UTC. The source, staging, sales and basket reconciliation documented during Phase 2 reported 2,595,732 transaction lines, 276,484 baskets, 2,500 purchasing households and $8,057,463.08 sales. The coupon redemption source and fact both had 2,318 records. These are historical local validation results, not a new dbt run for this documentation update.

A later read-only source-file check independently confirmed 2,595,732 transaction lines, 276,484 baskets, 2,500 purchasing households, 2,318 raw coupon-redemption records and $8,057,463.08 in sales rounded to cents. Read-only PostgreSQL checks confirmed 36,771,279 product-store-week promotion aggregates, 15,245 conflicting keys, 563,774 sales lines with a matching promotion record and 2,031,958 without one. This checked selected baselines, not a complete rebuild or fresh full-suite test. Some source sales strings carry precision beyond cents; monetary results here are rounded to two decimal places.

The tests cover uniqueness, non-null keys, dimension relationships, campaign dates, redemption eligibility and targeting, basket consistency, basket-to-line sales parity, promotion-record flags and sales-promotion line integrity. In particular, `assert_sales_promotion_row_integrity.sql` checks original line fields after the promotion join, while `assert_sales_promotion_parity.sql` checks aggregate lines and sales. See [dbt/tests](../dbt/tests/) and [model declarations](../dbt/models/marts/_marts.yml).

## Reporting limitations

| Finding | Evidence | Reporting treatment |
|---|---|---|
| Demographic coverage | 801 of 2,500 purchasing households, or 32.04%. | Label demographic charts as a subset; do not generalise them to all households. |
| Missing promotion matches | 2,031,958 of 2,595,732 transaction lines have no matching product-store-week record. Coverage is 563,774 lines, about 21.7%. | Call unmatched status **unknown**, not “no promotion”. |
| Conflicting promotion states | 15,245 product-store-week keys have multiple source states; 858 matched sales lines carry a conflict flag. | Retain conflict evidence; do not choose an arbitrary code. |
| Undocumented promotion codes | Display and mailer code meanings lack a verified codebook. | A nonzero code is observed activity, not verified customer exposure or causal uplift. |
| Quantity encoding | Total recorded quantity is 260,685,622; 257,331,979 units are associated with `GASOLINE-REG UNLEADED`. | Do not use an unrestricted “Units Sold” KPI. Fuel quantity encoding is unverified. |
| Relative periods | 711 observed days and 102 source weeks; the first and last weeks are partial. | Use relative-day and week labels, not invented calendar dates or weekday claims. |
| Store identity | 582 observed store IDs without verified physical locations. | Show IDs only; do not assign names or regions. |
| Product attributes | 15 products have blank classification fields; 30,607 have no recorded product size. | Keep missing values visible rather than guessing categories or sizes. |
| Zero quantity with sales | 67 positive-sales lines have zero recorded quantity. | Retain and flag them; do not invent units. |

The data-quality table distinguishes **recorded facts** from **interpretation**. For example, the 21.7% promotion-record coverage is a measurable join result, while “promotion exposure” would require validated code definitions and a customer-level exposure method. Differences in sales during promotional periods do not establish incremental lift.

## Checks before future releases

Re-run the full-dataset dbt suite after changing raw data or model SQL. Reconcile source, staging and reporting line counts and sales, and review the Power BI totals after refresh. The loader passed isolated synthetic integration checks; the CI workflow now implements those checks but has not yet run on GitHub. Neither result establishes a fresh rebuild of the original dataset. No raw data was reloaded for this documentation update. [Data source and reproduction](data_source.md) lists the required files and unresolved redistribution decision.
