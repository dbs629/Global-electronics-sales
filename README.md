# Global Electronics Retailer — Data Cleaning

Cleans the 5-table Global Electronics Retailer dataset (`Customers`,
`Exchange_Rates`, `Products`, `Sales`, `Stores`) and produces a data quality
report.

## Setup

```bash
git clone <your-repo-url>
cd <repo-name>
pip install -r requirements.txt
```

Drop the raw CSVs into `data/`:

```
data/
├── Customers.csv
├── Exchange_Rates.csv
├── Products.csv
├── Sales.csv
└── Stores.csv
```

## Usage

```bash
python clean_data.py
# or with custom paths:
python clean_data.py --input-dir path/to/raw --output-dir path/to/clean
```

Cleaned CSVs and `data_quality_report.md` land in `output/` (gitignored by
default — remove it from `.gitignore` if you want to commit example output).

## Issues found and fixed

| File | Issue | Fix |
|---|---|---|
| Customers.csv | Latin-1 encoded, not UTF-8 | re-encoded to UTF-8 |
| Customers.csv | `Zip Code` lost leading zeros (836 rows: AU, DE, FR, IT, US) | re-padded per country's standard length |
| Customers.csv | `City` mixes ALL CAPS / Title Case | standardized to Title Case |
| Customers.csv | UK `State Code` just duplicates the full `State` name — not a real abbreviation | flagged, left as-is (no authoritative code available) |
| Customers.csv | `State Code` missing for 10 rows (Napoli, Italy) | left blank — no source value to fill from |
| Products.csv | `Unit Cost USD` / `Unit Price USD` stored as text (`"$1,060.22 "`) | converted to numeric floats |
| Sales.csv | `Delivery Date` missing for ~79% of rows | left blank — means "not yet delivered," not an error |
| Stores.csv | `Square Meters` missing for the Online store | left blank — no physical footprint |

Checked and clean already: no duplicate rows or duplicate keys in any file;
every foreign key in `Sales.csv` (CustomerKey, StoreKey, ProductKey) matches
its parent table with zero orphans; all dates parse with no delivery-before-
order cases; currency codes match 1:1 between `Sales.csv` and
`Exchange_Rates.csv`.

## SQL analysis

Once the cleaned CSVs are loaded into a database (tables matching the cleaned file names), these queries answer some common
retail-analytics questions.

### Sales performance, seasonal trend & channel analysis

**Seasonal trend (revenue, profit, orders)**

```sql
SELECT
    YEAR(Order_Date) AS Year,
    MONTH(Order_Date) AS Month,
    SUM(s.Quantity * p.Unit_Price_USD) AS Revenue,
    SUM(s.Quantity * (p.Unit_Price_USD - p.Unit_Cost_USD)) AS Profit,
    COUNT(DISTINCT Order_Number) AS Orders
FROM Sales s
JOIN Products p
    ON s.ProductKey = p.ProductKey
GROUP BY YEAR(Order_Date), MONTH(Order_Date)
ORDER BY Year, Month ASC;
```

Same metrics as above, broken down to the month level to surface
seasonality (e.g. holiday-quarter spikes).

- **Revenue** = quantity × unit price
- **Profit** = quantity × (unit price − unit cost)
- **Orders** = distinct order count (not line items) per year/category

![Revenue YoY](RevenueYoY.png)

Key findings:
Revenue shows a repeating Q4-peak, Q1-trough pattern — it builds toward a high around each year-end (likely holiday shopping) before dropping sharply in the following January/February, and this cycle repeats across 2016–2020. That said, some of those early-year drops fall to literal $0, which looks more like a data gap than a true seasonal low, so the peak-to-trough shape is probably real but the depth is exaggerated in places.



**Average order value by channel**

```sql
SELECT
    YEAR(Order_Date) AS Year,
    Channel,
    SUM(c.Quantity * p.Unit_Price_USD) / COUNT(DISTINCT Order_Number) AS AOV
FROM Channel c
JOIN Products p
    ON c.ProductKey = p.ProductKey
GROUP BY YEAR(Order_Date), Channel
ORDER BY Year ASC;
```

> Assumes a `Channel` table/view (e.g. Online vs. In-Store) that isn't part
> of the base 5 CSVs — worth a line here on how you built it (e.g. derived
> from `Stores.StoreKey = 0` = Online) if you're sharing this repo.

### Customer analysis & segmentation

**Spend by generation**

```sql
WITH gen AS (
    SELECT
        CustomerKey,
        CASE
            WHEN YEAR([Birthday]) BETWEEN 1997 AND 2012 THEN 'Gen Z'
            WHEN YEAR([Birthday]) BETWEEN 1981 AND 1996 THEN 'Millennials'
            WHEN YEAR([Birthday]) BETWEEN 1965 AND 1980 THEN 'Gen X'
            WHEN YEAR([Birthday]) BETWEEN 1946 AND 1964 THEN 'Boomers'
            WHEN YEAR([Birthday]) >= 2013 THEN 'Gen Alpha'
            ELSE 'Unknown'
        END AS Generation
    FROM Customers
)
SELECT
    Generation,
    SUM(s.Quantity * p.Unit_Price_USD) AS Total_spending,
    COUNT(DISTINCT Order_Number) AS Orders,
    SUM(s.Quantity * p.Unit_Price_USD) / COUNT(Order_Number) AS AOV
FROM Sales s
JOIN Products p
    ON s.ProductKey = p.ProductKey
JOIN gen g
    ON s.CustomerKey = g.CustomerKey
GROUP BY Generation
ORDER BY Total_spending DESC;
```

Buckets customers into generational cohorts by birth year and ranks cohorts
by total spend. Customers born before 1946 fall into `Unknown` under this
cutoff scheme.

> Heads up: this `AOV` divides by `COUNT(Order_Number)` (every line item),
> while `Orders` right above it uses `COUNT(DISTINCT Order_Number)`. If you
> want AOV to mean "average per order" — consistent with the channel query
> above — switch the AOV denominator to `COUNT(DISTINCT Order_Number)` too.

## License

MIT (or your choice — update this section).
