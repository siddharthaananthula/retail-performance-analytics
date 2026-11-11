# Project Decisions

This file records the main decisions I made while building the retail performance Power BI project.

The goal is to explain not just what I did, but why I did it. I want this project to show the reasoning behind the data model, cleaning rules, KPI choices and reporting decisions.

## D001. Keep the raw data unchanged

I keep all original Dunnhumby CSV files inside `data/raw/` and do not modify them directly.

The raw files are ignored by Git because they are large and should not be stored in the repository.

Any cleaning or transformation will happen later in PostgreSQL and dbt.

Reason:

If I change the source files directly, it becomes harder to reproduce the pipeline or explain which changes were made. Keeping raw data untouched gives me a clean source of truth.

---

## D002. Use `transaction_data.csv` as the main sales fact source

The transaction table contains 2,595,732 rows.

I confirmed that:

- there are 276,484 unique baskets
- there are 2,500 households
- there are 92,339 products used in transactions
- there are 582 stores
- `BASKET_ID + PRODUCT_ID` has no duplicates

This means one row represents one product within one basket.

If multiple units of the same product are purchased in the basket, the quantity is stored in the `QUANTITY` column instead of repeating the product row.

This makes `transaction_data.csv` the main source for sales, basket, product and customer KPIs.

---

## D003. Treat `product.csv` as the product dimension source

`product.csv` contains 92,353 rows and 92,353 unique `PRODUCT_ID` values.

There are no duplicate product IDs.

Every product used in `transaction_data.csv` exists in the product table.

This means `PRODUCT_ID` can be safely used as the relationship key between the product dimension and the transaction fact table.

The product table provides:

- department
- brand
- manufacturer
- commodity
- sub-commodity
- product size

---

## D004. Demographic analysis only covers part of the customer base

There are 2,500 households in the transaction data.

Only 801 of them have demographic information in `hh_demographic.csv`.

This gives demographic coverage of 32.04%.

The demographic table itself is clean, with 801 rows and 801 unique household keys.

I will keep all 2,500 households in sales analysis.

For demographic visuals, I will clearly state that the results only represent households with available demographic data.

I will not present demographic findings as if they represent the full customer base.

---

## D005. Campaign targeting requires a bridge table

`campaign_desc.csv` contains 30 campaigns and each campaign ID is unique.

`campaign_table.csv` links households to campaigns.

One household can belong to multiple campaigns.

The maximum observed was 17 campaigns for one household, with an average of 4.55 campaigns per targeted household.

This creates a many-to-many relationship between households and campaigns.

I will not join the campaign table directly into the transaction fact table because that could duplicate sales rows.

The campaign targeting table will remain as a separate bridge table.

---

## D006. Use `campaign_desc.csv` as the campaign dimension

Both `campaign_desc.csv` and `campaign_table.csv` contain a campaign description.

I checked all 7,208 campaign targeting rows and found zero description mismatches.

This means the description stored in `campaign_table.csv` is redundant.

The campaign dimension will use:

- `CAMPAIGN`
- `DESCRIPTION`
- `START_DAY`
- `END_DAY`

The bridge table only needs the household and campaign keys.

---

## D007. Coupon to product relationships are many-to-many

`coupon.csv` contains 1,135 unique coupons and 44,133 unique products.

One coupon can apply to many products.

The largest coupon in the raw data is linked to 14,477 products.

One product can also appear under multiple coupons, with a maximum of 11 coupons for one product.

Because both sides can repeat, `coupon.csv` is a bridge between coupons and products rather than a simple dimension.

---

## D008. Deduplicate `coupon.csv` in the staging layer

`coupon.csv` contains 5,164 exact duplicate rows.

There are 1,824 duplicated combinations of:

- `COUPON_UPC`
- `PRODUCT_ID`
- `CAMPAIGN`

Some combinations appear as many as 19 times.

The repeated rows contain no additional information.

I will keep the raw file unchanged, but the dbt staging model will keep one unique row per coupon-product-campaign combination.

This prevents overcounting in coupon coverage and promotion analysis.

---

## D009. Coupon redemption rows are clean

`coupon_redempt.csv` contains:

- 2,318 redemption rows
- 434 households that redeemed at least one coupon
- 556 unique coupons redeemed
- redemptions across all 30 campaigns

