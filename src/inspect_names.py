# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import warnings
warnings.filterwarnings("ignore")

BASE = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\data"

players = pd.read_csv(f"{BASE}/transfermarkt/players.csv")
fbref   = pd.read_csv(f"{BASE}/fbref/players_data_2024_2025.csv", usecols=["Player","Squad","Comp"])

fifa_cols = ["fifa_version","short_name","club_name","league_name","overall"]
chunks = pd.read_csv(f"{BASE}/fifa/male_players.csv", usecols=fifa_cols, chunksize=200000)
fifa_v23 = pd.concat([c[c["fifa_version"]==23] for c in chunks])

def norm(s):
    return s.str.strip().str.lower()

fifa_names  = set(norm(fifa_v23["short_name"].dropna()))
fbref_names = set(norm(fbref["Player"].dropna()))
tm_names    = set(norm(players["name"].dropna()))

print(f"FIFA v23 unique names: {len(fifa_names)}")
print(f"FBref unique names:    {len(fbref_names)}")
print(f"TM unique names:       {len(tm_names)}")
print()

exact_fifa_fbref = fifa_names & fbref_names
exact_fbref_tm   = fbref_names & tm_names
exact_fifa_tm    = fifa_names & tm_names

print(f"Exact overlap FIFA v23 + FBref:        {len(exact_fifa_fbref):4d}  ({len(exact_fifa_fbref)/len(fbref_names)*100:.1f}% of FBref)")
print(f"Exact overlap FBref + Transfermarkt:   {len(exact_fbref_tm):4d}  ({len(exact_fbref_tm)/len(fbref_names)*100:.1f}% of FBref)")
print(f"Exact overlap FIFA v23 + Transfermarkt: {len(exact_fifa_tm):4d}  ({len(exact_fifa_tm)/len(tm_names)*100:.1f}% of TM)")

unmatched = fbref_names - fifa_names
print(f"\nFBref players NOT found in FIFA v23: {len(unmatched)}")
print("Examples (first 20):", sorted(list(unmatched))[:20])

print()
print("FBref competition breakdown:")
print(fbref["Comp"].value_counts().to_string())

# Also check if FIFA v23 covers Big 5 leagues
print()
print("FIFA v23 Big 5 league player counts:")
big5 = ["Premier League","La Liga","Bundesliga","Serie A","Ligue 1"]
for lg in big5:
    n = (fifa_v23["league_name"] == lg).sum()
    print(f"  {lg}: {n}")

# Overall rating distribution in FIFA v23
print()
print("FIFA v23 overall rating distribution:")
print(fifa_v23["overall"].describe().round(1))
print("Players by rating bucket:")
bins = [0,59,69,74,79,84,94]
labels = ["<60","60-69","70-74","75-79","80-84","85+"]
fifa_v23["rating_bucket"] = pd.cut(fifa_v23["overall"], bins=bins, labels=labels)
print(fifa_v23["rating_bucket"].value_counts().sort_index().to_string())
