# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

INTER = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\outputs\intermediate"
OUT   = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\outputs"

# Position-relevant metrics for percentile ranks (locked in project spec)
POSITION_METRICS = {
    "Striker":     ["npxg_per90", "goals_non_pen_per90", "xag_per90", "ast_per90", "prog_receptions_per90"],
    "Winger":      ["xg_per90", "ast_per90", "xag_per90", "key_passes_per90", "prog_carries_per90"],
    "Midfielder":  ["prog_passes_per90", "xag_per90", "key_passes_per90", "tackles_per90", "interceptions_per90"],
    "Full-Back":   ["prog_carries_per90", "prog_passes_per90", "ast_per90", "tackles_per90", "interceptions_per90"],
    "Centre-Back": ["clearances_per90", "interceptions_per90", "tackles_per90", "errors_per90", "prog_passes_per90"],
    "GK":          ["save_pct", "cs_pct", "ga_per90"],
}

# Lower is better — rank inverted so that a lower raw value earns a higher percentile
INVERTED_METRICS = {"errors_per90", "ga_per90"}

# ── 1. Load inputs ─────────────────────────────────────────────────────────────
print("── 1. Loading inputs ──")
fbref          = pd.read_csv(f"{INTER}/fbref_clean.csv")
dim_player     = pd.read_csv(f"{INTER}/dim_player.csv")
player_seasons = pd.read_csv(f"{OUT}/player_seasons.csv")

print(f"  fbref_clean:    {len(fbref)} rows")
print(f"  dim_player:     {len(dim_player)} rows")
print(f"  player_seasons: {len(player_seasons)} rows")

# ── 2. Join TM player attributes ───────────────────────────────────────────────
print("\n── 2. Joining TM player attributes ──")
tm_cols = ["player_id", "name", "date_of_birth", "nationality_country_id",
           "current_club_id", "sub_position", "market_value_eur", "highest_market_value_eur"]
enriched = fbref.merge(dim_player[tm_cols], on="player_id", how="left")

tm_match = enriched["name"].notna().sum()
mv_null  = enriched["market_value_eur"].isna().sum()
print(f"  TM attributes joined: {tm_match} / {len(enriched)} ({tm_match/len(enriched)*100:.1f}%)")
print(f"  market_value_eur nulls: {mv_null} ({mv_null/len(enriched)*100:.1f}%)")

# ── 3. Join FIFA v23 overall and potential ─────────────────────────────────────
print("\n── 3. Joining FIFA v23 overall/potential ──")
fifa_v23 = (
    player_seasons[player_seasons["fifa_version"] == 23]
    [["player_id", "overall", "potential"]]
    .dropna(subset=["player_id"])
    .sort_values("overall", ascending=False)
    .drop_duplicates(subset=["player_id"])   # multiple FIFA players can share a TM player_id via name match
    .rename(columns={"overall": "fifa_overall", "potential": "fifa_potential"})
)
enriched = enriched.merge(fifa_v23, on="player_id", how="left")

fifa_match = enriched["fifa_overall"].notna().sum()
print(f"  Matched to FIFA v23: {fifa_match} / {len(enriched)} ({fifa_match/len(enriched)*100:.1f}%)")
print(f"  Null fifa_overall: {enriched['fifa_overall'].isna().sum()} (emerged after FIFA 23 or unmatched)")

# ── 4. Percentile ranks within position bucket ─────────────────────────────────
print("\n── 4. Computing percentile ranks ──")
for bucket, metrics in POSITION_METRICS.items():
    mask = enriched["position_bucket"] == bucket
    n = mask.sum()
    print(f"  {bucket:<15} {n} players, {len(metrics)} metrics")
    for metric in metrics:
        if metric not in enriched.columns:
            print(f"    WARNING: {metric} not in dataframe — skipping")
            continue
        ascending = metric not in INVERTED_METRICS
        enriched.loc[mask, f"pr_{metric}"] = (
            enriched.loc[mask, metric]
            .rank(pct=True, ascending=ascending, na_option="keep")
            .mul(100)
        )

