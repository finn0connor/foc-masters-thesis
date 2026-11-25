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


BAND = re.compile(r"^(.*)price(\d+)$")
GENERIC_VALUE_COLS = {"quantity", "value"}


def resolve_duplicates(df, path):
    """For a repeated timestamp, keep the row that matches the following period."""
    dup = df["time_utc"].duplicated(keep=False)
    values = df.columns.drop("time_utc")
    unique = df[~dup].set_index("time_utc")[values]
    keep = []
    for t, group in df[dup].groupby("time_utc"):
        nxt = t + pd.Timedelta(FREQ)
        match = group.index[-1]
        if nxt in unique.index:
            target = unique.loc[nxt].to_numpy()
            for i, row in group[values].iterrows():
                if (row.to_numpy() == target).all():
                    match = i
                    break
        keep.append(match)
    print(f"    {path.name}: {dup.sum() - len(keep)} conflicting duplicate rows resolved")
    return pd.concat([df[~dup], df.loc[keep]]).sort_values("time_utc")


def clear_empty_bands(df, path):
    """Offer bands with price 0 and quantity 0 are unused padding, not real offers."""
    cleared = 0
    for col in df.columns:
        m = BAND.match(col)
        qty = f"{m.group(1)}quantity{m.group(2)}" if m else None
        if qty in df.columns:
            empty = (df[col] == 0) & (df[qty] == 0)
            df.loc[empty, [col, qty]] = float("nan")
            cleared += int(empty.sum())
    print(f"    {path.name}: {cleared} empty offer bands set to missing")
    return df


def load_file(path, cfg, name):
    df = pd.read_csv(path)
    df = df.drop(columns=[c for c in cfg["drop"] if c in df.columns])
    ts_col = cfg["timestamp_col"] or ("time_utc" if "time_utc" in df.columns else df.columns[0])
    ts = parse_timestamps(df[ts_col], cfg)
    df = df.drop(columns=[ts_col])
    df.columns = [snake(c) for c in df.columns]
    if cfg["rename"]:
        df = df.rename(columns={snake(k): v for k, v in cfg["rename"].items()})
    if len(df.columns) == 1 and df.columns[0] in GENERIC_VALUE_COLS:
        df.columns = [name]  # a single generic value column takes the dataset name
    df.insert(0, "time_utc", ts)

    if cfg["pivot"]:
        cols, vals = snake(cfg["pivot"]["columns"]), snake(cfg["pivot"]["values"])
        df = df.pivot_table(index="time_utc", columns=cols, values=vals, aggfunc="last")
        df.columns = [f"{snake(c)}_{vals}" for c in df.columns]
        df = df.reset_index()
    else:
        df = df.drop_duplicates()
        if df["time_utc"].duplicated().any():
            if cfg["duplicates"] == "match_next":
                df = resolve_duplicates(df, path)
            else:
                raise ValueError(
                    f"{path.name} has repeated timestamps with different values. If it is "
                    "long-format data, add a 'pivot' entry for it in config/datasets.py; if "
                    "the repeats are stray resubmissions, add 'duplicates': 'match_next'."
                )

    if cfg["zero_as_missing"]:
        value_cols = df.columns.drop("time_utc")
        zeros = int((df[value_cols] == 0).sum().sum())
        df[value_cols] = df[value_cols].mask(df[value_cols] == 0)
        print(f"    {path.name}: {zeros} exact zeros set to missing")
    if cfg["empty_bands"]:
        df = clear_empty_bands(df, path)
    if cfg["prefix"]:
        df = df.rename(columns={c: f"{cfg['prefix']}{c}" for c in df.columns if c != "time_utc"})
    return df


def build_dataset(name, files):
    cfg = settings(name)
    frames = []
    for f in sorted(files):
        try:
            frames.append(load_file(f, cfg, name))
        except Exception as err:
            raise RuntimeError(f"Problem reading {f.name}: {err}") from err
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset="time_utc", keep="last")
    return df.set_index("time_utc").sort_index()


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
    grid = pd.date_range(start.ceil(FREQ), end, freq=FREQ, name="time_utc")

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

    master.insert(0, "time_ist", master.index.tz_convert("Europe/Dublin"))
    return master.reset_index()


def report(master):
    print(f"\n  {len(master):,} periods, {master['time_utc'].min()} to {master['time_utc'].max()}")
    print(f"  {'column':<40}{'coverage':>10}  first valid")
    for col in master.columns[2:]:
        valid = master[col].notna()
        first = master.loc[valid, "time_utc"].min() if valid.any() else "-"
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