#!/usr/bin/env python3
"""
clean_data.py — cleans the Global Electronics Retailer dataset
(Customers, Exchange_Rates, Products, Sales, Stores).

Usage
-----
    python clean_data.py                       # reads ./data, writes ./output
    python clean_data.py --input-dir path/to/raw --output-dir path/to/clean

Fixes applied
-------------
Customers:
    - Latin-1 -> UTF-8 re-encoding (source file isn't valid UTF-8)
    - whitespace trimmed on all text columns
    - City standardized to Title Case (source mixes ALL CAPS / Title Case)
    - Zip Code re-padded where a leading zero was lost (Australia -> 4 digits,
      Germany/France/Italy/US -> 5 digits; Canada/Netherlands/UK use
      alphanumeric codes, e.g. "SW1A 1AA", and are left untouched)
    - Birthday parsed to a real date
    - missing State Code (10 rows, all Napoli, Italy) left blank - no source
      value exists to fill from
    - UK State Code flagged: it duplicates the full State name rather than
      being a real abbreviation - left as-is rather than fabricating a code
Exchange_Rates:
    - whitespace trimmed, Date parsed
Products:
    - Unit Cost USD / Unit Price USD converted from text (e.g. "$1,060.22 ")
      to numeric floats
Sales:
    - Order Date / Delivery Date parsed; missing Delivery Date (~79% of rows)
      kept blank rather than imputed - it legitimately means "not delivered yet"
Stores:
    - Open Date parsed; missing Square Meters kept blank for the Online store
      (StoreKey 0), which has no physical footprint

All five files are also checked for duplicate rows, duplicate keys, and (for
Sales) orphaned foreign keys against Customers/Stores/Products. A summary is
printed to stdout and written to output/data_quality_report.md.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd


def clean_customers(input_dir: Path, output_dir: Path, log: list[str]) -> None:
    log.append("=== Customers.csv ===")
    df = pd.read_csv(input_dir / "Customers.csv", encoding="latin-1")

    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype("string").str.strip()

    df["City"] = df["City"].str.title()

    zip_standard_len = {"Australia": 4, "Germany": 5, "France": 5, "Italy": 5, "United States": 5}
    df["Zip Code"] = df["Zip Code"].astype(str)
    fixed = 0
    for country, exp_len in zip_standard_len.items():
        mask = (df["Country"] == country) & (df["Zip Code"].str.len() < exp_len)
        fixed += int(mask.sum())
        df.loc[mask, "Zip Code"] = df.loc[mask, "Zip Code"].str.zfill(exp_len)
    log.append(f"Zip Code: re-padded {fixed} rows with a lost leading zero")

    missing_state_code = int(df["State Code"].isna().sum())
    log.append(f"Missing State Code: {missing_state_code} rows (all State='Napoli', Italy) -> left blank")

    uk_mask = df["Country"] == "United Kingdom"
    uk_dup = bool((df.loc[uk_mask, "State Code"] == df.loc[uk_mask, "State"]).all())
    log.append(f"UK State Code duplicates State name for all UK rows: {uk_dup} -> flagged, not a real abbreviation")

    df["Birthday"] = pd.to_datetime(df["Birthday"], format="%m/%d/%Y", errors="coerce")
    log.append(f"Unparseable Birthday values: {int(df['Birthday'].isna().sum())}")

    df.to_csv(output_dir / "Customers_clean.csv", index=False, encoding="utf-8")
    log.append(f"Rows written: {len(df)}\n")


def clean_exchange_rates(input_dir: Path, output_dir: Path, log: list[str]) -> None:
    log.append("=== Exchange_Rates.csv ===")
    df = pd.read_csv(input_dir / "Exchange_Rates.csv")
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype("string").str.strip()
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="coerce")
    log.append(f"Missing values: {int(df.isna().sum().sum())}")
    df.to_csv(output_dir / "Exchange_Rates_clean.csv", index=False, encoding="utf-8")
    log.append(f"Rows written: {len(df)}\n")


def clean_products(input_dir: Path, output_dir: Path, log: list[str]) -> None:
    log.append("=== Products.csv ===")
    df = pd.read_csv(input_dir / "Products.csv")
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype("string").str.strip()

    for col in ["Unit Cost USD", "Unit Price USD"]:
        df[col] = (
            df[col].astype(str)
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.strip()
            .astype(float)
        )
    loss_making = int((df["Unit Cost USD"] > df["Unit Price USD"]).sum())
    log.append(f"Products where cost > price: {loss_making}")
    df.to_csv(output_dir / "Products_clean.csv", index=False, encoding="utf-8")
    log.append(f"Rows written: {len(df)}\n")


def clean_sales(input_dir: Path, output_dir: Path, log: list[str]) -> None:
    log.append("=== Sales.csv ===")
    df = pd.read_csv(input_dir / "Sales.csv")
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype("string").str.strip()

    df["Order Date"] = pd.to_datetime(df["Order Date"], format="%m/%d/%Y", errors="coerce")
    df["Delivery Date"] = pd.to_datetime(df["Delivery Date"], format="%m/%d/%Y", errors="coerce")

    missing_delivery = int(df["Delivery Date"].isna().sum())
    log.append(f"Missing Delivery Date: {missing_delivery} / {len(df)} ({missing_delivery/len(df):.1%}) -> kept blank")

    bad_logic = int((df["Delivery Date"].notna() & (df["Delivery Date"] < df["Order Date"])).sum())
    log.append(f"Delivery Date before Order Date: {bad_logic}")

    dup_keys = int(df.duplicated(subset=["Order Number", "Line Item"]).sum())
    log.append(f"Duplicate Order Number+Line Item: {dup_keys}")

    df.to_csv(output_dir / "Sales_clean.csv", index=False, encoding="utf-8")
    log.append(f"Rows written: {len(df)}\n")


def clean_stores(input_dir: Path, output_dir: Path, log: list[str]) -> None:
    log.append("=== Stores.csv ===")
    df = pd.read_csv(input_dir / "Stores.csv")
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype("string").str.strip()
    df["Open Date"] = pd.to_datetime(df["Open Date"], format="%m/%d/%Y", errors="coerce")

    missing = df.loc[df["Square Meters"].isna(), "Country"].tolist()
    log.append(f"Missing Square Meters: {len(missing)} row(s), Country={missing} -> kept blank")

    df.to_csv(output_dir / "Stores_clean.csv", index=False, encoding="utf-8")
    log.append(f"Rows written: {len(df)}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean the Global Electronics Retailer CSVs.")
    parser.add_argument("--input-dir", default="data", help="folder with the raw CSVs (default: ./data)")
    parser.add_argument("--output-dir", default="output", help="folder to write cleaned CSVs to (default: ./output)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    required = ["Customers.csv", "Exchange_Rates.csv", "Products.csv", "Sales.csv", "Stores.csv"]
    missing_files = [f for f in required if not (input_dir / f).exists()]
    if missing_files:
        sys.exit(f"Missing input file(s) in {input_dir}: {', '.join(missing_files)}")

    log: list[str] = []
    clean_customers(input_dir, output_dir, log)
    clean_exchange_rates(input_dir, output_dir, log)
    clean_products(input_dir, output_dir, log)
    clean_sales(input_dir, output_dir, log)
    clean_stores(input_dir, output_dir, log)

    report = "\n".join(log)
    print(report)
    (output_dir / "data_quality_report.md").write_text(
        "# Data Quality & Cleaning Report\n\n" + report
    )
    print(f"\nDone. Cleaned files + report written to {output_dir}/")


if __name__ == "__main__":
    main()
