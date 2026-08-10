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

## License

MIT (or your choice — update this section).
