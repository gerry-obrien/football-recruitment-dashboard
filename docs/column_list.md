# Definitive Column List

For each output CSV, only columns that appear in the galaxy schema or are needed as join keys during cleaning are kept. Everything else is dropped.

---

## dim_country.csv
**Source:** `data/transfermarkt/countries.csv`
**Filter:** none

| Raw column | Output column | Notes |
|---|---|---|
| country_id | country_id | PK |
| name | name | |
| country_code | country_code | TM internal code e.g. ARM1, not ISO 3166-1 |
| confederation | confederation | |

**Drop:** all other columns if present.

---

## dim_competition.csv
**Source:** `data/transfermarkt/competitions.csv`
**Filter:** `type == 'domestic_league'` — keeps all domestic leagues worldwide (not Big 5 only — see Blocker 7)

| Raw column | Output column | Notes |
|---|---|---|
| competition_id | competition_id | PK e.g. GB1, ES1, IT1, FR1, L1 |
| name | name | |
| country_id | country_id | FK → dim_country |
| type | type | always 'domestic_league' after filter |

**Drop:** competition_code, country_name, sub_type, confederation.

---

## dim_club.csv
**Source:** `data/transfermarkt/clubs.csv`
**Filter:** none — all clubs kept to support dim_player FK chain across all active players

| Raw column | Output column | Notes |
|---|---|---|
| club_id | club_id | PK |
| name | name | |
| domestic_competition_id | domestic_competition_id | FK → dim_competition |
| squad_size | squad_size | |

**Drop:** coach_name, stadium_name, net_transfer_record, average_age, foreigners_number, national_team_players, stadium_seats, url, and all other columns.

---

## dim_position_group.csv
**Source:** manually created — no raw file
**Filter:** n/a

| Output column | Values |
|---|---|
| position_bucket | GK, Centre-Back, Full-Back, Midfielder, Winger, Striker |
| display_order | 1, 2, 3, 4, 5, 6 |

Written as a hardcoded dict in the cleaning script.

---

## dim_sub_position.csv
**Source:** `data/transfermarkt/players.csv` (distinct sub_position values only)
**Filter:** n/a — take all 13 distinct values

| Raw column | Output column | Notes |
|---|---|---|
| sub_position | sub_position | PK — 13 distinct TM values |
| — | position_bucket | derived: apply manual mapping dict → FK → dim_position_group |

**Mapping dict:**

| sub_position | position_bucket |
|---|---|
| Goalkeeper | GK |
| Centre-Back | Centre-Back |
| Left-Back | Full-Back |
| Right-Back | Full-Back |
| Left Wing Back | Full-Back |
| Right Wing Back | Full-Back |
| Defensive Midfield | Midfielder |
| Central Midfield | Midfielder |
| Attacking Midfield | Midfielder |
| Left Midfield | Midfielder |
| Right Midfield | Midfielder |
| Left Winger | Winger |
| Right Winger | Winger |
| Centre-Forward | Striker |
| Second Striker | Striker |

Verify exact distinct values from players.csv before finalising — the list above may not be exhaustive.

---

## dim_player.csv
**Source:** `data/transfermarkt/players.csv`
**Filter:** `last_season >= 2024`

| Raw column | Output column | Notes |
|---|---|---|
| player_id | player_id | PK |
| name | name | full display name |
| date_of_birth | date_of_birth | |
| country_of_citizenship | nationality_country_id | derived: text name resolved to FK → dim_country via join on dim_country.name (see Blocker 1) |
| current_club_id | current_club_id | FK → dim_club |
| sub_position | sub_position | FK → dim_sub_position |
| market_value_in_eur | market_value_eur | rename only |
| highest_market_value_in_eur | highest_market_value_eur | rename only |
| last_season | last_season | |

**Drop:** first_name, last_name, player_code, country_of_birth, city_of_birth, foot, height_in_cm, contract_expiration_date, agent_name, image_url, international_caps, international_goals, current_national_team_id, url, current_club_domestic_competition_id, current_club_name, position.

---

## fact_player_season.csv
**Sources:** `data/fifa/male_players.csv` + dim tables for FK resolution
**Filter:** `fifa_version IN (19, 21, 23)`, deduplicate to one row per player per version (keep highest `fifa_update`). All FIFA players kept — not filtered to Big 5 (needed for global nationality choropleth).

