# Power BI dashboard guide

The local Desktop report contains seven business pages plus **DAX TESTING** and **DATA QA** development pages. Its PBIX is withheld from publication pending an embedded-data, connection-metadata and redistribution-rights review. Page names, visual types and slicer fields below were checked against the saved PBIX report definition on 6 November 2026. Other visual-level filters, cross-filter interactions and refreshed values should be checked in Power BI Desktop before publication.

| Page | What it shows | Saved page slicers |
|---|---|---|
| **Executive Overview** | Total sales, baskets, purchasing households, average basket value, sales by reporting week and department performance. The Weekly Sales Trend uses weeks 20–101, linear interpolation and a $0 Y-axis start. Weeks 1–19 are excluded while the household panel was building; approximately 99.7% of households had purchased by week 20. Weeks 1 and 102 are partial, with five and six days respectively. Overview KPI cards remain full-period, including $8.06M in sales. | Department; store ID. |
| **Customer Behaviour** | Purchasing households, sales and baskets per purchasing household, and Regular shoppers (52+ weeks) at 48.04%. This measure is the percentage of purchasing households that bought products in at least 52 distinct weeks across the observed period. | Department. |
| **Customer Demographics** | Income-group comparisons for purchasing households and sales per purchasing household, excluding `(Blank)` from comparison charts only. Known demographics remain 801 of 2,500 purchasing households (32.0%); unknown households remain included in overall coverage reporting. | No page slicer identified in the saved definition. |
| **Promotions & Coupons Dashboard** | Redemption records and redeeming households alongside promotion-record coverage and unknown-status sales lines. | No page slicer identified; a chart uses campaign ID. |
| **Supplier & Product Performance** | Manufacturer-ID and sub-category rankings, product sales, purchasing households, basket reach and sales share. This page excludes `KIOSK-GAS` and `MISC SALES TRAN` while retaining `MISC. TRANS.`. Excluded sales are $664,182.32; filtered page sales are $7,393,280.76. Manufacturer 69 is labelled `Mfr 69 (private label)` and has a 20.80% share within this filtered Products page. Its all-department share remains 27.04%. | Department; brand; disconnected Top N selector. |
| **Business Insights** | Brand revenue and reach alongside basket-composition comparisons and written findings. | No page slicer identified. |
| **Business Recommendations** | Three evidence-based actions with supporting context. | No page slicer identified. |

The Supplier page's **Top N** control is designed for Top 5, 10, 20, 50 and All manufacturer and sub-category rankings. The PBIX visual definition confirms the disconnected `Top N Options.Show` slicer; confirm the five displayed choices and DAX behaviour in Desktop when capturing screenshots.

The report uses ten core reporting tables, plus the disconnected Top N selector and an imported **Basket Brand Insights** summary. Use the line-level sales table for sales, the basket table for overall basket counts, and the redemption fact for actual coupon use. A product-filtered basket measure counts distinct qualifying basket IDs from sales lines. Do not add basket sales to line sales or join the coupon/campaign bridges directly to sales. [Architecture](architecture.md) explains why.

The updated Manufacturer Sales Share calculation removes manufacturer filters from both `manufacturer_id` and `Manufacturer Display`, keeping the share denominator across manufacturers within the current page scope. The 20.80% Products-page share and the 27.04% all-department share therefore describe different reporting scopes.

Interpret the pages carefully: days and weeks are relative, not calendar dates; demographic information is known for only 801 purchasing households; missing promotion matches are unknown; and manufacturer IDs are not verified supplier identities. The promotions page is descriptive, not an uplift or ROI analysis. The overall quantity field is unsuitable as a general “Units Sold” KPI because fuel dominates it; a development QA table still contains the measure.

**Development pages:** DAX TESTING and DATA QA are development pages. They are hidden from the published screenshots and are not part of the seven business pages. The [data-source note](data_source.md) explains the open redistribution question.
