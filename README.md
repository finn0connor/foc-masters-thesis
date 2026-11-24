# foc-masters-thesis

**Sensitivity Analysis of Rare Events in Engineering Systems**

Forecasting Irish imbalance prices (PIMB) in the I-SEM, with sensitivity analysis applied at each stage of model development to identify what drives price spikes.

---

## How the project is split

The project lives in two places:

| Where | What | Backed up by |
|---|---|---|
| This repo (cloned locally) | Code, notebooks, config, notes | GitHub |
| OneDrive `MAI Project\thesis-data\` | Raw CSV extracts and the processed master table | OneDrive |

Data is never committed to the repo. The code finds the data through `config/paths.py`.

---

## Repo layout

```
foc-masters-thesis/
├── config/
│   ├── paths.py             # where the data lives (OneDrive)
│   ├── datasets.py          # per-dataset cleaning rules
│   ├── decision_points.py   # DA / IDA1 cutoffs and forecast vintages
│   └── groups.py            # feature groups for sensitivity analysis
├── src/
│   ├── data_prep.py         # raw CSVs -> master.parquet
│   ├── features.py          # master + decision point -> X, y
│   ├── spikes.py            # spike labels from PIMB-DA spread tails
│   ├── training.py          # shared train/val/test split and fit loop
│   ├── evaluation.py        # shared metrics, incl. spike-period error
│   ├── pricing_mechanism.py # bottom-up imbalance price recreation
│   ├── models/              # one file per model family
│   └── sensitivity/         # Morris, Sobol, EVT, rare-event methods
├── notebooks/               # one notebook per model
├── notes/                   # research notes
├── reports/                 # interim and final reports
├── outputs/                 # figures, tables, saved models (not committed)
├── requirements.txt
└── setup.bat
```

## Data layout (OneDrive)

```
MAI Project\thesis-data\
├── individual_csvs\         # raw SQL extracts, one CSV per dataset - never edit these
│   ├── outturn\
│   ├── forecasts\
│   └── ...
└── processed\
    ├── master.parquet       # built by data_prep.py
    └── master.csv
```

---

## Workflow

### 1. Start of a session (lab PC)

```bat
cd C:\Users\FOCONNO1
git clone https://github.com/finn0connor/foc-masters-thesis.git
cd foc-masters-thesis
setup.bat
```

If the repo is already on this PC, run `git pull` instead of cloning.

Activate the environment each time you open a new terminal:

```bat
.venv\Scripts\activate
```

In OneDrive, right-click `thesis-data` and choose **Always keep on this device** so the files load quickly.

### 2. Adding new data

1. Run the SQL query at work and export one CSV per dataset.
2. Zip and email to yourself.
3. Unzip into the right subfolder of `thesis-data\individual_csvs\`.

Rules:

- One CSV = one dataset. The dataset name is the filename.
- Timestamps go in the first column, in UTC.
- Put units in column names, e.g. `pimb_eur`, `niv_mwh`, `wind_fc_da_mw`.
- A newer extract of the same dataset can be added with a date at the end, e.g. `ie_niv_outturn_mwh_2026-12-10.csv`. It is appended, and the newer file wins where periods overlap.
- The same filename must not appear in two subfolders.

### 3. Building the master table

From the repo root:

```bat
python -m src.data_prep
```

This reads every CSV under `individual_csvs\`, puts everything on one half-hourly UTC timeline, and writes `master.parquet` and `master.csv` to `processed\`. It prints the coverage of each column.

Add `--no-csv` to write the Parquet file only.

Always run from the repo root with `python -m`, otherwise the `config` imports fail.

### 4. Cleaning rules

All cleaning happens in `src/data_prep.py`, driven by `config/datasets.py`. The raw CSVs are never edited, so the master table can always be rebuilt.

A dataset only needs an entry in `config/datasets.py` if it is not standard:

| Setting | Use when |
|---|---|
| `timestamp_col` | The timestamp is not the first column |
| `source_tz` | Timestamps are in local time, not UTC |
| `dayfirst` | Dates are dd/mm/yyyy |
| `ffill_limit` | Hourly or daily data that should be filled onto half-hours |
| `pivot` | Several rows per timestamp, e.g. one row per interconnector |
| `zero_as_missing` | Exact zeros are missing values at source |

Applied automatically to every dataset:

- Exact duplicate rows are removed.
- Missing periods are left blank. They are never interpolated or dropped.
- Clock-change days are kept.

Dataset-specific decisions:

| Dataset | Rule | Reason |
|---|---|---|
| `ie_niv_outturn_mwh` | Exact zeros set to missing | NIV is reported to 3 decimals; exact 0.000 appears in multi-hour runs while PIMB keeps moving |

Known source issues:

- PIMB and NIV share 299 missing periods (71 gaps, longest 29 periods on 11-12 May 2026).
- Exact-zero PIMB values (~4%) are genuine: they occur when the system is long and increase each year with wind.

### 5. Modelling

Each model has its own notebook in `notebooks/`, with the model itself defined in `src/models/`. Every notebook follows the same sections:

1. **Setup** - choose the decision point (DA or IDA1), load X and y via `features.py`
2. **Model definition** - import from `src/models/`, set hyperparameters
3. **Train** - via `training.py`
4. **Test** - via `evaluation.py`, overall and on spike periods
5. **Sensitivity analysis** - via `src/sensitivity/`
6. **Save** - results to `outputs/`

All models share the same data split, metrics and sensitivity analysis, so the only thing that changes between notebooks is the model. `07_model_comparison.ipynb` loads the saved results and compares them.

### 6. End of a session

```bat
git add .
git commit -m "describe what changed"
git push
```

Lab PCs may wipe local files at logout, so anything not pushed is lost. Push half-finished work to a `wip` branch rather than leaving it uncommitted.

---

## Order of work

1. `data_prep.py` - done
2. Add forecast, price and interconnector datasets
3. `decision_points.py`, `features.py`
4. `spikes.py`, `00_data_overview.ipynb`
5. Models, from baselines through to neural networks
6. Sensitivity analysis on each model
7. Model comparison
