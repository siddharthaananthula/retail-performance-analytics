# Data source and reproduction boundary

This project uses dunnhumby's **The Complete Journey** sample dataset. Obtain your own copy from the [dunnhumby source-files page](https://www.dunnhumby.com/source-files/) and review the terms attached to that copy before using or redistributing it. The repository does not include the full source data.

## Required source files

Place these eight files, with their original headers, under `data/raw/` in a local checkout:

| File | Role |
|---|---|
| `transaction_data.csv` | Basket-product sales lines, relative days and source weeks. |
| `product.csv` | Product classifications and manufacturer IDs. |
| `hh_demographic.csv` | Demographics for a subset of purchasing households. |
| `campaign_desc.csv` | Campaign descriptions and relative-day ranges. |
| `campaign_table.csv` | Household campaign targeting. |
| `coupon.csv` | Coupon-product-campaign eligibility mappings. |
| `coupon_redempt.csv` | Observed household coupon redemptions. |
| `causal_data.csv` | Product-store-week promotion records and source codes. |

The source uses relative day numbers, not verified calendar dates, and store IDs without verified names or locations. The locally checked copy contains 2,595,732 transaction lines, 276,484 baskets, 2,500 purchasing households and 2,318 coupon-redemption rows. Recorded sales round to $8,057,463.08. These figures are reference checks for this sample copy, not promises about every distribution or version.

## Reproducing the pipeline

The intended path is **source CSVs → PostgreSQL `raw` → eight dbt staging views → 12 analytical models → Power BI Import model**. [Architecture and local setup](architecture.md) explains the model grains, credentials and connection settings. Keep source archives and extracted CSVs local; `data/raw/` is ignored by Git.

The existing populated PostgreSQL database and its `dbt_dev` models were validated locally. The loader passed a fresh eight-table load, replacement protection and rollback checks against an isolated database containing only invented synthetic records. The fixture dbt build passed 20 models and 73 tests. A fresh load of the **original** dataset has not been validated, so this repository is not yet a verified one-command rebuild of the full source. Such a run should check all eight CSV headers and counts, build dbt models, and reconcile sales lines, baskets, households, redemptions and sales value to the source. The 73 passing full-dataset tests cited elsewhere come from the local run on 2 November 2026; GitHub-hosted CI has not yet been verified.

## Redistribution decision still open

The dataset's availability for download does not itself establish permission to republish source rows or derived files. Review the terms for the **exact copy obtained** and any applicable attribution requirements before publishing raw CSVs, the small derived fixture CSVs, screenshots containing source records, or a PBIX with an embedded Import `DataModel`. The current publication boundary keeps raw data, fixture CSVs and the PBIX out of ordinary Git staging. The report's connection metadata also needs inspection before release. No redistribution permission is claimed here; if it cannot be confirmed, publish only approved code, documentation and non-data-bearing visuals.

The repository's own code license is also undecided. Choose and add one only after the owner has reviewed how it interacts with the dataset's separate terms.
