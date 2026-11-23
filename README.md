# EDAM Transfers Scraper

Collects hourly **EDAM transfer** data from CAISO's
[Daily Extended Day-Ahead Market (EDAM) Report](https://www.caiso.com/documents/daily-extended-day-ahead-market-edam-report)
and stores it as monthly CSV files in this repo.

## How it works

1. Every **Monday at 6:00 AM UTC**, a GitHub Action ([`.github/workflows/scrape.yml`](.github/workflows/scrape.yml)) runs [`Daily-EDAM-Report.py`](Daily-EDAM-Report.py).
2. The script fetches the daily report page for each of the **previous 7 days** and extracts the transfer bar-chart data embedded in the page.
3. The rows are merged into `data/YYYY-MM.csv`, one file per month. A week that spans two months updates both files.
4. The Action commits any changed CSVs back to the repo.

Re-scraping a day replaces its existing rows rather than duplicating them. Rows are unique on `date, he, product, ba`. If a day's report isn't published, that day is skipped and logged.

## Data

Files: `data/2026-05.csv`, `data/2026-06.csv`, … Data starts May 1, 2026.

| Column    | Description                                                   |
|-----------|---------------------------------------------------------------|
| `date`    | Trade date, `YYYY-MM-DD`                                      |
| `he`      | Hour ending, 1–24 (25 on the fall daylight-saving day)        |
| `product` | Transfer product (see below)                                  |
| `ba`      | Balancing area: `CISO`, `PACE`, `PACW`, `PGE` (PGE from Oct 2026) |
| `value`   | Transfer quantity (MW)                                        |

Products, each with an `e` (export) and `i` (import) variant:

| Product  | Meaning                         |
|----------|---------------------------------|
| `energy` | Energy transfers                |
| `iru` / `ird` | Imbalance reserve up / down |
| `rcu` / `rcd` | Reliability capacity up / down |

