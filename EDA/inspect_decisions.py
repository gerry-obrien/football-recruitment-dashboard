# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import warnings
warnings.filterwarnings("ignore")

BASE = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\data"

players = pd.read_csv(f"{BASE}/transfermarkt/players.csv")
clubs   = pd.read_csv(f"{BASE}/transfermarkt/clubs.csv")
comps   = pd.read_csv(f"{BASE}/transfermarkt/competitions.csv")
tr      = pd.read_csv(f"{BASE}/transfermarkt/transfers.csv")
pv      = pd.read_csv(f"{BASE}/transfermarkt/player_valuations.csv")

# ── 1. TRANSFER FEES: breakdown by season and by league ──────────────────────
print("=" * 70)
print("DECISION 1: Transfer fee data depth")
print("=" * 70)

tr["transfer_date"] = pd.to_datetime(tr["transfer_date"], errors="coerce")
paid = tr[tr["transfer_fee"] > 0].copy()

print(f"Total non-zero fee transfers (all time): {len(paid)}")
print()

# Season breakdown - last 8 seasons
recent_seasons = ["17/18","18/19","19/20","20/21","21/22","22/23","23/24","24/25"]
print("Paid transfers per season (recent):")
for s in recent_seasons:
    n = (paid["transfer_season"] == s).sum()
    med = paid[paid["transfer_season"]==s]["transfer_fee"].median() if n > 0 else 0
    print(f"  {s}: {n:4d} paid transfers  | median fee: EUR {med:,.0f}")

# Join transfers to clubs to get competition
tr_comp = paid.merge(clubs[["club_id","domestic_competition_id"]],
                     left_on="to_club_id", right_on="club_id", how="left")
tr_comp = tr_comp.merge(comps[["competition_id","name","type"]],
                        left_on="domestic_competition_id", right_on="competition_id", how="left")

# Focus on domestic leagues only
dom = tr_comp[tr_comp["type"]=="domestic_league"].copy()
print(f"\nPaid transfers to domestic league clubs (all time): {len(dom)}")

# Recent 5 seasons
recent5 = ["19/20","20/21","21/22","22/23","23/24"]
dom_recent = dom[dom["transfer_season"].isin(recent5)]
print(f"Paid transfers to domestic leagues (last 5 seasons): {len(dom_recent)}")

print("\nTransfers per league (last 5 seasons, top 20 by count):")
league_counts = dom_recent.groupby("name")["transfer_fee"].agg(["count","median","mean"]).sort_values("count",ascending=False).head(20)
league_counts.columns = ["n_transfers","median_fee","mean_fee"]
league_counts["median_fee"] = league_counts["median_fee"].map("EUR {:,.0f}".format)
league_counts["mean_fee"]   = league_counts["mean_fee"].map("EUR {:,.0f}".format)
print(league_counts.to_string())

print("\nLeagues with < 5 paid transfers (last 5 seasons):")
lc_all = dom_recent.groupby("name")["transfer_fee"].count()
thin = lc_all[lc_all < 5]
print(f"  {len(thin)} leagues have fewer than 5 paid transfers")
print("  Examples:", list(thin.index[:10]))

# ── 2. PLAYER VALUATIONS: can it fill the TM market_value nulls? ─────────────
print()
print("=" * 70)
print("DECISION 2: Filling market_value_in_eur nulls from player_valuations")
print("=" * 70)

null_players = players[players["market_value_in_eur"].isna()]["player_id"]
print(f"Players with null market_value_in_eur: {len(null_players)}")

# Get latest valuation per player
pv["date"] = pd.to_datetime(pv["date"], errors="coerce")
latest_val = pv.sort_values("date").groupby("player_id").last()["market_value_in_eur"].reset_index()
latest_val.columns = ["player_id","latest_val"]

fillable = null_players.isin(latest_val["player_id"])
print(f"Of those, how many have a record in player_valuations: {fillable.sum()} ({fillable.sum()/len(null_players)*100:.1f}%)")
remaining_null = len(null_players) - fillable.sum()
print(f"Still null after filling from valuations: {remaining_null} ({remaining_null/len(players)*100:.1f}% of all players)")