There are no exact duplicate redemption rows.

The working grain is one household redeeming one coupon on one day within one campaign.

---

## D010. `causal_data.csv` cannot be joined directly to sales

`causal_data.csv` contains 36,786,524 rows.

The file is sorted by:

- `PRODUCT_ID`
- `STORE_ID`
- `WEEK_NO`

There are 36,771,279 distinct product-store-week groups.

I found 15,245 product-store-week combinations with multiple promotion states.

There are zero exact duplicate full rows.

This means the raw table is not always one row per product-store-week.

Some combinations contain multiple `display` or `mailer` states.

Because of this, I will not join the raw causal table directly to sales using only product, store and week.

A later dbt model will aggregate promotion information to a safe product-store-week grain before joining it to sales.

---

## D011. Do not use raw `QUANTITY` as a global units-sold KPI

Most transaction rows have `QUANTITY = 1`.

However, the dataset also contains very large quantity values.

There are 23,136 rows where `QUANTITY > 100`, which is 0.891% of all transaction rows.

Almost all of them are:

- KIOSK-GAS: 20,267 rows
- MISC SALES TRAN: 2,868 rows

The largest quantity values are related to gasoline and use a different quantity scale from normal grocery products.

Because of this, I will not use `SUM(QUANTITY)` as a global units-sold KPI across every department.

Sales value can still include these transactions.

Unit-based KPIs will either exclude fuel and miscellaneous transaction departments or separate them from normal merchandise.

---

## D012. Keep high sales values unless there is evidence they are invalid

The maximum line-level `SALES_VALUE` is $840.

I inspected the highest-value rows and found they were mainly:

- electronic gift cards
- tickets
- miscellaneous transactions
- patio sets
- floral baskets
- meat
- fuel

These values appear plausible for the product types involved.

I will keep them in sales analysis and will not cap or remove them just because they are high.

---

## D013. Treat near-zero retail discount values as floating-point noise

Most `RETAIL_DISC` values are zero or negative.

There are 36 rows with values above zero.

Most of those positive values are extremely small numbers such as:

- `2.22e-16`
- `4.44e-16`

These are effectively zero and come from floating-point precision.

Only 10 rows have `RETAIL_DISC > 0.001`.

I will treat values with an absolute size below 0.001 as zero.

The remaining genuine positive values will be preserved unless further evidence explains them.

---

## D014. Coupon discount fields behave consistently

`COUPON_DISC` and `COUPON_MATCH_DISC` are always zero or negative.

There are:

- 36,422 rows with `COUPON_DISC < 0`
- 17,449 rows with `COUPON_MATCH_DISC < 0`

There are zero rows where a coupon match exists without a normal coupon discount.

This means a retailer match is optional, but only appears when a coupon discount is already present.

Later:

`Total Coupon Discount = absolute coupon discount + absolute coupon match discount`

---

## D015. Treat midnight transaction times as valid

`TRANS_TIME` behaves like HHMM time.

There are zero invalid time values.

There are 443 rows with `TRANS_TIME = 0`, representing 53 baskets across 49 households and 35 stores.

These rows are spread from day 7 to day 707 and contain normal retail departments.

This does not look like one isolated system error.

For now I will treat `TRANS_TIME = 0` as a valid midnight value.

I will avoid making business claims about midnight shopping unless later analysis supports them.

---

## D016. Keep zero-sales transaction rows, but do not treat all of them as normal products

There are:

- zero negative sales rows
- 18,850 rows with `SALES_VALUE = 0`
- 16,305 baskets containing at least one zero-sales row

Of the zero-sales rows, 7,839 have a blank department.

Most of those blank rows come from two product IDs:

- `5978656`: 4,887 rows
- `5978648`: 2,867 rows

These product IDs have almost no product description.

`5978656` often has:

- quantity 0
- sales value 0
- negative coupon discount

This behaves like a non-merchandise transaction record used to carry coupon or discount information.

`5978648` often has:

- quantity 0
- sales value 0
- no discount

This also behaves like a non-merchandise transaction record rather than a normal product sale.

The source does not provide an official description for these IDs, so I will not invent one.

These rows will stay in the raw and staging data, but they will not be counted as normal products sold or used in standard product/category performance KPIs.

---

## D017. Keep positive sales records with zero quantity

During transaction profiling, I found:

