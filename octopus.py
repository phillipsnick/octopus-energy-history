#!/usr/bin/env python3
"""Download all half-hourly consumption from the Octopus API.

Usage:
  pip install -r requirements.txt
  export OCTOPUS_KEY=sk_live_xxx
  export OCTOPUS_ACCOUNT=A-XXXXXXXX
  python3 octopus.py

Writes one CSV per fuel (elec / gas), covering every meter on the account,
de-duplicated by interval start. Gas from SMETS2 meters is in m³.
"""
import csv, os, sys
from datetime import datetime, timedelta
import requests

BASE = "https://api.octopus.energy/v1"
KEY = os.environ.get("OCTOPUS_KEY") or sys.exit("set OCTOPUS_KEY")
ACCT = os.environ.get("OCTOPUS_ACCOUNT") or sys.exit("set OCTOPUS_ACCOUNT")
FROM = os.environ.get("PERIOD_FROM", "2015-01-01T00:00:00Z")

s = requests.Session()
s.auth = (KEY, "")  # API key as username, blank password


def get_all(url, params=None):
    """Follow 'next' links until exhausted."""
    out = []
    while url:
        r = s.get(url, params=params, timeout=60)
        r.raise_for_status()
        j = r.json()
        out += j["results"]
        url, params = j.get("next"), None  # 'next' already carries the query
    return out


def instant(ts):
    """Parse an API timestamp ('Z' or '+01:00') to an aware datetime."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def gaps(starts):
    """Yield (last_present, next_present, missing_slots) for holes in sorted starts."""
    for a, b in zip(starts, starts[1:]):
        if b - a > timedelta(minutes=30):
            yield a, b, (b - a) // timedelta(minutes=30) - 1


def meters(acct):
    r = s.get(f"{BASE}/accounts/{acct}/", timeout=60)
    r.raise_for_status()
    for prop in r.json()["properties"]:
        for mp in prop.get("electricity_meter_points", []):
            if mp.get("is_export"):
                continue  # skip export MPANs (solar export)
            for m in mp["meters"]:
                yield "elec", f"{BASE}/electricity-meter-points/{mp['mpan']}/meters/{m['serial_number']}/consumption/"
        for mp in prop.get("gas_meter_points", []):
            for m in mp["meters"]:
                yield "gas", f"{BASE}/gas-meter-points/{mp['mprn']}/meters/{m['serial_number']}/consumption/"


rows = {"elec": {}, "gas": {}}
for fuel, url in meters(ACCT):
    data = get_all(url, {"period_from": FROM, "page_size": 25000, "order_by": "period"})
    print(f"{fuel}: {url.split('/')[-4]} / {url.split('/')[-3]} -> {len(data)} intervals")
    for d in data:
        # key on the instant, not the string: the API mixes 'Z' and '+01:00'
        rows[fuel][instant(d["interval_start"])] = (d["consumption"], d["interval_start"], d["interval_end"])

for fuel, r in rows.items():
    if not r:
        continue
    fn = f"octopus-{fuel}.csv"
    with open(fn, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["consumption", "interval_start", "interval_end"])
        starts = sorted(r)
        for start in starts:
            w.writerow(r[start])
    print(f"wrote {fn}: {len(r)} rows, {r[starts[0]][1]} -> {r[starts[-1]][1]}")
    holes = list(gaps(starts))
    if holes:
        print(f"  {len(holes)} gaps, {sum(n for *_, n in holes)} missing half-hours:")
        for a, b, n in holes:
            print(f"    {r[a][1]} -> {r[b][1]}  ({n} missing)")