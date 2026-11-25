# Decision Points and Data Availability

## Decision points

Each decision point is set **45 minutes before the auction's gate closure**, to allow time to act on the forecast.

| Auction | Gate closure (Irish time) | Decision point (Irish time) | Periods covered (Irish time) | Notes |
|---|---|---|---|---|
| DA   | 11:00 D-1 | **10:15 D-1** | Full trading day (23:00–23:00) | Forecast before the day-ahead auction |
| IDA1 | 17:30 D-1 | **16:45 D-1** | Full trading day (23:00–23:00) | After DA results, before IDA1 |
| IDA2 | 08:00 D   | **07:15 D**   | 11:00–23:00 | After IDA1 results, before IDA2 |
| IDA3 | 14:00 D   | **13:15 D**   | 17:00–23:00 | After IDA2 results, before IDA3 |

- Trading day D runs 23:00 (D-1) to 23:00 (D), Irish local time.
- Times are Irish local time (IST in summer, GMT in winter). The UTC equivalent is one hour earlier in summer and the same in winter, so cutoffs are stored in local time and converted per date.
- `F_DatetimeTick` (arrival time) is stored in **UTC** — confirmed by the probe: EirGrid issues at 00/06/12/18 Irish time appear as 00/06/12/18 in January and 23/05/11/17 in June.
- A dataset is usable at a decision point only if its tick is **strictly before** the decision time.
- A forecast version older than **3 days** at the decision time is treated as missing.
- Sources for gate closures: SEMO market training (DA closes 11:00 D-1); Nord Pool SEM-GB IDA timings (IDA1 18:30 CET, IDA2 09:00 CET). IDA3 gate closure to be confirmed against the SEMOpx auction timings document.

## Data availability — actuals

| Dataset | dim_id | Resolution | Tick pattern (when it arrives) | Latest usable at DA | at IDA1 | at IDA2 | at IDA3 | Checked |
|---|---|---|---|---|---|---|---|---|
| isem_cap_ccgt_act_mw | 14135 | 30 min | Trading day D-1 (22:00 D-2 to 21:30 D-1 UTC) arrives 00:00 D | D-2 | D-2 | D-1 | D-1 | [x] |
| isem_cap_*_act_mw (other fuels) | 14126–14139 | 30 min | Assumed same as 14135 — verify | | | | | [ ] |
| isem_pimb_act_eur_mwh | 9658 (check) | 30 min | | | | | | [ ] |
| isem_niv_act_mwh | | 30 min | | | | | | [ ] |
| isem_price_da_act_eur_mwh | 9408 / 18385 | 60 / 30 min | | n/a (not yet cleared) | D | D | D | [ ] |
| isem_price_ida1_act_eur_mwh | 9500 | 30 min | | n/a | n/a (not yet cleared) | D | D | [ ] |
| isem_price_ida2_act_eur_mwh | 9502 | 30 min | | n/a | n/a | n/a (not yet cleared) | D | [ ] |
| isem_price_ida3_act_eur_mwh | 9504 | 30 min | | n/a | n/a | n/a | n/a (not yet cleared) | [ ] |
| isem_mcv_da_*_act_mw | 13159–13175, 13330, 13539 | 60 min | | n/a (not yet cleared) | D | D | D | [ ] |
| isem_mcv_ida1_*_act_mw | 13369–13386, 13540 | 30 min | | n/a | n/a (not yet cleared) | D | D | [ ] |
| isem_mcv_ida2_*_act_mw | 13387–13404, 13541 | 30 min | | n/a | n/a | n/a (not yet cleared) | D | [ ] |
| isem_mcv_ida3_*_act_mw | 13405–13422, 13542 | 30 min | | n/a | n/a | n/a | n/a (not yet cleared) | [ ] |
| roi/ni_mcv_da_net_act_mw | 9580 / 9581 | 60 min to 30 Sep 2025, then 30 min | | n/a (not yet cleared) | D | D | D | [ ] |
| roi/ni_mcv_ida1_net_act_mw | 9582 / 9583 | 30 min | | n/a | n/a (not yet cleared) | D | D | [ ] |
| roi/ni_mcv_ida2_net_act_mw | 9584 / 9585 | 30 min | | n/a | n/a | n/a (not yet cleared) | D | [ ] |
| roi/ni_mcv_ida3_net_act_mw | 9586 / 9587 | 30 min | | n/a | n/a | n/a | n/a (not yet cleared) | [ ] |
| isem_wind_act_mw | 9169 | 15 min | | | | | | [ ] |
| isem_demand_act_mw | 9168 | 15 min | | | | | | [ ] |
| isem_solar_act_mw | 18372 | 15 min | | | | | | [ ] |
| isem_snsp_act_pct | 13997 | 30 min | | | | | | [ ] |
| isem_wind_dispatchdown_act_mw | 9673 | 15 min | | | | | | [ ] |
| isem_ewic / moyle / greenlink_flow_act_mw | 4871 / 4872 / 18349 | 30 min | | | | | | [ ] |

