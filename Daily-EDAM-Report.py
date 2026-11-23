'''
This script pulls data off of caiso.com/documents/daily-extended-day-ahead-market-edam-report. 
Each run scrapes the past 7 days and merges them into monthly CSVs at data/YYYY-MM.csv.
'''

# ---------------- Imports ----------------------- #
import requests
import re
import pandas as pd
import ast
import os
from datetime import datetime, timedelta

# ---------------- Output ----------------------- #
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
KEY_COLS = ["date", "he", "product", "ba"]

# ---------------- Functions ----------------------- #
def save_monthly(df):
    '''Merge rows into data/YYYY-MM.csv files, one per month. Re-scraped rows replace older ones.'''
    os.makedirs(DATA_DIR, exist_ok=True)
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y")

    for month, month_df in df.groupby(df["date"].dt.to_period("M")):
        path = os.path.join(DATA_DIR, f"{month}.csv")
        if os.path.exists(path):
            existing = pd.read_csv(path, parse_dates=["date"])
            month_df = pd.concat([existing, month_df], ignore_index=True)
        month_df = (month_df.drop_duplicates(subset=KEY_COLS, keep="last")
                            .sort_values(["date", "ba", "product", "he"]))
        month_df.to_csv(path, index=False, date_format="%Y-%m-%d")
        print(f"Wrote {len(month_df)} rows to {path}")

def process_day(date_obj):
    # Retrieve information from CAISO website on Transfers Bar Charts
    url_date = date_obj.strftime("%b-%d-%Y").lower()
    url = f"https://www.caiso.com/documents/daily-extended-day-ahead-market-edam-report-{url_date}.html"
    res = requests.get(url).text

    start = res.find("<!-- JSBlock Variables -->")
    end = res.find("<!-- colors -->")
    if start == -1 or end == -1:
        raise Exception(f"{date_obj} Block not found")

    block = res[start:end]
    pattern = r"(tsr_xfer[\w_]+)\s*=\s*(\[[^\]]+\])"
    matches = re.findall(pattern, block, re.DOTALL)


    # Extract data from website to dataframe
    df = pd.DataFrame(matches, columns = ["Variable", "Value"])
    df = df[~df["Variable"].str.startswith('tsr_xfer_ruc_total_energy')] # Remove this variable not shown on graph
    df["Value"] = df["Value"].apply(ast.literal_eval) 
    df["BA"] = df["Variable"].str.extract(r"(ciso|pace|pacw|pge)", expand=False).str.upper()


    # Function to convert list format into long format
    def extract_product(var, ba):
        var = var.replace("tsr_xfer_ifm_total", "").replace("tsr_xfer_ruc_total", "") # strip beginning
        var = var[: -len(ba)]  # strip ending "pace", "ciso", etc.
        var = var.replace("_", " ").strip()
        return var
    
    df["product"] = df.apply(lambda x: extract_product(x["Variable"], x["BA"]), axis=1)

    rows = []
    for _, row in df.iterrows():
        for i, val in enumerate(row["Value"]):
            try:
                numeric_val = float(val)
            except (ValueError, TypeError):
                continue
            rows.append({
                "date": date_obj.strftime("%m/%d/%Y"),
                "he": i + 1,
                "product": row["product"],
                "ba": row["BA"],
                "value": numeric_val
            })

    return pd.DataFrame(rows)

# ---------------- Script Start ----------------------- #
if __name__ == "__main__":

    end_date = datetime.now().date() - timedelta(days=1)
    start_date = end_date - timedelta(days=6)

    print(f"Scraping EDAM data from {start_date} to {end_date}...")

    all_days = []

    current = start_date
    while current <= end_date:
        try:
            day_df = process_day(current)

            if not day_df.empty:
                all_days.append(day_df)
        except Exception as e:
            print(f"Skipping {current}: {e}")

        current += timedelta(days=1)

    if all_days:
        final_df = pd.concat(all_days, ignore_index=True)
        save_monthly(final_df)
        print(f"Successfully saved {len(final_df)} scraped records!")
    else:
        print("No data collected for this period.")
