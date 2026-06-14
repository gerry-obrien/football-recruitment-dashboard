import pandas as pd
import warnings
warnings.filterwarnings("ignore")

BASE = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\data"

players = pd.read_csv(f"{BASE}/transfermarkt/players.csv")
clubs   = pd.read_csv(f"{BASE}/transfermarkt/clubs.csv")
comps   = pd.read_csv(f"{BASE}/transfermarkt/competitions.csv")
ctry    = pd.read_csv(f"{BASE}/transfermarkt/countries.csv")

# ─── Join chain ───────────────────────────────────────────────────────────────
print("=" * 70)
print("Transfermarkt join chain validation")
print("=" * 70)
print("players columns:", list(players.columns))
print("clubs columns:", list(clubs.columns))
print("competitions columns:", list(comps.columns))
print("countries columns:", list(ctry.columns))
print()

# Step 1: players → clubs
m1 = players.merge(clubs, left_on="current_club_id", right_on="club_id", how="left", suffixes=("_pl","_cl"))
matched = m1["club_id"].notna().sum()
print(f"players -> clubs: {matched}/{len(players)} matched ({matched/len(players)*100:.1f}%)")

# Step 2: → competitions  (clubs has domestic_competition_id, competitions has competition_id)
m2 = m1.merge(comps, left_on="domestic_competition_id", right_on="competition_id", how="left", suffixes=("","_comp"))
matched2 = m2["competition_id"].notna().sum()
print(f"+ competitions: {matched2}/{len(m2)} matched ({matched2/len(m2)*100:.1f}%)")

# Step 3: → countries (competitions has country_id)
m3 = m2.merge(ctry, on="country_id", how="left", suffixes=("","_ctry"))
matched3 = m3["country_name"].notna().sum()
print(f"+ countries: {matched3}/{len(m3)} matched ({matched3/len(m3)*100:.1f}%)")
print()
print("Sample fully joined (3 rows):")
show = ["name_pl","position","market_value_in_eur","name_cl","competition_id","country_name"]
show_ok = [c for c in show if c in m3.columns]
print(m3[show_ok].dropna(subset=["competition_id","country_name"]).head(3).to_string())

# Key check: how many players have a market value AND a competition?
has_value_and_comp = m3[m3["market_value_in_eur"].notna() & m3["competition_id"].notna()]
print(f"\nPlayers with market_value + competition: {len(has_value_and_comp)}")

# ─── Transfers ────────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("transfers.csv: fee analysis")
print("=" * 70)
tr = pd.read_csv(f"{BASE}/transfermarkt/transfers.csv")
print("Total rows:", len(tr))
fee_non_null = tr["transfer_fee"].notna().sum()
fee_nonzero  = (tr["transfer_fee"] > 0).sum()
print(f"Non-null fees: {fee_non_null} ({fee_non_null/len(tr)*100:.1f}%)")
print(f"Non-zero fees (actual paid transfers): {fee_nonzero} ({fee_nonzero/len(tr)*100:.1f}%)")
print("Transfer seasons:", sorted(tr["transfer_season"].dropna().unique())[:25])
paid = tr[tr["transfer_fee"] > 0]["transfer_fee"]
print("Fee range (non-zero):", paid.min(), "–", paid.max())
print("Fee percentiles:")
print(paid.describe(percentiles=[.25,.5,.75,.9,.95,.99]).round(0))
print("Transfers with fee >1M:", (paid > 1_000_000).sum())
print("Transfers with fee >5M:", (paid > 5_000_000).sum())

# ─── Player valuations ────────────────────────────────────────────────────────
print()
print("=" * 70)
print("player_valuations.csv: temporal spread")
print("=" * 70)
pv = pd.read_csv(f"{BASE}/transfermarkt/player_valuations.csv")
pv["date"] = pd.to_datetime(pv["date"], errors="coerce")
print("Date range:", pv["date"].min(), "–", pv["date"].max())
pv["year"] = pv["date"].dt.year
print("Rows per year (last 15 years):")
print(pv["year"].value_counts().sort_index().tail(15).to_string())
vpx = pv.groupby("player_id").size()
print(f"Valuations per player: median={vpx.median()}, max={vpx.max()}, mean={vpx.mean():.1f}")
print("Unique players with valuation history:", pv["player_id"].nunique())

# ─── Cross-dataset name matching ──────────────────────────────────────────────
print()
print("=" * 70)
print("Cross-dataset name matching: FIFA v23 vs FBref vs Transfermarkt")
print("=" * 70)
# Only load what we need
fifa_cols = ["fifa_version","short_name","club_name","league_name","overall"]
fifa_chunks = pd.read_csv(f"{BASE}/fifa/male_players.csv", usecols=fifa_cols, chunksize=200000)
fifa_v23 = pd.concat([c[c["fifa_version"]==23] for c in fifa_chunks])
print(f"FIFA v23 rows: {len(fifa_v23)}")

fbref = pd.read_csv(f"{BASE}/fbref/players_data_2024_2025.csv", usecols=["Player","Squad","Comp"])

def norm(s):
    return s.str.strip().str.lower()

fifa_names  = set(norm(fifa_v23["short_name"].dropna()))
fbref_names = set(norm(fbref["Player"].dropna()))
tm_names    = set(norm(players["name"].dropna()))

print(f"FIFA v23 unique names: {len(fifa_names)}")
print(f"FBref unique names:    {len(fbref_names)}")
print(f"TM unique names:       {len(tm_names)}")

exact_fifa_fbref = fifa_names & fbref_names
exact_fbref_tm   = fbref_names & tm_names
exact_fifa_tm    = fifa_names & tm_names

print(f"\nExact overlap FIFA v23 ∩ FBref:        {len(exact_fifa_fbref):4d}  ({len(exact_fifa_fbref)/len(fbref_names)*100:.1f}% of FBref)")
print(f"Exact overlap FBref ∩ Transfermarkt:   {len(exact_fbref_tm):4d}  ({len(exact_fbref_tm)/len(fbref_names)*100:.1f}% of FBref)")
print(f"Exact overlap FIFA v23 ∩ Transfermarkt: {len(exact_fifa_tm):4d}  ({len(exact_fifa_tm)/len(tm_names)*100:.1f}% of TM)")

unmatched_fbref_from_fifa = fbref_names - fifa_names
print(f"\nFBref players NOT found in FIFA v23: {len(unmatched_fbref_from_fifa)}")
print("Examples:", sorted(list(unmatched_fbref_from_fifa))[:20])

# What's in FBref Big 5 leagues
print("\nFBref competition breakdown:")
print(fbref["Comp"].value_counts().to_string())
