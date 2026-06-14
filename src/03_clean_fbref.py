# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
from rapidfuzz import process, fuzz
import warnings
warnings.filterwarnings("ignore")

BASE_FBREF = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\data\fbref"
INTER      = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\outputs\intermediate"

# ── Load dimension tables ─────────────────────────────────────────────────────
dim_club         = pd.read_csv(f"{INTER}/dim_club.csv")
dim_player       = pd.read_csv(f"{INTER}/dim_player.csv")
dim_sub_position = pd.read_csv(f"{INTER}/dim_sub_position.csv")

# ── Mapping dicts ─────────────────────────────────────────────────────────────
COMP_MAP = {
    "Premier League": "GB1",
    "La Liga":        "ES1",
    "Serie A":        "IT1",
    "Ligue 1":        "FR1",
    "Bundesliga":     "L1",
}

# Manual club overrides: FBref squad names too different for fuzzy to resolve
SQUAD_OVERRIDES = {
    "Bayern Munich": 27,   # FC Bayern München
    "Inter":         46,   # Football Club Internazionale Milano S.p.A.
    "Wolves":       543,   # Wolverhampton Wanderers Football Club
    "Nice":         417,   # Olympique Gymnaste Club Nice Côte d'Azur
    "Auxerre":      290,   # Association de la Jeunesse auxerroise
    "Rennes":       273,   # Stade Rennais Football Club
}

# Coarse fallback for FBref players who don't match TM
FBREF_POSITION_FALLBACK = {
    "GK": "GK",
    "DF": "Centre-Back",
    "MF": "Midfielder",
    "FW": "Striker",
}

def norm(s):
    return str(s).strip().lower() if pd.notna(s) else ""

# ── 1. Read FBref ─────────────────────────────────────────────────────────────
print("── 1. Reading FBref ──")
keep_cols = [
    "Player", "Squad", "Comp", "Pos",
    "MP", "90s",
    "xG", "npxG", "xAG", "Ast", "KP", "G-PK",
    "Tkl", "Int", "Clr", "Err",
    "PrgP", "PrgC", "PrgR",
    "GA", "Saves", "CS",
]
fbref = pd.read_csv(f"{BASE_FBREF}/players_data_2024_2025.csv", usecols=keep_cols)
print(f"  Raw rows: {len(fbref)}  |  Unique players: {fbref['Player'].nunique()}")

# Strip country prefix from Comp and map to competition_id
fbref["Comp_clean"] = fbref["Comp"].str.split(" ", n=1).str[1]
fbref["competition_id"] = fbref["Comp_clean"].map(COMP_MAP)
print(f"  Comp values after stripping: {sorted(fbref['Comp_clean'].unique().tolist())}")

# Take first position code
fbref["pos_primary"] = fbref["Pos"].str.split(",").str[0].str.strip()

# ── 2. Match FBref players to TM player_id ────────────────────────────────────
print("\n── 2. Player name matching (FBref → TM) ──")
unique_players = fbref["Player"].dropna().unique()
tm_lookup = dict(zip(dim_player["name"].apply(norm), dim_player["player_id"]))

# Exact match
exact_map = {p: tm_lookup.get(norm(p)) for p in unique_players}
matched_exact = sum(1 for v in exact_map.values() if v is not None)
print(f"  Exact matches: {matched_exact} / {len(unique_players)} ({matched_exact/len(unique_players)*100:.1f}%)")

# Fuzzy match on remaining (rapidfuzz WRatio >= 90)
unmatched = [p for p, v in exact_map.items() if v is None]
tm_names_list = list(tm_lookup.keys())
print(f"  Running fuzzy match on {len(unmatched)} unmatched players...")
fuzzy_map = {}
for name in unmatched:
    result = process.extractOne(norm(name), tm_names_list,
                                scorer=fuzz.WRatio, score_cutoff=90)
    if result:
        fuzzy_map[name] = tm_lookup[result[0]]

print(f"  Fuzzy matches added: {len(fuzzy_map)}")
player_to_tm = {p: v for p, v in exact_map.items() if v is not None}
player_to_tm.update(fuzzy_map)
print(f"  Total matched: {len(player_to_tm)} / {len(unique_players)} ({len(player_to_tm)/len(unique_players)*100:.1f}%)")
print(f"  Unmatched: {len(unique_players) - len(player_to_tm)}")

fbref["player_id"] = fbref["Player"].map(player_to_tm)

# ── 3. Position bucket ────────────────────────────────────────────────────────
print("\n── 3. Position bucket assignment ──")
sub_lookup    = dict(zip(dim_player["player_id"], dim_player["sub_position"]))
sub_to_bucket = dict(zip(dim_sub_position["sub_position"], dim_sub_position["position_bucket"]))

fbref["position_bucket"] = (
    fbref["player_id"].map(sub_lookup).map(sub_to_bucket)
)
fallback_mask = fbref["position_bucket"].isna()
fbref.loc[fallback_mask, "position_bucket"] = (
    fbref.loc[fallback_mask, "pos_primary"].map(FBREF_POSITION_FALLBACK)
)
print(f"  From TM sub_position:    {(~fallback_mask).sum()}")
print(f"  From FBref Pos fallback: {fallback_mask.sum()}")
print(f"  Distribution:")
print(fbref["position_bucket"].value_counts().to_string())

# ── 4. Aggregate multi-row players (Blocker 3) ───────────────────────────────
print("\n── 4. Aggregating multi-row players ──")
row_counts = fbref["Player"].value_counts()
multi_players = row_counts[row_counts > 1]
print(f"  Players with multiple rows: {len(multi_players)}")

