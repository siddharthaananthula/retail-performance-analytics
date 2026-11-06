# Data architecture and local setup

The Complete Journey CSVs have been loaded into PostgreSQL's `raw` schema in the checked local environment. Eight dbt staging views standardise names and remove exact coupon-map duplicates. Twelve analytical models provide dimensions, bridges and facts. Power BI Desktop imports reporting tables from the locally validated `dbt_dev` schema. The loader passed isolated synthetic integration tests; the [CI workflow](../.github/workflows/dbt-quality.yml) implements those checks but has not yet run on GitHub. See [data source and reproduction](data_source.md) for the required CSVs and publication boundary.

## Model flow and grain

```text
Eight CSVs -> PostgreSQL raw -> eight staging views -> 12 analytical models
                                                   -> Power BI Import model -> DAX and seven business pages
```

| Model or group | Grain and role |
|---|---|
| `stg_transactions`, `fct_sales` | One observed basket-product transaction line. |
| `fct_sales_promotion` | The same transaction-line grain, materialised with safe promotion flags for Power BI. |
| `fct_baskets` | One basket; basket sales sum its lines. |
| `dim_product`, `dim_household`, `dim_campaign` | One product, purchasing household or campaign. The household dimension retains households without demographics. |
| `dim_day`, `dim_store` | One observed relative day or store ID. No calendar date, store name or location is inferred. |
| `fct_coupon_redemptions` | One observed household-day-coupon-campaign redemption; it is not a product sale. |
| `bridge_coupon_product_campaign` | One distinct coupon-product-campaign eligibility mapping. |
| `bridge_household_campaign` | One targeted household-campaign pair. |
| `fct_promotion_week` | One product-store-week, after aggregating all source promotion states. |

The full weekly promotion table has 36,771,279 rows. A direct join from its raw 36,786,524 source rows to sales would multiply some lines. `fct_sales_promotion` instead joins the unique weekly grain and retains all 2,595,732 sales lines. Multiple source states remain visible through state counts and conflict flags. A missing promotion match means *unknown*, not confirmed non-exposure; nonzero code flags do not prove that a customer saw a promotion.

## Power BI relationships

The initial report uses `fct_sales_promotion` as its only line-level sales fact. Import `fct_baskets` for overall basket counts and shopping frequency, and `fct_coupon_redemptions` for actual coupon use. Use one-to-many, single-direction relationships from each dimension to the facts and bridges:

| Dimension | Related reporting tables |
|---|---|
| `dim_day.transaction_day` | `fct_sales_promotion.transaction_day`, `fct_baskets.transaction_day`, `fct_coupon_redemptions.redemption_day` |
| `dim_store.store_id` | `fct_sales_promotion.store_id`, `fct_baskets.store_id` |
| `dim_product.product_id` | `fct_sales_promotion.product_id`, `bridge_coupon_product_campaign.product_id` |
| `dim_household.household_key` | `fct_sales_promotion.household_key`, `fct_baskets.household_key`, `fct_coupon_redemptions.household_key`, `bridge_household_campaign.household_key` |
| `dim_campaign.campaign_id` | `fct_coupon_redemptions.campaign_id` and both campaign bridges |

Do not join facts to each other or connect campaign bridges directly to sales. For example, one coupon may be eligible for several products, but a redemption remains one event. Adding `fct_baskets.basket_sales` to line-level sales would also count the same revenue twice. Product-filtered baskets should be counted as distinct basket IDs from the line fact; the basket fact has no product key. This is the documented relationship design; verify active relationships and measures in Power BI Desktop before presenting model screenshots as validated.

## Local configuration

Follow the [README reproduction commands](../README.md#reproduce-locally) for a fresh local database. The included [Compose file](../compose.yaml) starts PostgreSQL 17 on `127.0.0.1:5432` with a persistent named volume. It reads `POSTGRES_PASSWORD` from the ignored root `.env`; the loader and dbt read that value from the **process environment**, so set it in the shell before running them. The loader validates all eight CSVs before connecting, creates `raw` tables on an empty database and refuses to replace populated tables by default. Do not use `--replace-existing` against data you need to keep.

The included [dbt profile](../dbt/profiles.yml) targets schema `analytics`. The historical full-dataset validation used a separate local profile targeting `dbt_dev`; those schemas are not interchangeable. The [isolated fixture instructions](../tests/integration/README.md) cover synthetic ingestion and dbt validation. A fresh original-dataset load followed by a complete dbt build has not been independently validated.

To connect Power BI Desktop, select **Get data > PostgreSQL database**, enter server `127.0.0.1:5432` and database `retail_analytics`, choose **Import**, and authenticate as `retail_user` with the local password in the prompt. Select `analytics` after following the fresh-build commands; select `dbt_dev` only when using the separately validated existing local profile. Keep Docker Desktop running for refreshes. The local PBIX remains withheld until its embedded data and connection settings are reviewed.