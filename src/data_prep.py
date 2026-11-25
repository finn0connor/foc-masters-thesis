"""Build the master dataset from the raw CSV extracts.

    python -m src.data_prep            # writes master.parquet, master.csv, master_columns.csv
    python -m src.data_prep --no-csv   # skip master.csv

The raw CSVs in RAW_DIR are only read, never changed. Every run builds the master
dataset from scratch:

  1. every CSV under RAW_DIR is read; its folder is its group
  2. dataset rules from config/datasets.py are applied in memory
  3. 15-minute data is averaged to 30 minutes, hourly data is spread onto both
     half-hours, daily and weekly data is carried forward
  4. everything is joined on one half-hourly UTC timeline

Output, in PROCESSED_DIR:
  master.parquet        the dataset used by the code
  master.csv            the same, for checking in Excel
  master_columns.csv    one row per column: group, source file, dim_id, resolution, coverage

Columns are: time_utc, time_ist, trading_day, then PIMB and NIV, then each group in
GROUP_ORDER. Column names are flat (no multi-level header); use master_columns.csv
to select a group, e.g.

    cols = pd.read_csv(".../master_columns.csv")
    wind_fc_da = cols.loc[cols.group == "forecasts/fc_da", "column"]
"""

import argparse
import re
from collections import defaultdict

import pandas as pd

from config.datasets import END, FREQ, FRONT, GROUP_ORDER, LOCAL_TZ, START, settings
from config.paths import PROCESSED_DIR, RAW_DIR

DATE_SUFFIX = re.compile(r"[_\- ]\d{4}-\d{2}-\d{2}$")
BAND = re.compile(r"^(.*)price(\d+)$")
STEP = pd.Timedelta(FREQ)


# ============================================================================
# Names and timestamps
# ============================================================================
def snake(name):
    return re.sub(r"[^0-9a-zA-Z]+", "_", str(name)).strip("_").lower()


def dataset_name(path):
    return snake(DATE_SUFFIX.sub("", path.stem))


def group_name(path):
    return path.parent.relative_to(RAW_DIR).as_posix()


def parse_timestamps(series, cfg):
    ts = pd.to_datetime(series, dayfirst=cfg["dayfirst"], format="mixed")
    if ts.dtype == object:  # mixed UTC offsets, e.g. +00:00 and +01:00
        ts = pd.to_datetime(series, dayfirst=cfg["dayfirst"], format="mixed", utc=True)
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


