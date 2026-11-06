# Power BI dashboard guide

The local Desktop report contains seven business pages plus **DAX TESTING** and **DATA QA** development pages. Its PBIX is withheld from publication pending an embedded-data, connection-metadata and redistribution-rights review. Page names, visual types and slicer fields below were checked against the saved PBIX report definition on 6 November 2026. Other visual-level filters, cross-filter interactions and refreshed values should be checked in Power BI Desktop before publication.

| Page | What it shows | Saved page slicers |
|---|---|---|
| **Executive Overview** | Total sales, baskets, purchasing households, average basket value, sales by reporting week and department performance. | Department; store ID. |
| **Customer Behaviour** | Purchasing households, sales and baskets per purchasing household, and repeat purchasing measures. | Department. |
| **Customer Demographics** | Income-group comparisons for purchasing households and sales per purchasing household. | No page slicer identified in the saved definition. |
| **Promotions & Coupons Dashboard** | Redemption records and redeeming households alongside promotion-record coverage and unknown-status sales lines. | No page slicer identified; a chart uses campaign ID. |
| **Supplier & Product Performance** | Manufacturer-ID and sub-category rankings, product sales, purchasing households, basket reach and sales share. | Department; brand; disconnected Top N selector. |
| **Business Insights** | Brand revenue and reach alongside basket-composition comparisons and written findings. | No page slicer identified. |
| **Business Recommendations** | Three evidence-based actions with supporting context. | No page slicer identified. |

The Supplier page's **Top N** control is designed for Top 5, 10, 20, 50 and All manufacturer and sub-category rankings. The PBIX visual definition confirms the disconnected `Top N Options.Show` slicer; confirm the five displayed choices and DAX behaviour in Desktop when capturing screenshots.

The report uses ten core reporting tables, plus the disconnected Top N selector and an imported **Basket Brand Insights** summary. Use the line-level sales table for sales, the basket table for overall basket counts, and the redemption fact for actual coupon use. A product-filtered basket measure counts distinct qualifying basket IDs from sales lines. Do not add basket sales to line sales or join the coupon/campaign bridges directly to sales. [Architecture](architecture.md) explains why.

Interpret the pages carefully: days and weeks are relative, not calendar dates; demographics cover only 801 purchasing households; missing promotion matches are unknown; and manufacturer IDs are not verified supplier identities. The promotions page is descriptive, not an uplift or ROI analysis. The overall quantity field is unsuitable as a general “Units Sold” KPI because fuel dominates it; a development QA table still contains the measure.

**Development pages:** DAX TESTING and DATA QA contain checking visuals. DAX TESTING is first in the saved page order, and DATA QA is also present. Decide in Power BI Desktop whether to hide or move them before a public walkthrough. No genuine screenshots exist yet; the [screenshot checklist](../screenshots/README.md) describes captures to make later. This documentation update does not alter the PBIX. The [data-source note](data_source.md) explains the open redistribution question.
