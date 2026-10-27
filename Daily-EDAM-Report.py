'''
This script pulls data off of caiso.com/documents/daily-extended-day-ahead-market-edam-report. 
A data range can be specified to generate an excel spreadsheet of transfers per hour end per each region.
'''

# ---------------- Imports ----------------------- #
import requests
import re
import pandas as pd
import ast
import os
from datetime import datetime, timedelta
from supabase import create_client, Client

# ---------------- Supabase ----------------------- #
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- Functions ----------------------- #
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
    records = final_df.to_dict(orient="records")
    response = supabase.table("edam_transfers").upsert(
        records, 
        on_conflict="date,he,product,ba"
    ).execute()
    
    print(f"Successfully synced {len(records)} records to Supabase!")
else:
    print("No data collected for this period.")