# ── 5. Performance index ───────────────────────────────────────────────────────
print("\n── 5. Computing performance index ──")
enriched["performance_index"] = np.nan
for bucket, metrics in POSITION_METRICS.items():
    mask    = enriched["position_bucket"] == bucket
    pr_cols = [f"pr_{m}" for m in metrics if f"pr_{m}" in enriched.columns]
    if pr_cols and mask.sum() > 0:
        enriched.loc[mask, "performance_index"] = (
            enriched.loc[mask, pr_cols]
            .mean(axis=1, skipna=True)
            .round(2)
        )
print(f"  Range: {enriched['performance_index'].min():.1f} – {enriched['performance_index'].max():.1f}")
print(f"  Mean:  {enriched['performance_index'].mean():.1f}")
print(f"  Null:  {enriched['performance_index'].isna().sum()}")

# ── 6. Assemble and write players_enriched.csv ────────────────────────────────
print("\n── 6. Writing players_enriched.csv ──")
pr_cols_all = sorted([c for c in enriched.columns if c.startswith("pr_")])
out_cols = (
    ["player_id", "Player", "name", "date_of_birth", "nationality_country_id",
     "current_club_id", "sub_position", "market_value_eur", "highest_market_value_eur",
     "competition_id", "club_id", "Squad", "position_bucket", "minutes_90s", "season",
     "xg_per90", "npxg_per90", "xag_per90", "ast_per90", "key_passes_per90",
     "goals_non_pen_per90", "tackles_per90", "interceptions_per90",
     "clearances_per90", "errors_per90", "prog_passes_per90",
     "prog_carries_per90", "prog_receptions_per90", "save_pct", "cs_pct", "ga_per90",
     "fifa_overall", "fifa_potential"]
    + pr_cols_all
    + ["performance_index"]
)
out_cols = [c for c in out_cols if c in enriched.columns]
players_enriched = enriched[out_cols].copy()
players_enriched.to_csv(f"{OUT}/players_enriched.csv", index=False)

print(f"  Rows: {len(players_enriched)}  |  Columns: {len(players_enriched.columns)}")
print(f"  Null rates (key columns):")
for col in ["player_id", "name", "market_value_eur", "fifa_overall", "performance_index"]:
    n = players_enriched[col].isna().sum()
    print(f"    {col:<30} {n} ({n/len(players_enriched)*100:.1f}%)")

# ── 7. fbref_radar.csv — long format for Tableau radar chart ──────────────────
print("\n── 7. Writing fbref_radar.csv (long format) ──")
radar_id_cols = [c for c in
    ["player_id", "Player", "name", "position_bucket",
     "competition_id", "club_id", "market_value_eur", "fifa_overall", "performance_index"]
    if c in players_enriched.columns]

radar_parts = []
for bucket, metrics in POSITION_METRICS.items():
    mask         = players_enriched["position_bucket"] == bucket
    pr_cols_b    = [f"pr_{m}" for m in metrics if f"pr_{m}" in players_enriched.columns]
    group        = players_enriched[mask][radar_id_cols + pr_cols_b].copy()
    melted       = group.melt(id_vars=radar_id_cols, value_vars=pr_cols_b,
                              var_name="metric", value_name="pr_value")
    melted["metric"] = melted["metric"].str[3:]   # strip "pr_" prefix
    radar_parts.append(melted)

fbref_radar = pd.concat(radar_parts, ignore_index=True)
fbref_radar.to_csv(f"{OUT}/fbref_radar.csv", index=False)

print(f"  Rows: {len(fbref_radar)}")
print(f"  Unique players: {fbref_radar['Player'].nunique()}")
print(f"  Rows per position:")
for bucket, metrics in POSITION_METRICS.items():
    n = (fbref_radar["position_bucket"] == bucket).sum()
    nplayers = n // len(metrics) if metrics else 0
    print(f"    {bucket:<15} {n:>5} rows  ({nplayers} players × {len(metrics)} metrics)")

print(f"\nWritten:")
print(f"  outputs/players_enriched.csv  ({len(players_enriched)} rows, {len(players_enriched.columns)} columns)")
print(f"  outputs/fbref_radar.csv       ({len(fbref_radar)} rows, long format)")
