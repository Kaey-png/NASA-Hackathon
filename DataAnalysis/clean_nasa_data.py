#!/usr/bin/env python3
"""
Clean the team's Giovanni CSV exports, one state at a time.

Expected layout (your repo): .../United States/<State>/<Soil Moisture|Precipitation|Temperature>/*.csv

Setup: save this file as DataAnalysis/clean_nasa_data.py in the repo (needs: pip install pandas).
Usage: from inside DataAnalysis, just run
    python clean_nasa_data.py
It reads every CSV under its own folder and writes results to DataAnalysis/Cleaned/ (never touching the raw files).
Options: [root_folder] [-o out_folder] [--baseline 1991-2020] [--max-gap 2]

Per file it: skips the metadata header, turns the fill value into NaN, snaps dates to month start,
and converts units so everything is comparable:
    soil moisture   NLDAS/GLDAS kg m-2 -> m3/m3 (divide by layer thickness in mm); FLDAS already m3/m3
    precipitation   GPM IMERG mm/hr    -> mm/month (x 24 x days in month)
    temperature     Kelvin             -> degrees C (only if values look like Kelvin)
Per state it merges everything on date and writes <State>_clean.csv, _anomalies.csv, _zscores.csv.
It also writes all_states_clean.csv and qc_report.txt (read the WARNINGS first).
"""
import argparse
import io
import re
import sys
from pathlib import Path

import pandas as pd

KG_SOURCES = ("NLDAS", "GLDAS")
SEASONS = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
           6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}
LIMITS = {"soil": (0, 0.8), "precip": (0, 1000), "temp": (-50, 60)}   # sanity ranges after conversion


def state_of(path):
    parts = path.parts
    if "United States" in parts:
        i = parts.index("United States")
        if i + 1 < len(parts) - 1:
            return parts[i + 1]
    return path.parent.parent.name


def classify(col, title):
    label = f"{col} {title}".lower()
    if "soil moisture" in label or "soilm" in label:
        return "soil"
    if "precip" in label:
        return "precip"
    if "temperature" in label or re.search(r"t2m|tsurf|tmax|tmin", label):
        return "temp"
    return "other"


