import pandas as pd
import warnings
warnings.filterwarnings("ignore")

BASE = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\data"

# ─── FIFA ────────────────────────────────────────────────────────────────────
print("=" * 70)
print("FIFA male_players.csv  (first 1000 rows)")
print("=" * 70)
df = pd.read_csv(f"{BASE}/fifa/male_players.csv", nrows=1000)
print("Shape:", df.shape)
print("Columns:", list(df.columns))
print()
expected = ["fifa_version","short_name","nationality_name","club_name",
            "league_name","overall","potential","value_eur","wage_eur",
            "player_positions","age"]
missing = [c for c in expected if c not in df.columns]
print("Missing expected cols:", missing if missing else "None")
print()
print("fifa_version values:", sorted(df["fifa_version"].unique()) if "fifa_version" in df.columns else "MISSING")
print()
print("Null counts in expected cols:")
for c in expected:
    if c in df.columns:
        n = df[c].isnull().sum()
        print(f"  {c}: {n}/1000 nulls  | dtype={df[c].dtype}")
print()
sub = [c for c in expected if c in df.columns]
print("Sample (5 rows):")
print(df[sub].head(5).to_string())

# ─── TRANSFERMARKT ───────────────────────────────────────────────────────────
print()
for name in ["players","clubs","competitions","countries","transfers","player_valuations"]:
    print("=" * 70)
    print(f"transfermarkt/{name}.csv")
    print("=" * 70)
    df = pd.read_csv(f"{BASE}/transfermarkt/{name}.csv")
    print("Shape:", df.shape)
    print("Columns:", list(df.columns))
    nulls = df.isnull().sum()
    pct   = (nulls / len(df) * 100).round(1)
    nn    = pct[pct > 0]
    if len(nn):
        print("Null%:")
        for col, p in nn.items():
            print(f"  {col}: {p}%  ({nulls[col]} rows)")
    print("Head(3):")
    print(df.head(3).to_string())
    print()

# ─── FBREF ───────────────────────────────────────────────────────────────────
print("=" * 70)
print("FBref players_data_2024_2025.csv")
print("=" * 70)
df = pd.read_csv(f"{BASE}/fbref/players_data_2024_2025.csv")
print("Shape:", df.shape)
print("Columns:", list(df.columns))
expected_fb = ["Player","Nation","Pos","Squad","Comp","Age","Born","MP","Starts",
               "Min","90s","Gls","Ast","xG","xAG","npxG","G-PK","KP",
               "Tkl","TklW","Blocks","Int","Clr","Err",
               "PrgP","PrgC","Cmp%_stats_passing","PPA",
               "GA","Saves","Save%","CS","CS%","PKsv",
               "Touches","Carries","PrgR","Mis","Dis","CrdY","CrdR","Recov"]
missing = [c for c in expected_fb if c not in df.columns]
print("Missing expected cols:", missing if missing else "None")
print()
print("Comp values:", df["Comp"].unique() if "Comp" in df.columns else "MISSING")
print("Pos values:", df["Pos"].unique() if "Pos" in df.columns else "MISSING")
print()
nulls = df.isnull().sum()
pct   = (nulls / len(df) * 100).round(1)
nn    = pct[pct > 5]
if len(nn):
    print("Cols >5% null:")
    for col, p in nn.items():
        print(f"  {col}: {p}%")
print()
print("Head(3):")
print(df.head(3).to_string())
