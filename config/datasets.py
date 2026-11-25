"""Settings for building the master dataset from the raw CSV extracts.

Every CSV anywhere under RAW_DIR is one dataset. The dataset name is the filename,
lower-cased, with any trailing date removed, so these are the same dataset and are
appended together (the file that sorts last wins where periods overlap):

    imbalance/isem_niv_act_mwh.csv
    imbalance/isem_niv_act_mwh_2026-12-10.csv

The folder a file sits in is its group in the master dataset, e.g. "prices" or
"forecasts/fc_da". A dataset name must not appear in two folders.

The raw files are never changed: every rule below is applied in memory.
"""

START = "2022-02-01 00:00"   # UTC, first period kept
END = "2026-09-30 23:30"     # UTC, last period kept (None -> last timestamp in the data)
FREQ = "30min"
LOCAL_TZ = "Europe/Dublin"

# Columns placed straight after the time columns, in this order
FRONT = ["isem_pimb_act_eur_mwh", "isem_niv_act_mwh"]

# Order of the groups (folders) in the master dataset. Folders not listed go last.
GROUP_ORDER = [
    "imbalance",
    "prices",
    "generation and demand",
    "capacity",
    "interconnectors",
    "mcv_net",
    "mcv_by_unit/mcv_da",
    "mcv_by_unit/mcv_ida1",
    "mcv_by_unit/mcv_ida2",
    "mcv_by_unit/mcv_ida3",
    "forecasts/fc_da",
    "forecasts/fc_ida1",
    "forecasts/fc_ida2",
    "forecasts/fc_ida3",
    "commercial_offer_data",
]

DEFAULTS = {
    "timestamp_col": None,     # None -> "time_utc" if present, otherwise the first column
    "drop": ["dim_id", "tick"],  # columns ignored (tick = forecast arrival time, kept in the raw file)
    "source_tz": "UTC",        # time zone of the timestamps if they have no offset
    "dayfirst": False,         # True for dd/mm/yyyy dates
    "rename": None,            # {raw column: master column}; a file with one value column
                               # is otherwise named after the dataset automatically, and a
                               # file with several gets the dataset name as a prefix
    "hourly": False,           # hourly values: each hour also fills its :30 period, but
                               # only where the source has no :30 value of its own
    "ffill_limit": None,       # forward-fill up to N periods, for daily / weekly data
    "zero_as_missing": False,  # exact zeros are missing values at source
    "clip_min": None,          # values below this are set to this, e.g. 0 for solar
    "zero_from": None,         # UTC time from which missing values are 0 (unit retired)
    "empty_bands": False,      # offer bands with price 0 and quantity 0 set to missing
    "duplicates": "error",     # "match_next": keep the repeated row that matches the next period
}

# Rules for datasets that need something other than DEFAULTS.
# Keys can use * wildcards. Every matching key applies, in the order listed,
# so put general patterns first and specific names after them.
DATASETS = {
    # ---------------------------------------------------------------- imbalance
    # Exact 0.000 NIV appears in multi-hour runs while PIMB keeps moving:
    # missing values stored as zeros at source.
    "isem_niv_act_mwh": {"zero_as_missing": True},

    # ------------------------------------------------------------------- prices
    # Combined DA file: half-hourly price plus the market time unit (60 before Oct 2022).
    "isem_price_da_act_eur_mwh": {"rename": {"da_price_eur": "isem_price_da_act_eur_mwh",
                                             "da_mtu_min": "isem_price_da_mtu_min"}},

    # Hourly GB day-ahead prices: each hour's price applies to both half-hours.
    "gb_price_da_epex_act_gbp_mwh": {"hourly": True},
    "gb_price_da_n2ex_act_gbp_mwh": {"hourly": True},

    # Daily FX rate, held across the day.
    "fx_gbp_eur_act_rate": {"ffill_limit": 47},

    # NBP gas: day-ahead on working days (held over weekends and holidays, up to 4 days);
    # week-ahead weekly (held up to 7 days).
    "gb_gas_nbp_da_act_p_therm": {"ffill_limit": 191},
    "gb_gas_nbp_wa_act_p_therm": {"ffill_limit": 335},

    # ---------------------------------------------------- generation and demand
    # Solar: night-time readings of -1 to -5 MW and a bad block of -167 MW (22 Jul 2026).
    "isem_solar_act_mw": {"clip_min": 0},

    # ----------------------------------------------------------------- capacity
    # One reading of -0.77 MW (19 Nov 2022).
    "isem_cap_lignite_act_mw": {"clip_min": 0, "zero_from": "2023-12-31 23:00"},
    # Oil and lignite capacity series end with trading day 31 Dec 2023: 0 from then on.
    "isem_cap_oil_act_mw": {"zero_from": "2023-12-31 23:00"},
    # Capacity outturn has 9 missing days. Decision pending - to carry forward up to
    # 3 days, uncomment:
    # "isem_cap_*_act_mw": {"ffill_limit": 144},

    # ------------------------------------------------------------------ mcv_net
    # DA net position is hourly until 30 Sep 2025, half-hourly after.
    "*_mcv_da_net_act_mw": {"hourly": True},

    # -------------------------------------------------------------- mcv_by_unit
    # DA MCV is hourly throughout, including after the DA moved to 30 min.
    "isem_mcv_da_*_act_mw": {"hourly": True},

    # ---------------------------------------------------------------- forecasts
    # Hourly forecasts: Meteologica, capacity and interconnector availability.
    "*_meteologica_*_fc_*": {"hourly": True},
    "isem_cap_*_fc_*": {"hourly": True},
    "*_avail_fc_*": {"hourly": True},
    "isem_solar_eirgrid_fc_*": {"clip_min": 0},

    # ---------------------------------------------------- commercial_offer_data
    # Offer curves: unused bands are padded with 0/0.
    # Turlough Hill has stray second curves at some trading-day boundaries.
    "*_cod": {"empty_bands": True},
    "ie_turloughhill_cod": {"duplicates": "match_next"},
}


def settings(name):
    """Rules for one dataset: DEFAULTS, then every matching DATASETS entry in order."""
    from fnmatch import fnmatch
    cfg = dict(DEFAULTS)
    for pattern, rules in DATASETS.items():
        if fnmatch(name, pattern):
            cfg.update(rules)
    return cfg