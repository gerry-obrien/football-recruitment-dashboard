# Data Cleaning Blockers and Resolutions

Seven blockers identified during data analysis. Each has a decision recorded below.

---

## Blocker 1 — TM player nationality column name
**Status: RESOLVED** (confirmed by reading players.csv header)

The nationality field is `country_of_citizenship` and contains text country names (e.g. "Germany", "Poland") — it is NOT a foreign key to countries.csv.

**Decision:** In the dim_player cleaning script, resolve `country_of_citizenship` to `nationality_country_id` via a left join against dim_country on `dim_country.name`. Players with no matching country name receive `nationality_country_id = null`. This is expected to be rare (mainly historical or retired players).

---

## Blocker 2 — FIFA nationality_name → dim_country name mismatches
**Status: RESOLVED** (anti-join run against all 178 distinct FIFA nationality values)

TM countries.csv has only 118 countries. Of 178 distinct FIFA nationality_name values, 105 matched exactly and 73 did not. The 73 split into two groups:

**Group A — naming differences (6 values, fixable with correction dict):**

| FIFA nationality_name | TM country_name |
|---|---|
| Bosnia and Herzegovina | Bosnia-Herzegovina |
| China PR | China |
| Hong Kong | Hongkong |
| Republic of Ireland | Ireland |
| Korea Republic | Korea, South |
| Turkey | Türkiye |

**Group B — countries genuinely absent from TM's 118-country database (67 values):**
These include Angola, Cameroon, Côte d'Ivoire, Congo DR, Burkina Faso, Mali, Senegal... wait — Senegal IS matched. The absent ones include: Afghanistan, Angola, Antigua and Barbuda, Aruba, Bahrain, Barbados, Belize, Benin, Bermuda, Botswana, Burkina Faso, Burundi, Cameroon, Cape Verde Islands, Central African Republic, Chad, Congo, Congo DR, Cuba, Curacao, Côte d'Ivoire, Equatorial Guinea, Eritrea, Gabon, Gambia, Grenada, Guam, Guinea, Guinea Bissau, Guyana, Haiti, Kenya, Korea DPR, Kuwait, Liberia, Liechtenstein, Macau, Madagascar, Malawi, Mali, Mauritania, Mauritius, Montserrat, Mozambique, Namibia, New Caledonia, Niger, Palestine, Papua New Guinea, Rwanda, Saint Kitts and Nevis, Saint Lucia, Seychelles, Sierra Leone, Somalia, South Sudan, Sudan, Suriname, Syria, São Tomé e Príncipe, Tanzania, Togo, Trinidad and Tobago, Vanuatu, Yemen, Zambia, Zimbabwe.

**Decision:** Apply the 6-entry correction dict before the FK join. Players from Group B countries receive `nationality_country_id = null` and are excluded from the Page 1 choropleth. Disclose this as a limitation in the report — TM's country scope determines which nationalities are visible on the map.

**Correction dict for cleaning script:**
```python
NATIONALITY_CORRECTIONS = {
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "China PR": "China",
    "Hong Kong": "Hongkong",
    "Republic of Ireland": "Ireland",
    "Korea Republic": "Korea, South",
    "Turkey": "Türkiye",
}
```

---

## Blocker 3 — FBref multi-row players (mid-season transfers)
**Status: MUST RESOLVE before fact_performance script**

Players who transferred mid-season appear on multiple rows in FBref with different Squad and Comp. Per-90 stats cannot be averaged row-by-row — this produces wrong rates.

**Decision:** Before computing any per-90 stats:
1. Sum all counting stats (xG, npxG, xAG, Ast, KP, G-PK, Tkl, Int, Clr, Err, PrgP, PrgC, PrgR, GA, Saves, CS, MP) across rows for the same player.
2. Sum 90s across rows to get total minutes.
3. Divide summed counting stats by summed 90s to get per-90 values.
4. Recompute Save% = Saves / (GA + Saves) and CS% = CS / MP from the summed counts — do NOT average the percentage columns directly.
5. Primary competition and club = whichever row had the most 90s for that player.

---

## Blocker 4 — Minimum minutes threshold not yet decided
**Status: DECIDED here**

Players with very few minutes have extreme per-90 rates that distort percentile ranks (e.g. a player who played 90 minutes and scored once has goals_non_pen/90 = 1.0, ranking above Haaland).

**Decision:** Filter to `90s >= 5` (450 minutes played) before computing percentile ranks and performance_index. This is a standard FBref convention for meaningful statistics. Players below this threshold are excluded from fact_performance entirely. Disclose this filter in the report.

---

## Blocker 5 — FBref Comp prefix verification
**Status: RESOLVED** (confirmed by running distinct value check on FBref file)

After stripping the first word, the five distinct Comp values are exactly:
- Premier League → GB1
- La Liga → ES1
- Serie A → IT1
- Ligue 1 → FR1
- Bundesliga → L1

**Competition mapping dict for cleaning script:**
```python
COMP_TO_COMPETITION_ID = {
    "Premier League": "GB1",
    "La Liga": "ES1",
    "Serie A": "IT1",
    "Ligue 1": "FR1",
    "Bundesliga": "L1",
}
```

Row counts: Serie A 634, La Liga 601, Premier League 574, Ligue 1 553, Bundesliga 492. Total 2,854 rows confirmed.

---

## Blocker 6 — FIFA club_name → dim_club FK quality
**Status: DECIDED here**

FIFA club names are free text and rarely match TM club names exactly. The club_id FK in fact_player_season is not displayed in any dashboard page (we never show FIFA club data).

**Decision:** Use exact string match only — no fuzzy matching for clubs. Accept the resulting high null rate for `club_id` in fact_player_season. Document the null rate in the report. Do not invest cleaning effort in an FK that has no dashboard impact.

---

## Blocker 7 — dim_competition scope (Big 5 only vs all domestic leagues)
**Status: DECIDED here**

fact_player_season covers all FIFA players globally (needed for the nationality choropleth). Most players are in non-Big 5 leagues. If dim_competition is filtered to Big 5 only, `competition_id` would be null for the majority of fact_player_season rows, and dim_club would have broken FK references for non-Big 5 clubs.

**Decision:** dim_competition keeps ALL domestic leagues from TM (filter `type == 'domestic_league'`, approximately 300 rows). The Big 5 filter is applied only at the fact_performance level (FBref data is already Big 5 only). This preserves FK integrity throughout the schema.

---

## Blocker 8 — TM CSV encoding (new, found during Blocker 1 investigation)
**Status: DECIDED here**

Reading players.csv without specifying encoding produces garbled characters for non-ASCII club and player names (e.g. "SocietÃ " instead of "Società"). This will corrupt name-matching steps.

**Decision:** All TM CSV reads must use `pd.read_csv(..., encoding='utf-8')`. If any file fails with UTF-8, fall back to `encoding='utf-8-sig'` (UTF-8 with BOM). Do NOT use the system default encoding. Apply this to all four TM files: players.csv, clubs.csv, competitions.csv, countries.csv.
