# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import warnings
warnings.filterwarnings("ignore")

BASE = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\data"

# ── dim_country ───────────────────────────────────────────────────────────────
print("=== dim_country (countries.csv) ===")
df = pd.read_csv(f"{BASE}/transfermarkt/countries.csv")
print("Dtypes:", dict(df.dtypes))
print("country_id range:", df["country_id"].min(), "-", df["country_id"].max())
print("country_code samples:", list(df["country_code"].dropna().head(8)))
print("confederation values:", df["confederation"].unique())
print()

# ── dim_competition ───────────────────────────────────────────────────────────
print("=== dim_competition (competitions.csv, domestic only) ===")
df = pd.read_csv(f"{BASE}/transfermarkt/competitions.csv")
dom = df[df["type"] == "domestic_league"]
print("Dtypes:", dict(dom.dtypes))
print("competition_id samples:", list(dom["competition_id"].head(10)))
print("competition_id dtype:", dom["competition_id"].dtype)
print("country_id dtype:", dom["country_id"].dtype)
print("country_id range:", dom["country_id"].min(), "-", dom["country_id"].max())
print("All Big 5 IDs:")
big5_names = ["premier-league","laliga","bundesliga","serie-a","ligue-1"]
print(dom[dom["competition_code"].isin(big5_names)][["competition_id","competition_code","name","country_name"]].to_string())
print()

# ── dim_club ──────────────────────────────────────────────────────────────────
print("=== dim_club (clubs.csv) ===")
df = pd.read_csv(f"{BASE}/transfermarkt/clubs.csv")
print("Dtypes:", dict(df.dtypes))
print("club_id dtype:", df["club_id"].dtype)
print("club_id samples:", list(df["club_id"].head(8)))
print("domestic_competition_id samples:", list(df["domestic_competition_id"].dropna().head(8)))
print("squad_size nulls:", df["squad_size"].isnull().sum())
print()

# ── dim_player ────────────────────────────────────────────────────────────────
print("=== dim_player (players.csv) ===")
df = pd.read_csv(f"{BASE}/transfermarkt/players.csv")
print("Dtypes:", dict(df[["player_id","current_club_id","market_value_in_eur",
                           "highest_market_value_in_eur","date_of_birth",
                           "sub_position","position","last_season"]].dtypes))
print("player_id range:", df["player_id"].min(), "-", df["player_id"].max())
print("current_club_id dtype:", df["current_club_id"].dtype)
print("sub_position unique values:", sorted(df["sub_position"].dropna().unique()))
print("position unique values:", df["position"].dropna().unique())
print("market_value_in_eur dtype:", df["market_value_in_eur"].dtype)
print("date_of_birth sample:", list(df["date_of_birth"].dropna().head(3)))
print()

# ── fact_player_season ────────────────────────────────────────────────────────
print("=== fact_player_season (male_players.csv v19/21/23 sample) ===")
cols = ["fifa_version","player_id","overall","potential","value_eur",
        "nationality_name","player_positions"]
chunks = pd.read_csv(f"{BASE}/fifa/male_players.csv",
                     usecols=cols, chunksize=200000)
sample = pd.concat([c[c["fifa_version"].isin([19,21,23])] for c in chunks])
print("Dtypes:", dict(sample.dtypes))
print("overall range:", sample["overall"].min(), "-", sample["overall"].max())
print("potential range:", sample["potential"].min(), "-", sample["potential"].max())
print("value_eur dtype:", sample["value_eur"].dtype)
print("value_eur null %:", round(sample["value_eur"].isnull().sum()/len(sample)*100,1))
print("player_positions samples:", list(sample["player_positions"].dropna().unique()[:12]))
print("player_id dtype:", sample["player_id"].dtype)
print()

# ── fact_performance ──────────────────────────────────────────────────────────
print("=== fact_performance (fbref) ===")
df = pd.read_csv(f"{BASE}/fbref/players_data_2024_2025.csv")
key_cols = ["Player","Squad","Comp","Pos","Age","Born","MP","Starts","Min","90s",
            "xG","npxG","xAG","Ast","KP","G-PK",
            "Tkl","TklW","Int","Clr","Err","PrgP","PrgC","PrgR",
            "Touches","Carries","Recov","Mis","Dis",
            "GA","Saves","Save%","CS","CS%","PKsv",
            "CrdY","CrdR"]
present = [c for c in key_cols if c in df.columns]
missing = [c for c in key_cols if c not in df.columns]
print("Present:", present)
print("Missing:", missing)
print()
print("Dtypes of key cols:")
for c in present:
    print(f"  {c}: {df[c].dtype}  nulls={df[c].isnull().sum()}")
print()
print("90s range:", df["90s"].min(), "-", df["90s"].max())
print("MP range:", df["MP"].min(), "-", df["MP"].max())
print("Comp values after strip:")
df["Comp_clean"] = df["Comp"].str.split(" ", n=1).str[1]
print(df["Comp_clean"].unique())