def read_file(path, warn):
    """Return a list of dicts, one per data column in a Giovanni CSV."""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    start = next((i for i, l in enumerate(lines) if l.lower().startswith("time")), None)
    if start is None:
        warn(f"{path.name}: no 'time' header row, skipped")
        return []
    text = "\n".join(lines[:start])
    title = next((l for l in lines[:start] if l.startswith("Title")), "")
    fills = {m.group(1): float(m.group(2)) for m in re.finditer(r"Fill Value \((.+?)\):,\s*(\S+)", text)}
    shape = re.search(r"shape=([^&]+)", text)
    bbox = re.search(r'User Bounding Box:,"([^"]*)"', text)
    region = shape.group(1).split("/")[-1] if shape else (bbox.group(1) if bbox and bbox.group(1) else "unknown")

    df = pd.read_csv(io.StringIO("\n".join(lines[start:])), skipinitialspace=True)
    df.columns = [c.strip() for c in df.columns]
    dates = pd.to_datetime(df.iloc[:, 0]).dt.to_period("M").dt.to_timestamp()
    out = []
    for col in df.columns[1:]:
        v = pd.to_numeric(df[col], errors="coerce")
        v = v.mask(v == fills[col]) if col in fills else v.mask(v < -999)
        kind, conv = classify(col, title), "none"
        name = re.sub(r"^mean_", "", col)
        if kind == "soil":
            src = next((s for s in ("FLDAS", "NLDAS", "GLDAS") if s in f"{col} {title}".upper()), "SOIL")
            m = re.search(r"\((\d+)\s*-\s*(\d+)\s*cm", title) or re.search(r"(\d+)_(\d+)cm", col)
            if not m:
                warn(f"{path.name}: cannot read layer depth, skipped")
                continue
            top, bot = int(m.group(1)), int(m.group(2))
            name = f"{src}_{top}-{bot}cm"
            if src in KG_SOURCES:
                v, conv = v / ((bot - top) * 10), f"kg m-2 / {(bot - top) * 10} mm"
            if "_CP_" in col:
                warn(f"{path.name}: FLDAS 'CP' product (2019 onward only). Re-download the "
                     f"'C_GL_M' rows (1982 onward) for a long record.")
        elif kind == "precip":
            name = "precip_mm_month"
            if "IMERG" in col.upper():
                v, conv = v * 24 * dates.dt.days_in_month.values, "mm/hr x 24 x days"
            else:
                warn(f"{path.name}: unknown precipitation unit, left unchanged")
        elif kind == "temp" and v.median() > 200:
            v, conv = v - 273.15, "K - 273.15"
        s = pd.Series(v.values, index=dates, name=name)
        out.append(dict(file=path.name, kind=kind, name=name, series=s[~s.index.duplicated()],
                        region=region, conv=conv, fills=int(df[col].isna().sum())))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", help="folder to search for .csv files (default: the folder this script is in)")
    ap.add_argument("-o", "--out", help="output folder (default: <root>/Cleaned)")
    ap.add_argument("--baseline", help="anomaly baseline years, e.g. 1991-2020 (default: full record)")
    ap.add_argument("--max-gap", type=int, default=2, help="fill gaps up to N months (default 2, 0 = off)")
    a = ap.parse_args()

    rep, warns = [], []

    def log(m):
        print(m)
        rep.append(m)

    def warn(m):
        warns.append(m)

    root = Path(a.root).resolve() if a.root else Path(__file__).resolve().parent
    out = Path(a.out).resolve() if a.out else root / "Cleaned"
    files = sorted(f for f in root.rglob("*.csv") if out not in f.resolve().parents)   # skip our own output
    if not files:
        sys.exit(f"No CSV files under {root}")
    by_state = {}
    for f in files:
        for r in read_file(f, warn):
            by_state.setdefault(state_of(f), []).append(r)

    out.mkdir(parents=True, exist_ok=True)
    frames, regions = [], {}
    for state, recs in sorted(by_state.items()):
        log(f"\n=== {state}")
        series, kinds = {}, {}
        for r in recs:
            if r["name"] in series:
                warn(f"{state}: {r['file']} duplicates {r['name']}, kept the first")
                continue
            series[r["name"]], kinds[r["name"]] = r["series"], r["kind"]
            regions.setdefault(state, set()).add(r["region"])
            s = r["series"]
            log(f"  {r['name']:<18} {s.index.min():%Y-%m} to {s.index.max():%Y-%m} | {len(s)} months | "
                f"fill {r['fills']} | {r['conv']} | {r['region']}")
        n = {k: s.notna().sum() for k, s in series.items()}
        for k, c in n.items():
            peers = [n[j] for j in n if kinds[j] == kinds[k]]
            if kinds[k] == "soil" and c < 0.5 * max(peers):
                warn(f"{state}: {k} has only {c} months vs {max(peers)} for its peers (different product or dates?)")
        data = pd.concat(series.values(), axis=1, sort=True)
        data = data.reindex(pd.date_range(data.index.min(), data.index.max(), freq="MS"))
        data.index.name = "date"
        if a.max_gap > 0:
            data = data.interpolate(limit=a.max_gap, limit_area="inside")
        for k in data:
            lo, hi = LIMITS.get(kinds[k], (-1e9, 1e9))
            bad = int(((data[k] < lo) | (data[k] > hi)).sum())
            if bad:
                warn(f"{state}: {k} has {bad} value(s) outside {lo} to {hi}. Check units.")
        base = data
        if a.baseline:
            y0, y1 = map(int, a.baseline.split("-"))
            base = data[(data.index.year >= y0) & (data.index.year <= y1)]
        clim = base.groupby(base.index.month).mean()
        anom = data - clim.reindex(data.index.month).values
        z = (anom - anom.mean()) / anom.std()
        d = out / state.replace(" ", "")
        d.mkdir(exist_ok=True)
        tag = state.replace(" ", "")
        clean = data.copy()
        clean["season"] = [SEASONS[m] for m in clean.index.month]
        clean.to_csv(d / f"{tag}_clean.csv", float_format="%.6f")
        anom.to_csv(d / f"{tag}_anomalies.csv", float_format="%.6f")
        z.to_csv(d / f"{tag}_zscores.csv", float_format="%.4f")
        frames.append(clean.assign(state=state))
        full = data.dropna()
        log(f"  months with every series present: {len(full)}"
            + (f" ({full.index.min():%Y-%m} to {full.index.max():%Y-%m})" if len(full) else ""))

    for s, r in regions.items():
        if len(r) > 1:
            warn(f"{s}: files use different regions {sorted(r)}")
    ids = {}
    for s, r in regions.items():
        for x in r:
            ids.setdefault(x, set()).add(s)
    for x, ss in ids.items():
        if len(ss) > 1:
            warn(f"region {x} appears in more than one state folder: {sorted(ss)}")

    pd.concat(frames).to_csv(out / "all_states_clean.csv", float_format="%.6f")
    log("\nWARNINGS" if warns else "\nNo warnings.")
    for w in warns:
        log(f"  !! {w}")
    (out / "qc_report.txt").write_text("\n".join(rep), encoding="utf-8")
    log(f"\nWrote cleaned files and qc_report.txt to {out}/")


if __name__ == "__main__":
    main()