def native_step(index):
    """Most common spacing between timestamps, e.g. '15min', '1h', '1D'."""
    if len(index) < 2:
        return ""
    minutes = int(pd.Series(index).diff().mode().iloc[0].total_seconds() // 60)
    if minutes % 1440 == 0:
        return f"{minutes // 1440}D"
    return f"{minutes}min"


# ============================================================================
# Cleaning rules (all in memory)
# ============================================================================
def resolve_duplicates(df, path):
    """For a repeated timestamp, keep the row that matches the following period."""
    dup = df.index.duplicated(keep=False)
    unique = df[~dup]
    keep = []
    for t, group in df[dup].groupby(level=0):
        match = group.iloc[[-1]]
        nxt = t + STEP
        if nxt in unique.index:
            target = unique.loc[nxt].to_numpy()
            for i in range(len(group)):
                if (group.iloc[i].to_numpy() == target).all():
                    match = group.iloc[[i]]
                    break
        keep.append(match)
    print(f"      {path.name}: {dup.sum() - len(keep)} conflicting duplicate rows resolved")
    return pd.concat([unique, *keep]).sort_index()


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
    print(f"      {path.name}: {cleared} empty offer bands set to missing")
    return df


def to_half_hourly(df, path):
    """Average anything finer than 30 minutes onto the 30-minute grid."""
    t = df.index
    if ((t.minute % 30 != 0) | (t.second != 0)).any():
        df = df.resample(FREQ, label="left", closed="left").mean()
        print(f"      {path.name}: averaged from {native_step(t)} to {FREQ}")
    return df


def hourly_to_half_hourly(df):
    """Copy each hour's value onto its :30 period where the source has none."""
    on_hour = df[df.index.minute == 0]
    half = on_hour.copy()
    half.index = half.index + STEP
    half = half[~half.index.isin(df.index)]
    return pd.concat([df, half]).sort_index()


# ============================================================================
# Loading
# ============================================================================
def load_file(path, cfg, name):
    df = pd.read_csv(path)
    df = df.drop(columns=[c for c in cfg["drop"] if c in df.columns])
    ts_col = cfg["timestamp_col"] or ("time_utc" if "time_utc" in df.columns else df.columns[0])
    df.index = pd.DatetimeIndex(parse_timestamps(df[ts_col], cfg), name="time_utc")
    df = df.drop(columns=[ts_col])
    df.columns = [snake(c) for c in df.columns]

    df = df.reset_index().drop_duplicates().set_index("time_utc")
    if df.index.duplicated().any():
        if cfg["duplicates"] == "match_next":
            df = resolve_duplicates(df, path)
        else:
            raise ValueError(
                f"{path.name} has repeated timestamps with different values. If the repeats "
                "are stray resubmissions, add 'duplicates': 'match_next' for it in "
                "config/datasets.py."
            )

    if cfg["zero_as_missing"]:
        zeros = int((df == 0).sum().sum())
        df = df.mask(df == 0)
        print(f"      {path.name}: {zeros} exact zeros set to missing")
    if cfg["empty_bands"]:
        df = clear_empty_bands(df, path)
    if cfg["clip_min"] is not None:
        low = int((df < cfg["clip_min"]).sum().sum())
        df = df.clip(lower=cfg["clip_min"])
        if low:
            print(f"      {path.name}: {low} values below {cfg['clip_min']} raised to {cfg['clip_min']}")

    step = native_step(df.index)
    df = to_half_hourly(df, path)
    if cfg["hourly"]:
        df = hourly_to_half_hourly(df)

    # Column names: one value column takes the dataset name; several get it as a prefix
    if cfg["rename"]:
        df = df.rename(columns={snake(k): v for k, v in cfg["rename"].items()})
    elif len(df.columns) == 1:
        df.columns = [name]
    else:
        df.columns = [f"{name}_{c}" for c in df.columns]
    return df, step


def first_dim_id(path):
    try:
        ids = pd.read_csv(path, usecols=["dim_id"], nrows=1)["dim_id"]
        return int(ids.iloc[0]) if len(ids) else None
    except ValueError:
        return None


def build_dataset(name, paths):
    cfg = settings(name)
    frames, steps = [], []
    for p in sorted(paths):
        try:
            df, step = load_file(p, cfg, name)
        except Exception as err:
            raise RuntimeError(f"Problem reading {p.name}: {err}") from err
        frames.append(df)
        steps.append(step)
    df = pd.concat(frames)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df, steps[-1]


# ============================================================================
# Master dataset
# ============================================================================
def find_files():
    files = defaultdict(list)
    for path in RAW_DIR.rglob("*.csv"):
        files[dataset_name(path)].append(path)
    if not files:
        raise FileNotFoundError(f"No CSV files found in {RAW_DIR}")
    for name, paths in files.items():
        groups = {group_name(p) for p in paths}
        if len(groups) > 1:
            raise ValueError(f"Dataset '{name}' appears in more than one folder: "
                             f"{', '.join(sorted(groups))}. Each dataset name must be unique.")
    return files


def group_rank(group):
    return (GROUP_ORDER.index(group), group) if group in GROUP_ORDER else (len(GROUP_ORDER), group)


def build_master():
    files = find_files()
    start = pd.Timestamp(START, tz="UTC")
    end = pd.Timestamp(END, tz="UTC") if END else None

    datasets, info, current = [], [], None
    for name in sorted(files, key=lambda n: (group_rank(group_name(files[n][0])), n)):
        paths = files[name]
        group = group_name(paths[0])
        if group != current:
            n = sum(group_name(p[0]) == group for p in files.values())
            print(f"  [{group}] {n} dataset(s)")
            current = group
        df, step = build_dataset(name, paths)
        datasets.append((name, df))
        for col in df.columns:
            info.append({"column": col, "group": group, "dataset": name,
                         "dim_id": first_dim_id(paths[0]), "source_resolution": step,
                         "files": len(paths)})

    columns = [c for _, df in datasets for c in df.columns]
    clashes = sorted({c for c in columns if columns.count(c) > 1})
    if clashes:
        raise ValueError(f"Column names used by more than one dataset: {clashes}")

    end = end or max(df.index.max() for _, df in datasets)
    grid = pd.date_range(start, end, freq=FREQ, name="time_utc")

    parts = []
    for name, df in datasets:
        off_grid = df.index[(df.index >= start) & (df.index <= end)].difference(grid)
        if len(off_grid):
            print(f"  warning: {name}: {len(off_grid)} timestamps off the {FREQ} grid dropped, "
                  f"e.g. {off_grid[0]}")
        df = df.reindex(grid)
        cfg = settings(name)
        if cfg["ffill_limit"]:
            df = df.ffill(limit=cfg["ffill_limit"])
        if cfg["zero_from"]:
            later = df.index >= pd.Timestamp(cfg["zero_from"], tz="UTC")
            filled = int(df.loc[later].isna().sum().sum())
            df.loc[later] = df.loc[later].fillna(0)
            print(f"  {name}: {filled} missing values from {cfg['zero_from']} set to 0")
        parts.append(df)

    master = pd.concat(parts, axis=1).copy()

    # Column order: PIMB and NIV first, then groups in GROUP_ORDER
    front = [c for c in FRONT if c in master.columns]
    master = master[front + [c for c in master.columns if c not in front]]

    local = master.index.tz_convert(LOCAL_TZ)
    master.insert(0, "time_ist", local)
    master.insert(1, "trading_day", (local + pd.Timedelta(hours=1)).date)  # 23:00 D-1 to 23:00 D
    master = master.reset_index()

    info = pd.DataFrame(info).set_index("column").reindex(master.columns[3:])
    info.index.name = "column"
    info["dim_id"] = info["dim_id"].astype("Int64")
    valid = master[info.index].notna()
    info["coverage"] = valid.mean().round(4)
    info["first_valid"] = [master.loc[valid[c], "time_utc"].min() if valid[c].any() else None
                           for c in info.index]
    info["last_valid"] = [master.loc[valid[c], "time_utc"].max() if valid[c].any() else None
                          for c in info.index]
    return master, info.reset_index()


def report(master, info):
    print(f"\n  {len(master):,} periods, {master['time_utc'].min()} to {master['time_utc'].max()}, "
          f"{len(info)} data columns")
    for group, rows in info.groupby("group", sort=False):
        print(f"\n  [{group}]")
        for r in rows.itertuples():
            first = str(r.first_valid)[:16] if r.first_valid is not None else "-"
            print(f"    {r.column:<48}{r.coverage:>8.1%}  from {first}  ({r.source_resolution})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-csv", action="store_true", help="skip writing master.csv")
    args = parser.parse_args()

    print(f"Reading CSVs from {RAW_DIR}")
    master, info = build_master()
    report(master, info)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    master.to_parquet(PROCESSED_DIR / "master.parquet", index=False)
    info.to_csv(PROCESSED_DIR / "master_columns.csv", index=False)
    if not args.no_csv:
        master.to_csv(PROCESSED_DIR / "master.csv", index=False)
    print(f"\nSaved to {PROCESSED_DIR}")


if __name__ == "__main__":
    main()