- 14,466 rows with QUANTITY = 0
- 14,399 of these also have SALES_VALUE = 0
- 67 rows have positive SALES_VALUE despite having zero quantity

The 67 positive-sales rows include ordinary product categories such as produce, grocery and personal care.

I could not confirm whether these came from measurement rounding, transaction adjustments or source-data inconsistencies.

**Decision:**

I will preserve the original sales and quantity values instead of replacing missing quantities with an assumed value of 1.

These records will be flagged during staging and excluded from unit-price calculations where the denominator would be zero.

I will also keep non-merchandise transaction identification separate from zero-quantity identification, since not every zero-quantity row is necessarily a non-merchandise record.

## D018. Retain the unusual bulk produce transaction

I identified one Produce transaction with QUANTITY greater than 100.

The record contains:

- Product ID: 911878
- Product: Corn White
- Package description: 48 CT
- Quantity: 144
- Sales value: 24.00
- Retail discount: -24.00

The quantity is exactly three times the stated package count of 48.

This could be a bulk purchase, but I cannot confirm how the source system represents units for this item.

**Decision:**

I will retain the record rather than remove it as an outlier. The quantity will be interpreted cautiously when defining merchandise unit-based KPIs.

## D019. Treat blank product categories separately from null values

The initial null check found no missing values in the seven loaded source tables.

However, later categorical profiling found blank strings in the product table:

- DEPARTMENT: 15 blank values
- COMMODITY_DESC: 15 blank values
- SUB_COMMODITY_DESC: 15 blank values
- CURR_SIZE_OF_PRODUCT: 30,607 blank values

All 15 products with blank category classifications appear in transactions.

Two of these product IDs, 5978648 and 5978656, were previously identified as behaving like special transaction records.

**Decision:**

I will preserve the source values in staging.

For reporting, blank classifications can be labelled as Unclassified or Not specified.

I will not assume that every unclassified product is a non-merchandise record. Exclusion rules must be based on transaction behaviour and documented business logic rather than missing descriptions alone.

## D020. Do not invent missing product sizes

Product size is blank for 30,607 of the 92,353 products.

This represents approximately 33.14% of the product catalogue.

The field contains values such as 16 OZ, 12 OZ and 750 ML, but not every product has a usable recorded size.

**Decision:**

I will not replace missing sizes with zero or infer sizes from product descriptions without a validated method.

Product-size analysis will only use products with suitable source information. Missing sizes can be labelled as Not specified in reporting.

## D021. Preserve the source week numbering

Transaction data covers:

- 711 distinct days
- 102 reporting weeks
- Zero days assigned to multiple weeks

Week 1 contains days 1 to 5.

Weeks 2 to 101 contain seven days each.

Week 102 contains days 706 to 711.

**Decision:**

I will preserve the supplied DAY and WEEK_NO relationships when constructing the date dimension.

I will not assume that week 1 begins with a complete seven-day period.

Weekly comparisons will account for partial weeks, for example by using average daily sales or clearly marking incomplete weeks.

The source provides relative days rather than confirmed calendar dates, so any calendar mapping must be documented as an assumption.

## D022. Calculate campaign reach using distinct households

The campaign targeting table contains:

- 30 campaigns
- 7,208 targeting records
- 1,584 unique targeted households

The transaction dataset contains 2,500 households.

Therefore, 63.36% of transacting households were targeted by at least one campaign.

Individual campaigns have different audience sizes. Campaign 18 targeted 1,133 households, while smaller campaigns targeted considerably fewer.

**Decision:**

Campaign reach will use distinct household counts.

The denominator for overall household reach will be the 2,500 observed transacting households, not an assumed total retailer customer population.

Campaign audiences overlap, so I will not add individual campaign reach percentages to calculate total reach.

## D023. Separate campaign reach from coupon redemption participation

The dataset contains 2,318 coupon redemption records across 434 unique households.

All redemption records matched households targeted by their recorded campaign.

I calculated household-level redemption participation as:

434 / 1,584 × 100 = 27.40%

Campaign 18 had 214 redeeming households out of 1,133 targeted households, giving an observed household redemption rate of 18.89%.

**Decision:**

I will keep the following metrics separate:

- Households targeted
- Unique households redeeming
- Household redemption participation rate
- Number of coupon redemption records
- Distinct coupons redeemed