Auction results ("D") are usable only if they are published before the decision time of the later auction; check publication times (e.g. DA results before 16:45 D-1).

## Data availability — forecasts

Pulled with `dim_id_fcast_extractor.py`: for each delivery period, the latest version that arrived strictly before each decision time. One file per decision point in `individual_csvs/forecasts/fc_da`, `fc_ida1`, `fc_ida2`, `fc_ida3`. Each file keeps the `tick` of the version used.

| Dataset | dim_id | Source | Resolution | History from | Issue pattern | Version used at DA | at IDA1 | at IDA2 | at IDA3 | Checked |
|---|---|---|---|---|---|---|---|---|---|---|
| isem_wind_eirgrid_fc | 9171 | EirGrid | 15 min | Nov 2017 | 00/06/12/18 Irish time, extra issues in summer | 06:00 D-1 | 12:00 D-1 (later in summer) | 06:00 D | 12:00 D | [x] probe |
| isem_demand_eirgrid_fc | 9170 | EirGrid | 30 min | Nov 2017 | As 9171 | Only reaches ~30 h ahead: probe covered 44% (Jan) / 56% (Jun) of periods | 81% (Jan) / 96% (Jun) | 100% | 100% | [x] probe |
| isem_solar_eirgrid_fc | 18375 | EirGrid | 15 min | 21 May 2025 | | | | | | [ ] |
| isem_wind_meteologica_p10 / p50 / p90_fc | 4012 / 4014 / 4013 | Meteologica | | Jan 2015 | ~300 versions per week, mostly at :15 past the hour | Within ~1 h of cutoff | Within ~1 h | Within ~1 h | Within ~1 h | [x] probe (p50) |
| isem_demand_meteologica_p50_fc | 4004 | Meteologica | | Jan 2015 | As 4014 | 100% | 100% | 100% | 100% | [x] probe |
| isem_cap_*_fc (CCGT, OCGT, CHP, coal, distillate, pumped, DSU) | 14073, 14074, 14085, 14079, 14076, 14082, 14087 | ElectroRoute | 60 min | Sep 2021 | Daily 11:00 Irish time, covers ~12 h to ~5 days ahead | 11:00 D-2 | 11:00 D-1 | 11:00 D-1 | 11:00 D-1 | [x] probe (CCGT only) |
| isem_ewic_import / export_avail_fc | 14083 / 14084 | ElectroRoute | 60 min | Sep 2021 | As capacity | 11:00 D-2 | 11:00 D-1 | 11:00 D-1 | 11:00 D-1 | [x] probe |
| isem_moyle_import / export_avail_fc | 14088 / 14089 | ElectroRoute | 60 min | Sep 2021 | As capacity | 11:00 D-2 | 11:00 D-1 | 11:00 D-1 | 11:00 D-1 | [x] probe |
| isem_greenlink_import / export_avail_fc | 18344 / 18346 | ElectroRoute | 60 min | Apr 2025 | As capacity | 11:00 D-2 | 11:00 D-1 | 11:00 D-1 | 11:00 D-1 | [x] probe |

### Forecasts not used

| Dataset | dim_id | Reason |
|---|---|---|
| Available capacity forecast (SEMOpx) | 13312–13325 | Every version stamped 00:00 the day **after** delivery (`F_ST_ID_Status` = 2, `F_T_Type` null), so none exists before any decision point. Replaced by ElectroRoute capacity forecasts |
| SNSP forecast | 13955 | Only covers Mar 2021 – Jul 2022 |
| Capacity / IC availability, daily resolution | 9685–9702, 18343, 18345 | Same data as the hourly series at daily resolution |
| Other Meteologica, GB and ROI-only forecasts | various | Commented out in the extractor for now |

## Data quality status

### Good

| Dataset | dim_id | Notes |
|---|---|---|
| Wind actual | 9169 | Full 2022–2026; 154 short gaps; 13 small negatives (to −5 MW); resample 15 min → 30 min |
| Demand actual | 9168 | Full 2022–2026; 154 short gaps; resample 15 min → 30 min |
| MCV, all auctions (19 categories each) | 13159–13175, 13330, 13369–13386, 13387–13404, 13405–13422, 13539–13542 | IDA auctions balance; DA balances 2022–2025 |
| Capacity outturn | 14126–14139 | Re-pulled with latest tick: duplicate week (1–7 June 2022) removed, values unchanged |
| DA net position | 9580 / 9581 | ROI = −NI in 99.7% of periods (DA is an all-island auction) |
| IDA1 / IDA2 net position | 9582–9585 | ROI + NI = −interconnector MCV for that auction |
| IDA3 net position | 9586 / 9587 | ROI = −NI exactly (no interconnector flow in IDA3) |
| DA / IDA1 price | 18385 + 9408 / 9500 | No gaps |
| GB DA price (EPEX, N2EX hourly) | | No gaps |
| Greenlink flow | 18349 | From 18 Apr 2025 |

