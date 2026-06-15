# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import warnings
warnings.filterwarnings("ignore")

BASE_FIFA = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\data\fifa"
INTER     = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\outputs\intermediate"
OUT       = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\outputs"

# ── Load dimension tables ─────────────────────────────────────────────────────
dim_country     = pd.read_csv(f"{INTER}/dim_country.csv")
dim_competition = pd.read_csv(f"{INTER}/dim_competition.csv")
dim_club        = pd.read_csv(f"{INTER}/dim_club.csv")
dim_player      = pd.read_csv(f"{INTER}/dim_player.csv")

# ── Mapping dicts ─────────────────────────────────────────────────────────────
FIFA_POSITION_MAP = {
    "GK":  "GK",
    "CB":  "Centre-Back",
    "LB":  "Full-Back",  "RB":  "Full-Back",
    "LWB": "Full-Back",  "RWB": "Full-Back",
    "CDM": "Midfielder", "CM":  "Midfielder", "CAM": "Midfielder",
    "LM":  "Midfielder", "RM":  "Midfielder",
    "LW":  "Winger",     "RW":  "Winger",
    "CF":  "Striker",    "ST":  "Striker",
}

NATIONALITY_CORRECTIONS = {
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "China PR":               "China",
    "Hong Kong":              "Hongkong",
    "Republic of Ireland":    "Ireland",
    "Korea Republic":         "Korea, South",
    "Turkey":                 "Türkiye",
}

FIFA_LEAGUE_MAP = {
    "English Premier League": "GB1",
    "Premier League":         "GB1",
    "LaLiga Santander":       "ES1",
    "LaLiga EA Sports":       "ES1",
    "LaLiga":                 "ES1",
    "La Liga":                "ES1",
    "Bundesliga":             "L1",
    "Serie A":                "IT1",
    "Serie A TIM":            "IT1",
    "Ligue 1":                "FR1",
    "Ligue 1 Uber Eats":      "FR1",
    "Ligue 1 Conforama":      "FR1",
    "Ligue 1 McDonald's":     "FR1",
}

# ── 1. Read and deduplicate FIFA v19/v21/v23 ──────────────────────────────────
print("── 1. Loading FIFA v19/v21/v23 ──")
cols = [
    "player_id", "fifa_version", "fifa_update",
    "long_name", "short_name",
    "nationality_name", "league_name", "club_name",
    "player_positions", "overall", "potential", "value_eur",
]
chunks = pd.read_csv(f"{BASE_FIFA}/male_players.csv",
                     usecols=cols, chunksize=200_000)
fifa = pd.concat([c[c["fifa_version"].isin([19, 21, 23])] for c in chunks])
print(f"  Raw rows (v19/21/23): {len(fifa)}")

# One row per (FIFA player_id, version) — keep highest fifa_update
fifa = (
    fifa.sort_values("fifa_update", ascending=False)
    .drop_duplicates(subset=["player_id", "fifa_version"])
    .reset_index(drop=True)
)
print(f"  After dedup: {len(fifa)}")
print(f"  Rows per version:")
print(fifa["fifa_version"].value_counts().sort_index().to_string())

# Verify Big 5 league names present in the data
league_counts = fifa["league_name"].value_counts()
print(f"\n  FIFA league_name values matching Big 5 map:")
for name, count in league_counts.items():
    if name in FIFA_LEAGUE_MAP:
        print(f"    {name!r:<42} {count} rows → {FIFA_LEAGUE_MAP[name]}")
unrecognised = [(n, c) for n, c in league_counts.items() if n not in FIFA_LEAGUE_MAP]
print(f"\n  Top 10 unrecognised leagues (will get null competition_id):")
for name, count in unrecognised[:10]:
    print(f"    {name!r:<42} {count} rows")

# ── 2. Position bucket ────────────────────────────────────────────────────────
print("\n── 2. Position mapping ──")
fifa["position_first"] = fifa["player_positions"].str.split(",").str[0].str.strip()
fifa["position_bucket"] = fifa["position_first"].map(FIFA_POSITION_MAP)
unmapped = fifa[fifa["position_bucket"].isna()]["position_first"].value_counts()
if len(unmapped):
    print(f"  WARNING — unmapped positions: {unmapped.to_dict()}")
