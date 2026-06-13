import pandas as pd
import warnings
warnings.filterwarnings("ignore")

BASE = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\data"

# ─── 1. FIFA: how many versions in the full file? ────────────────────────────
print("=" * 70)
print("FIFA version coverage (scanning fifa_version column only)")
print("=" * 70)
versions = pd.read_csv(f"{BASE}/fifa/male_players.csv", usecols=["fifa_version"])
print("Total rows:", len(versions))
print("Version distribution:")
print(versions["fifa_version"].value_counts().sort_index())

# ─── 2. FIFA: overall/value_eur nulls at scale ────────────────────────────────
print()
print("=" * 70)
print("FIFA: null rates at full scale")
print("=" * 70)
key_cols = ["fifa_version","overall","value_eur","nationality_name","player_positions","club_name","league_name"]
fifa = pd.read_csv(f"{BASE}/fifa/male_players.csv", usecols=key_cols)
for c in key_cols:
    n = fifa[c].isnull().sum()
    pct = n / len(fifa) * 100
    print(f"  {c}: {n} nulls ({pct:.1f}%)")
print("Overall rating range:", fifa["overall"].min(), "–", fifa["overall"].max())
print("value_eur range (non-null): €", fifa["value_eur"].min(), "– €", fifa["value_eur"].max())
print("nationality_name unique count:", fifa["nationality_name"].nunique())
print("Leagues (FIFA v23 only):")
v23 = fifa[fifa["fifa_version"]==23]
print("  V23 rows:", len(v23))
print("  V23 leagues:", v23["league_name"].nunique(), "unique")
print("  Sample leagues:", list(v23["league_name"].dropna().unique()[:15]))

# ─── 3. Transfermarkt join chain ──────────────────────────────────────────────
print()
print("=" * 70)
print("Transfermarkt join chain validation")
print("=" * 70)
players = pd.read_csv(f"{BASE}/transfermarkt/players.csv")
clubs   = pd.read_csv(f"{BASE}/transfermarkt/clubs.csv")
comps   = pd.read_csv(f"{BASE}/transfermarkt/competitions.csv")
ctry    = pd.read_csv(f"{BASE}/transfermarkt/countries.csv")

# players → clubs on current_club_id / club_id
m1 = players.merge(clubs, left_on="current_club_id", right_on="club_id", how="left")
matched = m1["club_id"].notna().sum()
print(f"players->clubs merge: {matched}/{len(players)} players matched ({matched/len(players)*100:.1f}%)")

# clubs → competitions on domestic_competition_id / competition_id
m2 = m1.merge(comps, left_on="domestic_competition_id", right_on="competition_id", how="left")
matched2 = m2["competition_id"].notna().sum()
print(f"+ competitions merge: {matched2}/{len(m2)} rows matched ({matched2/len(m2)*100:.1f}%)")

# competitions → countries on country_id
m3 = m2.merge(ctry, left_on="country_id_x", right_on="country_id", how="left")
matched3 = m3["country_name"].notna().sum()
print(f"+ countries merge: {matched3}/{len(m3)} rows matched ({matched3/len(m3)*100:.1f}%)")

# Key columns present after full join
print()
print("Sample of fully joined chain (3 rows):")
cols_to_show = ["name","position","market_value_in_eur","name_y","competition_id","country_name"]
cols_present = [c for c in cols_to_show if c in m3.columns]
print(m3[cols_present].dropna(subset=["competition_id"]).head(3).to_string())

# ─── 4. Transfers: fee coverage ───────────────────────────────────────────────
print()
print("=" * 70)
print("transfers.csv: fee analysis")
print("=" * 70)
tr = pd.read_csv(f"{BASE}/transfermarkt/transfers.csv")
print("Total transfer rows:", len(tr))
fee_non_null = tr["transfer_fee"].notna().sum()
fee_nonzero  = (tr["transfer_fee"] > 0).sum()
print(f"Non-null fees: {fee_non_null} ({fee_non_null/len(tr)*100:.1f}%)")
print(f"Non-zero fees: {fee_nonzero} ({fee_nonzero/len(tr)*100:.1f}%)")
print("Transfer seasons present:", sorted(tr["transfer_season"].dropna().unique())[:20])
print("Fee range (>0):", tr[tr["transfer_fee"]>0]["transfer_fee"].min(), "–", tr[tr["transfer_fee"]>0]["transfer_fee"].max())
print("Fee percentiles (>0):")
print(tr[tr["transfer_fee"]>0]["transfer_fee"].describe(percentiles=[.25,.5,.75,.9,.99]))

# ─── 5. player_valuations temporal spread ─────────────────────────────────────
print()
print("=" * 70)
print("player_valuations.csv: temporal spread")
print("=" * 70)
pv = pd.read_csv(f"{BASE}/transfermarkt/player_valuations.csv")
pv["date"] = pd.to_datetime(pv["date"], errors="coerce")
print("Date range:", pv["date"].min(), "–", pv["date"].max())
pv["year"] = pv["date"].dt.year
print("Rows per year:")
print(pv["year"].value_counts().sort_index().tail(15))
vals_per_player = pv.groupby("player_id").size()
print("Valuations per player — median:", vals_per_player.median(), " max:", vals_per_player.max())

# ─── 6. Cross-dataset name matching feasibility ──────────────────────────────
print()
print("=" * 70)
print("Cross-dataset name matching: FIFA v23 vs FBref vs Transfermarkt")
print("=" * 70)
fifa_v23 = pd.read_csv(f"{BASE}/fifa/male_players.csv",
                        usecols=["fifa_version","short_name","club_name"],
                        nrows=500000)
fifa_v23 = fifa_v23[fifa_v23["fifa_version"] == 23].copy()

fbref = pd.read_csv(f"{BASE}/fbref/players_data_2024_2025.csv",
                    usecols=["Player","Squad","Comp"])

# Normalize
def norm(s):
    return s.str.strip().str.lower()

fifa_names  = set(norm(fifa_v23["short_name"].dropna()))
fbref_names = set(norm(fbref["Player"].dropna()))
tm_names    = set(norm(players["name"].dropna()))

print(f"FIFA v23 unique player names: {len(fifa_names)}")
print(f"FBref unique player names: {len(fbref_names)}")
print(f"Transfermarkt unique player names: {len(tm_names)}")

fifa_fbref_exact = fifa_names & fbref_names
print(f"\nExact name overlap FIFA v23 ∩ FBref: {len(fifa_fbref_exact)} ({len(fifa_fbref_exact)/len(fbref_names)*100:.1f}% of FBref)")

fifa_tm_exact = fifa_names & tm_names
print(f"Exact name overlap FIFA v23 ∩ Transfermarkt: {len(fifa_tm_exact)} ({len(fifa_tm_exact)/len(tm_names)*100:.1f}% of TM)")

fbref_tm_exact = fbref_names & tm_names
print(f"Exact name overlap FBref ∩ Transfermarkt: {len(fbref_tm_exact)} ({len(fbref_tm_exact)/len(fbref_names)*100:.1f}% of FBref)")

# Unmatched FBref players (not in FIFA)
unmatched = fbref_names - fifa_names
print(f"\nFBref players NOT in FIFA v23 (exact name): {len(unmatched)}")
print("Examples:", list(unmatched)[:15])