# Primary row = max 90s per player (determines competition and club)
primary = (
    fbref.sort_values("90s", ascending=False)
    .drop_duplicates("Player")
    [["Player", "Squad", "competition_id", "player_id", "position_bucket"]]
)

# Sum counting stats — min_count=1 preserves NaN for all-null columns (GK stats for outfield)
count_cols = ["MP", "90s", "xG", "npxG", "xAG", "Ast", "KP", "G-PK",
              "Tkl", "Int", "Clr", "Err", "PrgP", "PrgC", "PrgR",
              "GA", "Saves", "CS"]
agg = fbref.groupby("Player")[count_cols].sum(min_count=1).reset_index()
agg = agg.merge(primary, on="Player", how="left")
print(f"  After aggregation: {len(agg)} unique players")

# ── 5. Filter to 90s >= 5 (Blocker 4) ────────────────────────────────────────
print("\n── 5. Minimum minutes filter (90s >= 5) ──")
before = len(agg)
agg = agg[agg["90s"] >= 5].reset_index(drop=True)
print(f"  Dropped: {before - len(agg)} players below 450 minutes")
print(f"  Remaining: {len(agg)}")

# ── 6. Compute per-90 stats ───────────────────────────────────────────────────
print("\n── 6. Computing per-90 stats ──")
per90_map = {
    "xG":   "xg_per90",           "npxG": "npxg_per90",
    "xAG":  "xag_per90",          "Ast":  "ast_per90",
    "KP":   "key_passes_per90",   "G-PK": "goals_non_pen_per90",
    "Tkl":  "tackles_per90",      "Int":  "interceptions_per90",
    "Clr":  "clearances_per90",   "Err":  "errors_per90",
    "PrgP": "prog_passes_per90",  "PrgC": "prog_carries_per90",
    "PrgR": "prog_receptions_per90", "GA": "ga_per90",
}
for raw, out in per90_map.items():
    agg[out] = agg[raw] / agg["90s"]

# Recompute rates from aggregated counts — do NOT average raw percentages (Blocker 3)
agg["save_pct"] = agg["Saves"] / (agg["Saves"] + agg["GA"])
agg["cs_pct"]   = agg["CS"] / agg["MP"]

gk_count = agg["save_pct"].notna().sum()
print(f"  Per-90 columns computed: {len(per90_map)}")
print(f"  Goalkeepers identified (save_pct not null): {gk_count}")

# ── 7. Club FK resolution (exact then fuzzy against Big 5 clubs only) ────────
print("\n── 7. Club FK resolution ──")
big5_ids = {"GB1", "ES1", "IT1", "FR1", "L1"}
big5_clubs = dim_club[dim_club["domestic_competition_id"].isin(big5_ids)].copy()
club_lookup = dict(zip(big5_clubs["name"].apply(norm), big5_clubs["club_id"]))
club_names_list = list(club_lookup.keys())

unique_squads = agg["Squad"].dropna().unique()
squad_exact = {s: club_lookup.get(norm(s)) for s in unique_squads}
exact_clubs = sum(1 for v in squad_exact.values() if v is not None)
print(f"  Exact matches: {exact_clubs} / {len(unique_squads)}")

unmatched_squads = [s for s, v in squad_exact.items() if v is None]
fuzzy_clubs = {}
for squad in unmatched_squads:
    result = process.extractOne(norm(squad), club_names_list,
                                scorer=fuzz.WRatio, score_cutoff=85)
    if result:
        fuzzy_clubs[squad] = club_lookup[result[0]]
print(f"  Fuzzy matches added: {len(fuzzy_clubs)}")

squad_to_club = {s: v for s, v in squad_exact.items() if v is not None}
squad_to_club.update(fuzzy_clubs)
squad_to_club.update(SQUAD_OVERRIDES)
agg["club_id"] = agg["Squad"].map(squad_to_club)
matched_club = agg["club_id"].notna().sum()
print(f"  Total resolved: {matched_club} / {len(agg)} ({matched_club/len(agg)*100:.1f}%)")
print(f"  Unresolved squads: {agg[agg['club_id'].isna()]['Squad'].unique().tolist()}")

# ── 8. Assemble and write ─────────────────────────────────────────────────────
print("\n── 8. Writing fbref_clean.csv ──")
out_cols = [
    "player_id", "Player", "competition_id", "club_id", "Squad",
    "position_bucket", "90s",
    "xg_per90", "npxg_per90", "xag_per90", "ast_per90",
    "key_passes_per90", "goals_non_pen_per90",
    "tackles_per90", "interceptions_per90", "clearances_per90", "errors_per90",
    "prog_passes_per90", "prog_carries_per90", "prog_receptions_per90",
    "save_pct", "cs_pct", "ga_per90",
]
fbref_clean = agg[out_cols].rename(columns={"90s": "minutes_90s"}).copy()
fbref_clean["season"] = "2024-25"

print(f"  Final rows: {len(fbref_clean)}")
print(f"  Columns: {fbref_clean.columns.tolist()}")
print(f"\n  Null rates per column:")
for col in fbref_clean.columns:
    n = fbref_clean[col].isna().sum()
    if n > 0:
        print(f"    {col:<35} {n} ({n/len(fbref_clean)*100:.1f}%)")

fbref_clean.to_csv(f"{INTER}/fbref_clean.csv", index=False)
print(f"\nWritten to outputs/intermediate/fbref_clean.csv")
