# Business findings and recommendations

The figures below come from the locally checked Complete Journey sample and Phase 2 analysis; key sales, brand and basket totals were independently checked against source CSVs during the publication audit. They do not measure profit, customer preference or causal impact. “Qualifying-basket revenue” means revenue from the selected brand type within baskets containing that brand, not the full value of those baskets. [Data source and reproduction](data_source.md) describes how to obtain the sample and the open redistribution question.

## Validated findings

| Brand classification | Recorded revenue | Share of all sales | Purchasing households | Baskets containing brand | Basket reach | Revenue per qualifying basket |
|---|---:|---:|---:|---:|---:|---:|
| National | $5,820,201.75 | 72.23% | 2,500 | 238,309 | 86.2% | $24.42 |
| Private | $2,237,261.33 | 27.77% | 2,496 | 195,721 | 70.8% | $11.43 |

The brand revenues sum to the $8,057,463.08 recorded sales baseline. The two household and basket groups overlap, so their counts must not be added.

| Basket composition | Baskets | Revenue | Share of all sales | Average basket value | Average lines per basket |
|---|---:|---:|---:|---:|---:|
| Both Private and National | 157,546 | $6,468,441.00 | 80.28% | $41.06 | 14.58 |
| National only | 80,763 | $905,664.25 | N/A | $11.21 | 3.09 |
| Private only | 38,175 | $683,357.83 | N/A | $17.90 | 1.27 |

Mixed-brand baskets are about **57.0%** of the 276,484 baskets and contain more lines on average. Their larger share of revenue is associated with larger basket sizes; brand mixing itself has not been shown to cause higher spending. The three basket groups are mutually exclusive and reconcile to 276,484 baskets and $8,057,463.08 sales.

In Private-only baskets, `KIOSK-GAS` contributes 76.80% of revenue and `MISC SALES TRAN` contributes 13.27%; together they account for 90.07%. This makes an all-department Private-only average a poor proxy for grocery shopping.

For **Grocery only**, National products contribute $2,987,981.47 (72.99%) with $15.64 revenue per qualifying basket and 2,499 purchasing households. Private products contribute $1,105,832.67 (27.01%) with $7.26 revenue per qualifying basket and 2,490 purchasing households. These are revenue comparisons, not price, margin or preference measures.

Manufacturer ID **69** has $2,178,431.70 recorded revenue (27.04% of all sales), is classified as Private, and has $1,091,687.90 Grocery revenue (26.67% of Grocery sales). Its commercial identity has not been verified; the ID must not be presented as a confirmed supplier name or company.

## Analytical interpretation

National products contribute more recorded revenue, while Private products appear in baskets from nearly all purchasing households. Mixed-brand baskets are common, but include larger shopping missions. The Private-only basket total is strongly influenced by fuel and miscellaneous departments. These patterns support further category-level investigation; they do not establish pricing advantage, profitability or a causal effect of promotions or brand mixing.

## Evidence-based next steps

### 1. Investigate Private-label opportunities in Grocery

- **Evidence:** Private Grocery revenue is $1,105,832.67, or 27.01% of Grocery revenue; 2,490 households bought Private Grocery products.
- **Interpretation:** There is an observed customer base for Private products, with scope to investigate category-level spending differences.
- **Action:** Compare like-for-like Grocery products, prices, availability and gross margins before designing a controlled merchandising or promotion test.
- **Measure success:** Track category-level Private revenue share, gross margin and repeat purchasing in a defined test group against a suitable comparison group.
- **Limitation:** Current revenue does not show margins, prices per comparable unit or why a household chose a product.

### 2. Investigate basket-building opportunities

- **Evidence:** Mixed-brand baskets are 57.0% of baskets and 80.28% of revenue, with 14.58 lines on average.
- **Interpretation:** Larger shopping missions often include both brand types.
- **Action:** Analyse frequently co-purchased categories and test relevant product placement or combinations where stock and margin data support it.
- **Measure success:** Compare basket value, item count and margin against a control or matched baseline, including the cost of any test.
- **Limitation:** Mixed baskets are already larger; the observed association cannot be treated as an incremental sales estimate.

### 3. Improve promotion-data quality before uplift analysis

- **Evidence:** Only about 21.7% of transaction lines match a promotion record; 15,245 product-store-week keys have conflicting states, and the code meanings are not verified.
- **Interpretation:** Current promotion flags support descriptive coverage checks but cannot reliably prove exposure.
- **Action:** Reconcile product-store-week mapping, investigate conflicting states, obtain the codebook and define a valid exposure measure before any uplift study.
- **Measure success:** Track match coverage, conflict counts, code-definition completeness and independently validated exposure records.
- **Limitation:** Better metadata alone will not establish causality; uplift still needs an appropriate counterfactual.

See [data quality](data_quality.md) for the reporting caveats and [dashboard guide](dashboard_guide.md) for where these findings appear.
