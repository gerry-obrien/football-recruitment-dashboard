# Cleaning Order

Dimension tables must be cleaned before fact tables. Within dimensions, tables that are referenced by other tables must come first — following the FK chain from 1 to many. This order ensures every foreign key can be resolved at the point it is needed.

---

| # | Output table | Reason |
|---|---|---|
| 1 | dim_country | No dependencies. Referenced by dim_competition (country_id), dim_player (nationality_country_id), and fact_player_season (nationality_country_id). Must exist before any of these can resolve their country FKs. |
| 2 | dim_position_group | No dependencies. Manually created — no source file to read. Referenced by dim_sub_position (position_bucket) and both fact tables. Trivial to produce but must exist before dim_sub_position. |
| 3 | dim_competition | Depends on dim_country (FK: competition.country_id → dim_country). Referenced by dim_club (domestic_competition_id) and both fact tables. Must follow dim_country. |
| 4 | dim_club | Depends on dim_competition (FK: club.domestic_competition_id → dim_competition). Referenced by dim_player (current_club_id) and both fact tables. Must follow dim_competition. |
| 5 | dim_sub_position | Depends on dim_position_group (FK: sub_position.position_bucket → dim_position_group). Referenced by dim_player (sub_position). Must follow dim_position_group. |
| 6 | dim_player | Depends on dim_country (nationality_country_id), dim_club (current_club_id), and dim_sub_position (sub_position) — all three must be complete before dim_player FKs can be resolved. Referenced by both fact tables. This is the last dimension to clean. |
| 7 | fact_player_season | Depends on all six dimension tables. Player FK resolution requires dim_player. Nationality FK requires dim_country. Competition and club FKs require dim_competition and dim_club. Position bucket requires dim_position_group. |
| 8 | fact_performance | Depends on all six dimension tables. Comes last because it also computes performance_index, which requires the full fact_performance dataset to be assembled before percentile ranks can be calculated across the Big 5 position groups. |

---

## Dependency diagram

```
dim_country ──────────────────────────────────────────────────┐
     └──→ dim_competition ──→ dim_club ──→ dim_player ──→ fact_player_season
                                                    └──→ fact_performance
dim_position_group ──→ dim_sub_position ──→ dim_player
```

## Corresponding Python scripts

| Script | Produces |
|---|---|
| `src/01_clean_dimensions.py` | dim_country, dim_competition, dim_club, dim_position_group, dim_sub_position, dim_player |
| `src/02_clean_fifa.py` | fact_player_season → `outputs/player_seasons.csv` (Page 1 final output) |
| `src/03_clean_fbref.py` | fact_performance → `outputs/intermediate/fbref_clean.csv` |
| `src/04_build_players_enriched.py` | joins dim_player + fact_performance → `outputs/players_enriched.csv` (Pages 2/3/4 final output) |

Note: all six dimension CSVs are written to `outputs/intermediate/` and read back by scripts 02, 03, and 04.
