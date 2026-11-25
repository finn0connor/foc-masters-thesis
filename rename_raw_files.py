"""Rename raw CSV extracts to the naming convention.

    python -m scripts.rename_raw_files            # dry run: shows what would change
    python -m scripts.rename_raw_files --apply    # renames the files

Searches every subfolder of RAW_DIR. Files with a date suffix
(e.g. ie_niv_outturn_mwh_2026-12-10.csv) keep their suffix.
"""

import argparse
import re

from config.paths import RAW_DIR

RENAMES = {
    "ie_pimb_outturn_eur": "isem_pimb_act_eur_mwh",
    "ie_niv_outturn_mwh": "isem_niv_act_mwh",
    "ie_da_semopx_outturn_eur": "isem_price_da_act_eur_mwh",
    "ie_ida1_semopx_outturn_eur": "isem_price_ida1_act_eur_mwh",
    "ie_ida2_semopx_outturn_eur": "isem_price_ida2_act_eur_mwh",
    "ie_ida3_semopx_outturn_eur": "isem_price_ida3_act_eur_mwh",
    "ie_gb_ewic_flow_outturn_mw": "isem_ewic_flow_act_mw",
    "ie_gb_ic_moyle_flow_outturn_mw": "isem_moyle_flow_act_mw",
    "ie_gb_greenlink_flow_outturn_mw": "isem_greenlink_flow_act_mw",
    "gb_da_epex_outturn_gbp": "gb_price_da_epex_act_gbp_mwh",
    "gb_da-hh_epex_outturn_gbp": "gb_price_dahh_epex_act_gbp_mwh",
    "gb_da_n2ex_outturn_gbp": "gb_price_da_n2ex_act_gbp_mwh",
    "gb_da_nbp_outturn_gbp": "gb_gas_nbp_da_act_p_therm",
    "gb_week_nbp_outturn_gbp": "gb_gas_nbp_wa_act_p_therm",
    "eur_gbp_daily_fx_outturn_eur": "fx_gbp_eur_act_rate",
}

DATE_SUFFIX = re.compile(r"^(?P<base>.+?)(?P<suffix>[_\- ]\d{4}-\d{2}-\d{2})?$")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="rename the files (default: dry run)")
    args = parser.parse_args()

    planned, problems = [], []
    for path in sorted(RAW_DIR.rglob("*.csv")):
        m = DATE_SUFFIX.match(path.stem)
        base, suffix = m["base"], m["suffix"] or ""
        if base not in RENAMES:
            continue
        target = path.with_name(f"{RENAMES[base]}{suffix}.csv")
        if target.exists():
            problems.append(f"  target already exists, skipped: {target.relative_to(RAW_DIR)}")
            continue
        planned.append((path, target))

    if not planned and not problems:
        print(f"Nothing to rename in {RAW_DIR}")
        return

    print(f"{'Renaming' if args.apply else 'Would rename'} {len(planned)} file(s) in {RAW_DIR}:")
    for src, dst in planned:
        print(f"  {src.relative_to(RAW_DIR)}  ->  {dst.name}")
        if args.apply:
            src.rename(dst)
    for p in problems:
        print(p)

    if not args.apply:
        print("\nDry run only. Run again with --apply to rename.")


if __name__ == "__main__":
    main()