Household redemption participation will not be described as the proportion of coupons redeemed.

A high redemption rate also does not automatically imply a profitable campaign.

## D024. Validate coupon and campaign relationships before reporting

I performed two checks on all 2,318 coupon redemption records.

First, I verified that the redeeming household was targeted by the recorded campaign.

Second, I verified that the redeemed coupon was associated with the recorded campaign in the coupon table.

Both checks returned:

- Valid matches: 2,318
- Unmatched records: 0

**Decision:**

These checks will be recreated as automated dbt data-quality tests where appropriate.

This will help prevent invalid campaign and coupon relationships from entering the reporting layer.

## D025. Keep promotional reporting descriptive

The dataset contains campaign targeting, coupon redemption and promotion-related information.

However, observing higher sales during a campaign does not prove the campaign caused the increase.

Customers might have purchased the same products without the promotion.

**Decision:**

The initial Power BI report will focus on observed campaign performance, coupon usage and descriptive sales comparisons.

I will not label promotional-period sales differences as incremental lift.

Counterfactual estimation and causal impact analysis are outside the scope of this first reporting version.

## D026. Separate data exploration from production transformations

I used Python and pandas to understand the source files and investigate unusual records.

For the large causal dataset, I used chunked processing to avoid loading the entire dataset into memory.

The notebook helped identify the cleaning and modelling requirements, but the notebook itself will not become the production transformation pipeline.

**Decision:**

The reusable data workflow will use PostgreSQL and dbt.

The notebook will remain as evidence of the original investigation.

Cleaning rules, transformation logic and data-quality tests will be implemented in version-controlled models so they can be repeated consistently.

## D027. Keep Power BI deployment claims accurate

The current project will use Power BI Desktop for reporting and GitHub for version control.

Power BI Service deployment is not part of the selected approach.

**Decision:**

I plan to version-control the Power BI project using PBIP where practical, validate the upstream data workflow through GitHub Actions, and present the report using exported visuals, documentation and a walkthrough.

I will only describe CI/CD as implemented once the workflow is running and tested.

I will not describe the Power BI report as live or deployed to Power BI Service.

---

## D028. Use observed relative days as the reporting day dimension

The source has 711 observed transaction days, numbered 1-711, with one source week per day. Redemption days all fall within that range. There is no verified mapping to calendar dates.

**Decision:** `dim_day` contains each observed `transaction_day`, its source `week_no`, its position within that week, the observed week bounds and an `is_partial_week` flag. Week 1 has five observed days; week 102 has six. I will label report periods as relative days and reporting weeks, not calendar dates. For example, a supermarket's "day 421" can be compared with "day 420" without claiming either was a particular Monday.

## D029. Use actual store IDs without invented attributes

There are 582 distinct store IDs in sales, but this dataset does not provide verified names, addresses or regions.

**Decision:** `dim_store` contains exactly those IDs. A report can compare store 5 with store 6, but cannot label them as Sydney or Melbourne stores. Tests ensure that sales and baskets reference known store IDs.

## D030. Materialize the safe sales-promotion reporting grain

The 36,786,524 raw causal rows collapse to 36,771,279 product-store-week rows; 15,245 groups have conflicting display or mailer states. Joining the raw states directly to sales would duplicate transaction lines. The full weekly promotion table occupies about 2,686 MB in local PostgreSQL.

**Decision:** `fct_promotion_week` remains one product-store-week row with source/state counts. `fct_sales_promotion` joins that unique grain to each sales line and is materialized as a table for Power BI. It has 2,595,732 rows and occupies about 240 MB. For example, if a cereal has two display codes in the same store-week, a cereal sale remains one sales row with a conflict flag. A line-level integrity test compares every original sales field, and a uniqueness test checks the basket-product key.

The raw display codes are `0-7`, `9`, `A`; mailer codes are `0`, `A`, `C`, `D`, `F`, `H`, `J`, `L`, `P`, `X`, `Z`. A nonzero code is recorded activity, not verified customer exposure, because the code meanings have not been confirmed. The aggregate retains conflict evidence as counts; exact codes remain in staging. `has_promotion_record` separates a missing match from a matched record with no nonzero code. In the current data, 2,031,958 sales lines have no promotion match, 563,774 have one, 858 join to conflicting states, and none have a matched record with both code flags false.

