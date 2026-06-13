# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import warnings
warnings.filterwarnings("ignore")

BASE = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\data"

# ── 1. FIFA 23: what exact dates does it cover? ──────────────────────────────
print("=" * 70)
print("FIFA 23: update dates")
print("=" * 70)
fifa_cols = ["fifa_version","fifa_update","fifa_update_date","short_name","long_name",
             "club_name","league_name","overall","value_eur"]
chunks = pd.read_csv(f"{BASE}/fifa/male_players.csv", usecols=fifa_cols, chunksize=200000)
fifa_v23 = pd.concat([c[c["fifa_version"]==23] for c in chunks])

print("fifa_update values:", sorted(fifa_v23["fifa_update"].unique()))
print("fifa_update_date values:", sorted(fifa_v23["fifa_update_date"].unique()))
print()
print("Rows per update:")
print(fifa_v23.groupby(["fifa_update","fifa_update_date"]).size().to_string())
print()
# Sample of latest update
latest_update = fifa_v23["fifa_update"].max()
sample = fifa_v23[fifa_v23["fifa_update"]==latest_update]
print(f"Latest update ({latest_update}) sample players:")
print(sample[["long_name","club_name","league_name","overall","value_eur"]].head(10).to_string())

# ── 2. TM players.csv: what season/date does it represent? ───────────────────
print()
print("=" * 70)
print("Transfermarkt players.csv: temporal anchor")
print("=" * 70)
players = pd.read_csv(f"{BASE}/transfermarkt/players.csv")
print("last_season distribution (top 10):")
print(players["last_season"].value_counts().head(10).to_string())
print()
print("Sample players with last_season 2024 or 2025:")
recent = players[players["last_season"].isin([2024, 2025])]
print(f"  Players with last_season 2024: {(players['last_season']==2024).sum()}")
print(f"  Players with last_season 2025: {(players['last_season']==2025).sum()}")
print()
print("Sample recent players:")
print(recent[["name","position","current_club_name","market_value_in_eur","last_season"]].head(10).to_string())

# ── 3. TM player_valuations: what's the actual current date of data? ─────────
print()
print("=" * 70)
print("player_valuations.csv: most recent dates")
print("=" * 70)
pv = pd.read_csv(f"{BASE}/transfermarkt/player_valuations.csv")
pv["date"] = pd.to_datetime(pv["date"], errors="coerce")
print("Most recent 20 valuation dates:")
print(pv["date"].sort_values(ascending=False).head(20).dt.strftime("%Y-%m-%d").value_counts().to_string())
print()
# What clubs/players have the most recent dates?
latest = pv[pv["date"] >= "2024-01-01"].sort_values("date", ascending=False)
print(f"Valuations from 2024 onwards: {len(latest)}")
print("Sample:")
print(latest[["player_id","date","market_value_in_eur","current_club_name"]].head(10).to_string())

# ── 4. Transfers: season coverage and date range ──────────────────────────────
print()
print("=" * 70)
print("transfers.csv: season and date coverage")
print("=" * 70)
tr = pd.read_csv(f"{BASE}/transfermarkt/transfers.csv")
tr["transfer_date"] = pd.to_datetime(tr["transfer_date"], errors="coerce")
print("Season distribution:")
print(tr["transfer_season"].value_counts().sort_index().to_string())
print()
print("transfer_date range:", tr["transfer_date"].min(), "to", tr["transfer_date"].max())
print()
# Future dates investigation
future = tr[tr["transfer_date"] > "2026-06-13"]
print(f"Rows with transfer_date after today (2026-06-13): {len(future)}")
print(future[["player_id","transfer_date","transfer_season","transfer_fee","from_club_name","to_club_name"]].head(10).to_string())

# ── 5. FBref: what season exactly? ───────────────────────────────────────────
print()
print("=" * 70)
print("FBref: season confirmation")
print("=" * 70)
fbref = pd.read_csv(f"{BASE}/fbref/players_data_2024_2025.csv",
                    usecols=["Player","Squad","Comp","Age","Born","MP","Min"])
print("Shape:", fbref.shape)
print("Age distribution:")
print(fbref["Age"].describe().round(1))
print()
# Born year distribution to confirm season vintage
print("Born year distribution (should peak around 1995-2005 for active players):")
print(fbref["Born"].value_counts().sort_index().tail(20).to_string())

# ── 6. THE KEY QUESTION: who appears across datasets at the same time? ────────
print()
print("=" * 70)
print("TEMPORAL ALIGNMENT: same player across FIFA 23 vs FBref 24-25")
print("=" * 70)
# Take latest FIFA 23 update, join to FBref on long_name
def norm(s): return s.str.strip().str.lower()

latest_fifa = fifa_v23[fifa_v23["fifa_update"]==latest_update].copy()
latest_fifa["name_norm"] = norm(latest_fifa["long_name"].fillna(latest_fifa["short_name"]))
fbref["name_norm"] = norm(fbref["Player"])

merged = latest_fifa.merge(fbref, on="name_norm", how="inner",
                           suffixes=("_fifa","_fbref"))
print(f"Players matched FIFA 23 (latest update) -> FBref 2024-25: {len(merged)}")
print()
print("Age at FIFA 23 vs age in FBref 24-25 season:")
merged["age_gap"] = merged["Age"].astype(float) - (merged["overall"] * 0)  # just use Age from fbref
# FIFA 23 update date for age comparison
print("FBref age distribution for matched players:")
print(merged["Age"].astype(float).describe().round(1))
print()
print("Sample matched players — club in FIFA 23 vs club in FBref 24-25:")
print(merged[["long_name","club_name","Squad","overall","Age"]].head(20).to_string())

# How many matched players changed clubs between FIFA 23 and FBref 24-25?
merged["same_club"] = merged["club_name"].str.strip().str.lower() == merged["Squad"].str.strip().str.lower()
print(f"\nSame club in both datasets: {merged['same_club'].sum()} / {len(merged)}")
print(f"Changed club between FIFA 23 and FBref 24-25: {(~merged['same_club']).sum()} / {len(merged)}")
print()
print("Examples of club changes:")
changed = merged[~merged["same_club"]][["long_name","club_name","Squad","overall"]].head(15)
print(changed.to_string())