### Usable with a decision

| Dataset | dim_id | Issue | Decision |
|---|---|---|---|
| Oil capacity | 14139 | Ends 31 Dec 2023 | Set to 0 afterwards if units retired — confirm |
| Lignite capacity | 14138 | Ends 31 Dec 2023; one value of −0.77 MW (19 Nov 2022) | Set to 0 afterwards if units retired — confirm; clip at 0 |
| Lignite MCV | 13174, 13384, 13402, 13420 | Volumes 2022–23, then zero | Keep; document |
| AGU MCV | 13163, 13369, 13387, 13405 | Only DA has volumes; IDA all zero | Keep DA only |
| DA MCV | 13159–13175 | Hourly throughout, incl. after DA moved to 30 min (Oct 2025) | Fill each hour onto both half-hours |
| DA MCV balance | — | Unexplained ~−42 MW gap in 2026 | Investigate later (possible new category) |
| DA net position | 9580 / 9581 | Hourly until 30 Sep 2025, 30 min from 1 Oct 2025 | Fill each hour onto both half-hours before Oct 2025 |
| Capacity outturn gaps | 14126–14139 | 9 missing days: 4 Dec 2022, 31 Dec 2022, 4 Jul 2023, 23 Apr 2025, 11 Sep 2025, 29 Oct 2025, 28–30 Aug 2026 | Carry forward up to 3 days, or leave blank — decide |
| Net position, all auctions | 9580–9587 | Missing 28 Aug – 17 Sep 2025 and 31 Dec 2023 | Leave blank; MCV available for the 2025 gap |
| IDA2 / IDA3 net position and price | 9584–9587, 9502, 9504 | Only cover 11:00–23:00 and 17:00–23:00 | Expected; do not fill outside the auction window |
| Solar actual | 18372 | Starts 20 May 2025 (18373 / 18374 ROI / NI start the same day, not kept); −1 to −5 MW at night; block of −167 MW on 22 Jul 2026 ~04:00 UTC; missing repeated hour on 26 Oct 2025 | Clip at 0 |
| SNSP actual | 13997 | Both clock-change days missing completely (30 Oct 2022, 29 Oct 2023), plus short gaps | Leave blank — decide |
| Wind dispatch-down | 9673 | 1,863 missing periods, mostly Feb–Mar 2022 | Leave blank — decide |
| EWIC / Moyle flow | 4871 / 4872 | Long runs of zero = outages (EWIC Mar–May 2022, Apr–May 2025, Apr–May 2026; Moyle Jul 2022) | Keep as zero (real outages) |
| EWIC availability forecast | 14083 / 14084 | Still 500 MW during the Apr 2025 outage (flows 0); Moyle forecast correctly 0 in Jul 2022 | Validate against flows over the full history |
| ElectroRoute CCGT capacity forecast vs outturn | 14073 / 14135 | Forecast ~4,390 MW vs outturn ~4,883 MW (8–14 Jan 2024) — different definitions | Treat as separate inputs |
| NBP week-ahead gas | | One 14-day gap (June 2022); 7-day forward-fill won't cover it | Decide |
| GB DA price, half-hourly EPEX | | One missing day | Decide |

### Needs fixing

| Dataset | dim_id | Issue | Action |
|---|---|---|---|
| MCV file names | 13159–13542 | 66 files still had database names (e.g. `13159_IE_DA_MCV_Hydro_MW.csv`) | Run `rename_mcv_files.py --apply` — done? [ ] |
| Master dataset | — | `processed/master.parquet` built before renaming | Rebuild with `python -m src.data_prep` |

### Not yet pulled / in progress

| Dataset | dim_id | Status |
|---|---|---|
| Gas capacity outturn | 14140 | Pulled — returned no data. Not needed (CCGT + OCGT + CHP cover it) |
| Forecasts (20 series × 4 decision points) | see forecast table | Full pull running |

## Notes

- Net position files were re-pulled under the new names (`roi_mcv_da_net_act_mw` etc.); the old `netpos` files are no longer used.
- DA interconnector MCV (13330) is 99.7% zero and IDA3 interconnector MCV (13422) 99.9% zero.
- Work-laptop extracts are saved to `OneDrive - Electroroute Ireland\thesis-data` and copied to the TCD OneDrive `thesis-data` manually (the two OneDrive accounts don't sync).