| Raw column | Output column | Notes |
|---|---|---|
| — | id | derived: surrogate key (row index after dedup) |
| long_name | player_id | derived: fuzzy match long_name → dim_player.name via rapidfuzz WRatio ≥ 90. Nullable. Drop long_name after matching. |
| nationality_name | nationality_country_id | derived: text name mapped to dim_country.country_id via correction dict then join. Populated for ALL rows including where player_id is null. Drop nationality_name after. |
| league_name | competition_id | derived: FIFA text league name mapped to dim_competition.competition_id. Null for leagues not in TM. Drop league_name after. |
| club_name | club_id | derived: exact string match against dim_club.name. High null rate expected and accepted (see Blocker 6). Drop club_name after. |
| player_positions | position_bucket | derived: take first listed position code, apply FIFA → position_bucket mapping dict. Drop player_positions after. |
| fifa_version | fifa_version | keep — degenerate dimension |
| overall | overall | keep |
| potential | potential | keep |
| value_eur | value_eur | keep |

**Also needed during cleaning but not in output:** `fifa_update` (for deduplication), `short_name` (fallback for player matching).

**FIFA position code → position_bucket mapping:**

| FIFA code | position_bucket |
|---|---|
| GK | GK |
| CB | Centre-Back |
| LB, RB, LWB, RWB | Full-Back |
| CDM, CM, CAM, LM, RM | Midfielder |
| LW, RW | Winger |
| CF, ST | Striker |

---

## fact_performance.csv
**Sources:** `data/fbref/players_data_2024_2025.csv` + dim tables for FK resolution
**Filter:** `90s >= 5` (450 minutes minimum — see Blocker 4). Aggregate multi-row players before computing per-90s (see Blocker 3).

| Raw column | Output column | Notes |
|---|---|---|
| Player | player_id | derived: exact then rapidfuzz match → dim_player.player_id. Drop after. |
| Comp | competition_id | derived: strip country prefix, map cleaned name → dim_competition.competition_id. Primary competition by minutes. |
| Squad | club_id | derived: exact match → dim_club.club_id. Primary club by minutes. |
| Pos | position_bucket | derived: take first listed code, apply FBref → position_bucket mapping dict. |
| — | season | derived: constant string "2024-25" |
| 90s | minutes_90s | rename only |
| xG | xg_per90 | derived: xG / 90s |
| npxG | npxg_per90 | derived: npxG / 90s |
| xAG | xag_per90 | derived: xAG / 90s |
| Ast | ast_per90 | derived: Ast / 90s |
| KP | key_passes_per90 | derived: KP / 90s |
| G-PK | goals_non_pen_per90 | derived: G-PK / 90s |
| Tkl | tackles_per90 | derived: Tkl / 90s |
| Int | interceptions_per90 | derived: Int / 90s |
| Clr | clearances_per90 | derived: Clr / 90s |
| Err | errors_per90 | derived: Err / 90s |
| PrgP | prog_passes_per90 | derived: PrgP / 90s |
| PrgC | prog_carries_per90 | derived: PrgC / 90s |
| PrgR | prog_receptions_per90 | derived: PrgR / 90s |
| Save% | save_pct | rename only — already a rate, not divided by 90s |
| CS% | cs_pct | rename only — already a rate. Recompute from CS/MP after aggregation (see Blocker 3). |
| GA | ga_per90 | derived: GA / 90s |
| — | performance_index | derived: mean percentile rank of position-relevant metrics within Big 5 position group |

**Drop:** Nation, Age, Born, MP, Starts, Min, TklW, Touches, Carries, Recov, Mis, Dis, PKsv, CrdY, CrdR, CS (count version), Saves (count version — used for recomputing Save% then dropped).

**FBref position code → position_bucket mapping:**

| FBref code | position_bucket |
|---|---|
| GK | GK |
| DF | Centre-Back |
| DF (LB/RB context) | Full-Back |
| MF | Midfielder |
| FW | Winger or Striker |

Note: FBref uses DF/MF/FW which are less granular than FIFA codes. Where Pos is compound (e.g. "DF,MF"), take the first value only.
