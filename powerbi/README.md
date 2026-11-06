# Power BI development

The seven-page Power BI Desktop report exists locally but is not included in this publication snapshot. Its Import model contains sample data, and its connection metadata and redistribution rights require review before release. The project does not claim that a new clone can open the original PBIX.

After building dbt in a fresh local database, connect Power BI Desktop to PostgreSQL as described in the [architecture guide](../docs/architecture.md). The [dashboard guide](../docs/dashboard_guide.md) documents the existing pages and measures. Use the `analytics` reporting tables for a fresh build; the historical full-data report used a separately configured `dbt_dev` schema. Keep facts at their documented grains so basket and sales revenue is not counted twice.