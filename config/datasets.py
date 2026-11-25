"""Settings for building the master dataset.

Every CSV anywhere under RAW_DIR (including category subfolders such as outturn/)
is one dataset. The dataset name is the filename, lower-cased, with any trailing
date removed, so these are treated as the same dataset and appended together:

    outturn/ie_niv_outturn_mwh.csv
    outturn/ie_niv_outturn_mwh_2026-12-10.csv

Where extracts overlap, the file that sorts last (latest date) wins. A dataset
name must not appear in two different subfolders.
"""

START = "2022-02-01"   # UTC
END = None             # None -> last timestamp in the data
FREQ = "30min"

DEFAULTS = {
    "timestamp_col": None,     # None -> "time_utc" if present, otherwise the first column
    "drop": ["dim_id"],        # columns to ignore
    "source_tz": "UTC",        # timezone of the timestamps if they have no offset
    "dayfirst": False,         # True for dd/mm/yyyy dates
    "pivot": None,             # long-format data, e.g. {"columns": "interconnector", "values": "flow_mw"}
    "ffill_limit": None,       # forward-fill up to N periods, for hourly or daily data
    "zero_as_missing": False,  # treat exact zeros as missing values
    "rename": None,            # e.g. {"quantity": "ida3_mcv_au_mw"}; a lone "quantity"
                               # column is otherwise named after the dataset automatically
    "prefix": None,            # added to every value column, e.g. "th_"
    "empty_bands": False,      # offer bands with price 0 and quantity 0 set to missing
    "duplicates": "error",     # "match_next": keep the repeated row that matches the next period
}

# Only list datasets that need something other than DEFAULTS.
DATASETS = {
    # Exact 0.000 NIV appears in multi-hour runs while PIMB keeps moving:
    # missing values stored as zeros at source.
    "ie_niv_outturn_mwh": {"zero_as_missing": True},

    # Daily rate: one value per UTC day, held across all 48 half-hours.
    "eur_gbp_daily_fx_outturn_eur": {"ffill_limit": 47},

    # Hourly GB day-ahead prices: each hour's price applies to both half-hours.
    "gb_da_epex_outturn_gbp": {"ffill_limit": 1},
    "gb_da_n2ex_outturn_gbp": {"ffill_limit": 1},

    # NBP gas: day-ahead published on working days (held over weekends and
    # holidays, up to 4 days); week-ahead published weekly (held up to 7 days).
    "gb_da_nbp_outturn_gbp": {"ffill_limit": 191},
    "gb_week_nbp_outturn_gbp": {"ffill_limit": 335},

    # Offer curves: one prefix per unit; unused bands are padded with 0/0.
    # Turlough Hill has stray second curves at some trading-day boundaries.
    "ie_turloughhill_cod":  {"prefix": "th_", "empty_bands": True, "duplicates": "match_next"},
    "ie_ep_kilrootgt6_cod": {"prefix": "kgt6_", "empty_bands": True},
    "ie_ep_kilrootgt7_cod": {"prefix": "kgt7_", "empty_bands": True},

    # IDA3 only covers the 12 evening periods; the rest is blank by design.
    "13406_ie_ida3_mcv_au_mw": {"rename": {"quantity": "ida3_mcv_au_mw"}},

    # "pimb_niv":  {"timestamp_col": "start_time", "source_tz": "Europe/Dublin"},
    # "da_price":  {"ffill_limit": 1},     # hourly -> half-hourly
    # "gas_price": {"ffill_limit": 47},    # daily
    # "ic_flows":  {"pivot": {"columns": "interconnector", "values": "flow_mw"}},
}


def settings(name):
    return {**DEFAULTS, **DATASETS.get(name, {})}