# What dates are the latest valuations for these filled players?
filled_ids = null_players[fillable]
filled_dates = pv[pv["player_id"].isin(filled_ids)].groupby("player_id")["date"].max()
print(f"\nLatest valuation dates for filled players:")
print(filled_dates.dt.year.value_counts().sort_index().tail(10).to_string())

# ── 3. FIFA value_eur vs TM market_value: how correlated? ────────────────────
print()
print("=" * 70)
print("DECISION 3: FIFA value_eur vs TM market_value_in_eur correlation")
print("=" * 70)

# Load FIFA v23 value and name
fifa_cols = ["fifa_version","long_name","short_name","value_eur","overall","league_name"]
chunks = pd.read_csv(f"{BASE}/fifa/male_players.csv", usecols=fifa_cols, chunksize=200000)
fifa_v23 = pd.concat([c[c["fifa_version"]==23] for c in chunks])

print(f"FIFA v23 players with value_eur: {fifa_v23['value_eur'].notna().sum()}")
print(f"FIFA v23 value_eur range: EUR {fifa_v23['value_eur'].min():,.0f} - EUR {fifa_v23['value_eur'].max():,.0f}")

# Try to match on long_name to TM
def norm(s):
    return s.str.strip().str.lower()

fifa_v23["name_norm"] = norm(fifa_v23["long_name"].fillna(fifa_v23["short_name"]))
players["name_norm"]  = norm(players["name"])

merged = fifa_v23.merge(players[["name_norm","market_value_in_eur"]],
                         on="name_norm", how="inner")
print(f"\nExact match FIFA long_name -> TM name: {len(merged)} players")
if len(merged) > 100:
    corr = merged[["value_eur","market_value_in_eur"]].dropna().corr()
    print("Pearson correlation (FIFA value_eur vs TM market_value):")
    print(corr.to_string())
    print("\nSample matched rows:")
    print(merged[["long_name","value_eur","market_value_in_eur","overall","league_name"]].dropna().head(10).to_string())

# ── 4. How many FIFA v23 names improve with long_name? ───────────────────────
print()
print("=" * 70)
print("DECISION 4: long_name vs short_name match rate against TM")
print("=" * 70)

fbref = pd.read_csv(f"{BASE}/fbref/players_data_2024_2025.csv", usecols=["Player","Squad"])
fbref["name_norm"] = norm(fbref["Player"])

fifa_short = set(norm(fifa_v23["short_name"].dropna()))
fifa_long  = set(norm(fifa_v23["long_name"].dropna()))
fbref_names = set(fbref["name_norm"])
tm_names    = set(norm(players["name"].dropna()))

print("Match FIFA short_name -> FBref:", len(fifa_short & fbref_names), f"({len(fifa_short & fbref_names)/len(fbref_names)*100:.1f}% of FBref)")
print("Match FIFA long_name  -> FBref:", len(fifa_long  & fbref_names), f"({len(fifa_long  & fbref_names)/len(fbref_names)*100:.1f}% of FBref)")
print()
print("Match FIFA short_name -> TM:", len(fifa_short & tm_names), f"({len(fifa_short & tm_names)/len(tm_names)*100:.1f}% of TM)")
print("Match FIFA long_name  -> TM:", len(fifa_long  & tm_names), f"({len(fifa_long  & tm_names)/len(tm_names)*100:.1f}% of TM)")

# ── 5. FIFA v23 per-league value_eur: league scatter viability ───────────────
print()
print("=" * 70)
print("DECISION 5: FIFA value_eur per league (Page 2 scatter viability)")
print("=" * 70)
league_stats = fifa_v23[fifa_v23["value_eur"].notna()].groupby("league_name").agg(
    n_players=("value_eur","count"),
    avg_overall=("overall","mean"),
    avg_value=("value_eur","mean"),
    median_value=("value_eur","median")
).sort_values("n_players", ascending=False)
league_stats["avg_overall"] = league_stats["avg_overall"].round(1)
league_stats["avg_value"]   = league_stats["avg_value"].apply(lambda x: f"EUR {x:,.0f}")
league_stats["median_value"] = league_stats["median_value"].apply(lambda x: f"EUR {x:,.0f}")
print("Top 20 leagues by player count:")
print(league_stats.head(20).to_string())
print(f"\nTotal leagues in FIFA v23 with value data: {len(league_stats)}")
print(f"Leagues with < 20 players: {(league_stats['n_players'] < 20).sum()}")