else:
    print(f"  All positions mapped")
print(f"  Distribution:")
print(fifa["position_bucket"].value_counts().to_string())

# ── 3. Nationality → country_id ───────────────────────────────────────────────
print("\n── 3. Nationality FK resolution ──")
country_lookup = dim_country.set_index("name")["country_id"]
fifa["nat_clean"] = fifa["nationality_name"].replace(NATIONALITY_CORRECTIONS)
fifa["nationality_country_id"] = fifa["nat_clean"].map(country_lookup)
null_nat = fifa["nationality_country_id"].isna().sum()
print(f"  Resolved: {len(fifa) - null_nat} / {len(fifa)}")
print(f"  Null (countries absent from TM): {null_nat} ({null_nat/len(fifa)*100:.1f}%)")

# ── 4. FIFA player → TM player_id (exact name match only) ────────────────────
print("\n── 4. Player → TM player_id (exact match only) ──")

def norm(s):
    return str(s).strip().lower() if pd.notna(s) else ""

tm_lookup = dict(zip(dim_player["name"].apply(norm), dim_player["player_id"]))
fifa["long_name_norm"] = fifa["long_name"].apply(norm)
fifa["tm_player_id"] = fifa["long_name_norm"].map(tm_lookup)

matched = fifa["tm_player_id"].notna().sum()
print(f"  Exact matches: {matched} / {len(fifa)} ({matched/len(fifa)*100:.1f}%)")
print(f"  Null player_id: {fifa['tm_player_id'].isna().sum()} (nullable — not needed for Page 1)")

# ── 5. League → competition_id ────────────────────────────────────────────────
print("\n── 5. Competition FK resolution ──")
fifa["competition_id"] = fifa["league_name"].map(FIFA_LEAGUE_MAP)
matched_comp = fifa["competition_id"].notna().sum()
print(f"  Resolved: {matched_comp} / {len(fifa)} ({matched_comp/len(fifa)*100:.1f}%)")
print(f"  Null (non-Big 5 leagues): {fifa['competition_id'].isna().sum()}")

# ── 6. Club → club_id (exact match only, high null rate expected) ─────────────
print("\n── 6. Club FK resolution ──")
club_lookup = dict(zip(dim_club["name"].apply(norm), dim_club["club_id"]))
fifa["club_id"] = fifa["club_name"].apply(norm).map(club_lookup)
matched_club = fifa["club_id"].notna().sum()
print(f"  Resolved: {matched_club} / {len(fifa)} ({matched_club/len(fifa)*100:.1f}%)")

# ── 7. Assemble and write ─────────────────────────────────────────────────────
print("\n── 7. Assembling player_seasons.csv ──")
player_seasons = (
    fifa[[
        "tm_player_id", "nationality_country_id", "competition_id", "club_id",
        "position_bucket", "league_name", "fifa_version", "overall", "potential", "value_eur",
    ]]
    .rename(columns={"tm_player_id": "player_id"})
    .copy()
)
# Cast FK columns to nullable integer so CSV writes "9" not "9.0"
# This prevents Tableau treating them as decimals and failing to join
for col in ["player_id", "nationality_country_id", "club_id"]:
    player_seasons[col] = player_seasons[col].astype("Int64")
player_seasons.insert(0, "id", range(1, len(player_seasons) + 1))

print(f"  Final rows:    {len(player_seasons)}")
print(f"  Columns:       {player_seasons.columns.tolist()}")
print(f"  overall range: {player_seasons['overall'].min()} – {player_seasons['overall'].max()}")
print(f"\n  Null rates per column:")
for col in player_seasons.columns:
    n = player_seasons[col].isna().sum()
    if n > 0:
        print(f"    {col:<30} {n} ({n/len(player_seasons)*100:.1f}%)")

player_seasons.to_csv(f"{OUT}/player_seasons.csv", index=False)
print(f"\nWritten to outputs/player_seasons.csv")