## D031. Keep sales and baskets as separate Power BI facts

`fct_sales_promotion` has one row per basket-product transaction line. `fct_baskets` has one row per shopping basket. Both carry sales values at their own grains.

**Decision:** Import only `fct_sales_promotion` for line sales and use `fct_baskets` for basket counts and overall shopping frequency. Do not add the two sales columns together or connect the fact tables directly. For example, a $10 basket containing two products contributes $10 to line sales in total and one basket; summing line sales plus basket sales would incorrectly report $20. A product-filtered "baskets containing the product" measure counts distinct basket IDs in the line fact because the separate basket fact has no product key.

## D032. Keep campaign and coupon bridges away from sales totals

A household may be targeted by several campaigns, and a coupon can cover several products. Redemptions are observed household-day-coupon-campaign events, not product purchases.

**Decision:** Relate `dim_campaign` and `dim_household` to targeting and redemption tables using single-direction filtering. Relate `dim_product` and `dim_campaign` to coupon eligibility, but do not link either bridge directly to sales. A coupon valid for two cereals is still one redemption when a household uses it once. Campaign-associated sales need explicit measure logic and must not be presented as causal lift.

## D033. Support a supplier view with the sample dataset

`dim_product` contains department, commodity, sub-commodity and manufacturer ID; the line fact contains product, household and basket keys. `dim_household` has demographics for only 801 of 2,500 purchasing households.

**Decision:** The supplier-view page will compare sub-category sales and manufacturer IDs, count purchasing households and baskets containing selected products, and identify repeat purchasers using two or more distinct qualifying baskets in the selected period. It will not invent manufacturer names or generalize the demographic subset to all customers. The page is planned for Phase 3; no Power BI report has been created in Phase 2.

## D034. Record Phase 2 validation and remaining reproducibility work

On 2 November 2026, all 73 dbt tests passed in the existing local `dbt_dev` profile. Raw, staging, sales and basket layers reconcile to 2,595,732 transaction lines, 276,484 baskets, 2,500 purchasing households and $8,057,463.08 total sales. Raw and mart redemption counts both equal 2,318. `dim_day` has 711 rows and `dim_store` has 582.

**Decision:** Treat this as local Phase 2 validation. Local drafts of the ingestion script and GitHub Actions fixture workflow were reviewed but not executed during Step 84 and are excluded from the Phase 2 release. The script assumes existing raw-table column order and needs `POSTGRES_PASSWORD` in its process environment; its `.env` file is not auto-loaded. The workflow targets a separate `analytics` schema, while local validation uses `dbt_dev`. CI success and Power BI report performance remain unverified until those later steps are actually run.

## D035. Present the completed Desktop report without overstating automation

By 6 November 2026, the local PBIX contains seven business pages plus DAX Testing and Data QA pages. It is about 37 MB and is not yet tracked by Git. Genuine screenshots have not been captured. The Power BI report is a Desktop artefact; it is not a Power BI Service deployment. The earlier Phase 2 statements above record what was complete at that time.

**Decision:** Document the built report, validated business findings and remaining data limitations. Keep the unverified ingestion and CI drafts out of the release until tested. Review embedded data and connection metadata before deciding whether to publish the PBIX. Capture genuine screenshots manually and decide whether to hide the development pages before the public walkthrough.

**Update (12 November 2026):** Genuine screenshots of the seven business pages have now been added to `screenshots/`, and the portfolio site is published on GitHub Pages.

## D036. Set a publication boundary before adding automation or report files

The publication audit found that the dataset, fixture CSVs and local Power BI Import file need a redistribution-rights and embedded-data review. The documentation and screenshot checklist exist locally but are not yet committed. The ingestion and CI drafts have not passed an isolated local validation. A verified dbt test run is evidence for the existing analytics models, not evidence that the full pipeline can be rebuilt safely from an empty database.

**Decision:** Keep source data, fixture CSVs, the PBIX, credentials, generated caches and Docker data out of ordinary Git staging. Publish reviewed documentation and code only after checking links, paths and secrets. Replace personal setup paths with portable dbt profile instructions, record the unresolved rights question in [data source and reproduction](docs/data_source.md), and validate the loader against a disposable database before considering CI. No analytical SQL, data or report file is changed by this documentation decision.
