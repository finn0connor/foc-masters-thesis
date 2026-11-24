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
    "timestamp_col": None,     # None -> first column in the CSV
    "source_tz": "UTC",        # timezone of the timestamps if they have no offset
    "dayfirst": False,         # True for dd/mm/yyyy dates
    "pivot": None,             # long-format data, e.g. {"columns": "interconnector", "values": "flow_mw"}
    "ffill_limit": None,       # forward-fill up to N periods, for hourly or daily data
    "zero_as_missing": False,  # treat exact zeros as missing values
}

# Only list datasets that need something other than DEFAULTS.
DATASETS = {
    # Exact 0.000 NIV appears in multi-hour runs while PIMB keeps moving:
    # missing values stored as zeros at source.
    "ie_niv_outturn_mwh": {"zero_as_missing": True},

    # "pimb_niv":  {"timestamp_col": "start_time", "source_tz": "Europe/Dublin"},
    # "da_price":  {"ffill_limit": 1},     # hourly -> half-hourly
    # "gas_price": {"ffill_limit": 47},    # daily
    # "ic_flows":  {"pivot": {"columns": "interconnector", "values": "flow_mw"}},
}


def settings(name):
    return {**DEFAULTS, **DATASETS.get(name, {})}
