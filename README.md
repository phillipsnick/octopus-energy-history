# octopus.py

Downloads all half-hourly electricity and gas consumption for your Octopus Energy account via the API.

## Setup

```bash
pip install -r requirements.txt
```

Get your API key from https://octopus.energy/dashboard/new/accounts/personal-details/api-access (starts `sk_live_`). Your account number (`A-XXXXXXXX`) is on the same page.

## Usage

```bash
export OCTOPUS_KEY=sk_live_xxx
export OCTOPUS_ACCOUNT=A-XXXXXXXX
export PERIOD_FROM=2015-01-01T00:00:00Z   # optional, defaults to 2015-01-01
python3 octopus.py
```

## Output

- `octopus-elec.csv` — electricity import, kWh per half-hour
- `octopus-gas.csv` — gas, m³ (SMETS2) or kWh (SMETS1) per half-hour

Each file covers every meter on the account, sorted and de-duplicated by `interval_start`. Export (solar) MPANs are skipped.

## Notes

- Only data held by Octopus is available — typically from when you joined with a working smart meter.
- Timestamps are as returned by the API (UTC/GMT or with BST offset).
- The day/night (E7) register split isn't provided; derive it from the timestamps using your meter's E7 hours.