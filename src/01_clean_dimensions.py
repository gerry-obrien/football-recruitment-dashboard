# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import warnings
warnings.filterwarnings("ignore")

BASE  = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\data\transfermarkt"
OUT   = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\outputs\intermediate"

NATIONALITY_CORRECTIONS = {
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "China PR": "China",
    "Hong Kong": "Hongkong",
    "Republic of Ireland": "Ireland",
    "Korea Republic": "Korea, South",
    "Turkey": "Türkiye",
}

SUB_POSITION_MAP = {
    "Goalkeeper":          "GK",
    "Centre-Back":         "Centre-Back",
    "Left-Back":           "Full-Back",
    "Right-Back":          "Full-Back",
    "Left Wing Back":      "Full-Back",
    "Right Wing Back":     "Full-Back",
    "Defensive Midfield":  "Midfielder",
    "Central Midfield":    "Midfielder",
    "Attacking Midfield":  "Midfielder",
    "Left Midfield":       "Midfielder",
    "Right Midfield":      "Midfielder",
    "Left Winger":         "Winger",
    "Right Winger":        "Winger",
    "Centre-Forward":      "Striker",
    "Second Striker":      "Striker",
}

# ── 1. dim_country ────────────────────────────────────────────────────────────
print("── 1. dim_country ──")
raw = pd.read_csv(f"{BASE}/countries.csv", encoding='utf-8')
dim_country = (
    raw[["country_id", "country_name", "country_code", "confederation"]]
    .rename(columns={"country_name": "name"})
    .drop_duplicates("country_id")
    .reset_index(drop=True)
)
dim_country.to_csv(f"{OUT}/dim_country.csv", index=False)
print(f"  rows: {len(dim_country)}  |  nulls in name: {dim_country['name'].isna().sum()}")
print(f"  sample: {dim_country['name'].head(5).tolist()}")

# ── 2. dim_competition ────────────────────────────────────────────────────────
print("\n── 2. dim_competition ──")

COMPETITION_DISPLAY_NAMES = {
    "GB1": "Premier League",
    "ES1": "La Liga",
    "IT1": "Serie A",
    "FR1": "Ligue 1",
    "L1":  "Bundesliga",
}

raw = pd.read_csv(f"{BASE}/competitions.csv", encoding='utf-8')
dim_competition = (
    raw[raw["type"] == "domestic_league"]
    [["competition_id", "name", "country_id", "type"]]
    .drop_duplicates("competition_id")
    .reset_index(drop=True)
)
# Add display_name: proper name for Big 5, title-cased slug for others
dim_competition["display_name"] = (
    dim_competition["competition_id"]
    .map(COMPETITION_DISPLAY_NAMES)
    .fillna(dim_competition["name"].str.replace("-", " ").str.title())
)
dim_competition.to_csv(f"{OUT}/dim_competition.csv", index=False)
big5 = dim_competition[dim_competition["competition_id"].isin(["GB1","ES1","IT1","FR1","L1"])]
print(f"  rows: {len(dim_competition)}  |  Big 5 present: {len(big5)}/5")
print(f"  Big 5:\n{big5[['competition_id','display_name']].to_string(index=False)}")

# ── 3. dim_club ───────────────────────────────────────────────────────────────
print("\n── 3. dim_club ──")
raw = pd.read_csv(f"{BASE}/clubs.csv", encoding='utf-8')
dim_club = (
    raw[["club_id", "name", "domestic_competition_id", "squad_size"]]
    .drop_duplicates("club_id")
    .reset_index(drop=True)
)
dim_club.to_csv(f"{OUT}/dim_club.csv", index=False)
print(f"  rows: {len(dim_club)}  |  domestic_competition_id nulls: {dim_club['domestic_competition_id'].isna().sum()}")

# ── 4. dim_position_group (manual) ───────────────────────────────────────────
print("\n── 4. dim_position_group ──")
dim_position_group = pd.DataFrame({
    "position_bucket": ["GK", "Centre-Back", "Full-Back", "Midfielder", "Winger", "Striker"],
    "display_order":   [1,    2,             3,           4,            5,        6],
})
dim_position_group.to_csv(f"{OUT}/dim_position_group.csv", index=False)
print(f"  rows: {len(dim_position_group)}")
print(f"  {dim_position_group.to_string(index=False)}")

# ── 5. dim_sub_position ───────────────────────────────────────────────────────
print("\n── 5. dim_sub_position ──")
players_raw = pd.read_csv(f"{BASE}/players.csv", encoding='utf-8')
distinct_subs = players_raw["sub_position"].dropna().unique()
dim_sub_position = pd.DataFrame({"sub_position": distinct_subs})
dim_sub_position["position_bucket"] = dim_sub_position["sub_position"].map(SUB_POSITION_MAP)

unmapped = dim_sub_position[dim_sub_position["position_bucket"].isna()]
if len(unmapped):
    print(f"  WARNING — unmapped sub_positions: {unmapped['sub_position'].tolist()}")
else:
    print(f"  All {len(dim_sub_position)} sub_positions mapped successfully")

dim_sub_position = dim_sub_position.dropna(subset=["position_bucket"]).reset_index(drop=True)
dim_sub_position.to_csv(f"{OUT}/dim_sub_position.csv", index=False)
print(f"  {dim_sub_position.to_string(index=False)}")

# ── 6. dim_player ─────────────────────────────────────────────────────────────
print("\n── 6. dim_player ──")
players = players_raw.copy()

# Filter to active players
players = players[players["last_season"] >= 2024].copy()
print(f"  Active players (last_season >= 2024): {len(players)}")

# Resolve nationality: text → country_id
country_lookup = dim_country.set_index("name")["country_id"]
players["citizenship_clean"] = players["country_of_citizenship"].replace(NATIONALITY_CORRECTIONS)
players["nationality_country_id"] = players["citizenship_clean"].map(country_lookup)

null_nat = players["nationality_country_id"].isna().sum()
print(f"  nationality_country_id nulls: {null_nat} ({null_nat/len(players)*100:.1f}%) — countries not in TM's 118")

dim_player = (
    players[[
        "player_id", "name", "date_of_birth",
        "nationality_country_id", "current_club_id", "sub_position",
        "market_value_in_eur", "highest_market_value_in_eur", "last_season"
    ]]
    .rename(columns={
        "market_value_in_eur":         "market_value_eur",
        "highest_market_value_in_eur": "highest_market_value_eur",
    })
    .drop_duplicates("player_id")
    .reset_index(drop=True)
)

mv_null = dim_player["market_value_eur"].isna().sum()
print(f"  market_value_eur nulls: {mv_null} ({mv_null/len(dim_player)*100:.1f}%)")
print(f"  Final dim_player rows: {len(dim_player)}")
dim_player.to_csv(f"{OUT}/dim_player.csv", index=False)

print("\nAll dimension tables written to outputs/intermediate/")
