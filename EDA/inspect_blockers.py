# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import warnings
warnings.filterwarnings("ignore")

BASE = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\data"

# ── BLOCKER 2: FIFA nationality_name vs TM dim_country.name ──────────────────
print("=" * 70)
print("BLOCKER 2: FIFA nationality_name → dim_country mismatch check")
print("=" * 70)

countries = pd.read_csv(f"{BASE}/transfermarkt/countries.csv", encoding='utf-8')
print(f"dim_country rows: {len(countries)}")
print(f"TM country columns: {countries.columns.tolist()}")
print(f"Sample TM country_name values: {list(countries['country_name'].head(10))}")
print()

# Load all nationality_name values from FIFA v19/v21/v23
cols = ["fifa_version", "nationality_name"]
chunks = pd.read_csv(f"{BASE}/fifa/male_players.csv", usecols=cols, chunksize=200_000)
fifa = pd.concat([c[c["fifa_version"].isin([19, 21, 23])] for c in chunks])

fifa_nationalities = pd.DataFrame({"nationality_name": fifa["nationality_name"].dropna().unique()})
print(f"Distinct FIFA nationality_name values: {len(fifa_nationalities)}")

# Anti-join: which FIFA nationalities have no match in TM?
tm_names = set(countries["country_name"].dropna().str.strip())
fifa_nationalities["matched"] = fifa_nationalities["nationality_name"].str.strip().isin(tm_names)

unmatched = fifa_nationalities[~fifa_nationalities["matched"]].sort_values("nationality_name")
print(f"\nUnmatched FIFA nationality_name values ({len(unmatched)} total):")
print(unmatched["nationality_name"].tolist())

matched = fifa_nationalities[fifa_nationalities["matched"]]
print(f"\nMatched: {len(matched)} / {len(fifa_nationalities)}")

# ── BLOCKER 5: FBref Comp prefix → competition_id mapping ────────────────────
print()
print("=" * 70)
print("BLOCKER 5: FBref Comp values after stripping country prefix")
print("=" * 70)

fbref = pd.read_csv(f"{BASE}/fbref/players_data_2024_2025.csv", usecols=["Comp"])
fbref["Comp_clean"] = fbref["Comp"].str.split(" ", n=1).str[1]
print("Distinct Comp values (raw):", fbref["Comp"].unique().tolist())
print()
print("Distinct Comp values (after stripping prefix):", fbref["Comp_clean"].unique().tolist())
print()
print("Row counts per cleaned Comp:")
print(fbref["Comp_clean"].value_counts().to_string())
