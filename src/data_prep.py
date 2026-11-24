"""Build the master dataset from the raw CSV extracts.

    python -m src.data_prep            # writes master.parquet and master.csv
    python -m src.data_prep --no-csv   # parquet only
"""

import argparse
import re
from collections import defaultdict

import pandas as pd

from config.datasets import END, FREQ, START, settings
from config.paths import PROCESSED_DIR, RAW_DIR

DATE_SUFFIX = re.compile(r"[_\- ]\d{4}-\d{2}-\d{2}$")


def snake(name):
    return re.sub(r"[^0-9a-zA-Z]+", "_", str(name)).strip("_").lower()


def dataset_name(path):
    return snake(DATE_SUFFIX.sub("", path.stem))


def parse_timestamps(series, cfg):
    ts = pd.to_datetime(series, dayfirst=cfg["dayfirst"])
    if ts.dtype == object:  # mixed UTC offsets, e.g. +00:00 and +01:00
        ts = pd.to_datetime(series, dayfirst=cfg["dayfirst"], utc=True)
    if ts.dt.tz is not None:
        return ts.dt.tz_convert("UTC")
    if cfg["source_tz"] == "UTC":
        return ts.dt.tz_localize("UTC")
    try:
        return ts.dt.tz_localize(
            cfg["source_tz"], ambiguous="infer", nonexistent="shift_forward"
        ).dt.tz_convert("UTC")
    except Exception as err:
        raise ValueError(
            f"Could not resolve clock-change hours in {cfg['source_tz']} local time. "
            "Export timestamps in UTC or with a UTC offset instead."
        ) from err


def load_file(path, cfg):
    df = pd.read_csv(path)
    ts_col = cfg["timestamp_col"] or df.columns[0]
    ts = parse_timestamps(df[ts_col], cfg)
    df = df.drop(columns=[ts_col])
    df.columns = [snake(c) for c in df.columns]
    df.insert(0, "ts_utc", ts)

    if cfg["pivot"]:
        cols, vals = snake(cfg["pivot"]["columns"]), snake(cfg["pivot"]["values"])
        df = df.pivot_table(index="ts_utc", columns=cols, values=vals, aggfunc="last")
        df.columns = [f"{snake(c)}_{vals}" for c in df.columns]
        df = df.reset_index()
    else:
        df = df.drop_duplicates()
        if df["ts_utc"].duplicated().any():
            raise ValueError(
                f"{path.name} has repeated timestamps with different values, so it looks like "
                "long-format data. Add a 'pivot' entry for it in config/datasets.py."
            )

    if cfg["zero_as_missing"]:
        value_cols = df.columns.drop("ts_utc")
        zeros = int((df[value_cols] == 0).sum().sum())
        df[value_cols] = df[value_cols].mask(df[value_cols] == 0)
        print(f"    {path.name}: {zeros} exact zeros set to missing")
    return df


def build_dataset(name, files):
    cfg = settings(name)
    frames = [load_file(f, cfg) for f in sorted(files)]
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset="ts_utc", keep="last")
    return df.set_index("ts_utc").sort_index()


def build_master():
    files = defaultdict(list)
    for path in RAW_DIR.rglob("*.csv"):
        files[dataset_name(path)].append(path)
    if not files:
        raise FileNotFoundError(f"No CSV files found in {RAW_DIR}")
    for name, paths in files.items():
        folders = {p.parent for p in paths}
        if len(folders) > 1:
            raise ValueError(
                f"Dataset '{name}' appears in more than one folder: "
                + ", ".join(str(f.relative_to(RAW_DIR)) for f in sorted(folders))
                + ". Rename one so each dataset name is unique."
            )

    master = None
    columns_by_dataset = {}
    for name in sorted(files):
        df = build_dataset(name, files[name])
        if master is not None:
            clashes = master.columns.intersection(df.columns)
            df = df.rename(columns={c: f"{name}_{c}" for c in clashes})
        columns_by_dataset[name] = list(df.columns)
        master = df if master is None else master.join(df, how="outer")
        folder = files[name][0].parent.relative_to(RAW_DIR)
        print(f"  {folder}/{name}: {len(files[name])} file(s), {len(df):,} rows, "
              f"{len(df.columns)} columns")

    start = pd.Timestamp(START, tz="UTC") if START else master.index.min()
    end = pd.Timestamp(END, tz="UTC") if END else master.index.max()
    grid = pd.date_range(start.ceil(FREQ), end, freq=FREQ, name="ts_utc")

    off_grid = master.index.difference(grid)
    off_grid = off_grid[(off_grid >= start) & (off_grid <= end)]
    if len(off_grid):
        print(f"  warning: {len(off_grid)} timestamps not on the {FREQ} grid were dropped, "
              f"e.g. {off_grid[0]}")
    master = master.reindex(grid)

    for name, cols in columns_by_dataset.items():
        limit = settings(name)["ffill_limit"]
        if limit:
            master[cols] = master[cols].ffill(limit=limit)

    master.insert(0, "ts_local", master.index.tz_convert("Europe/Dublin"))
    return master.reset_index()


def report(master):
    print(f"\n  {len(master):,} periods, {master['ts_utc'].min()} to {master['ts_utc'].max()}")
    print(f"  {'column':<40}{'coverage':>10}  first valid")
    for col in master.columns[2:]:
        valid = master[col].notna()
        first = master.loc[valid, "ts_utc"].min() if valid.any() else "-"
        print(f"  {col:<40}{valid.mean():>9.1%}  {first}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-csv", action="store_true", help="skip writing master.csv")
    args = parser.parse_args()

    print(f"Reading CSVs from {RAW_DIR}")
    master = build_master()
    report(master)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    master.to_parquet(PROCESSED_DIR / "master.parquet", index=False)
    if not args.no_csv:
        master.to_csv(PROCESSED_DIR / "master.csv", index=False)
    print(f"\nSaved to {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
