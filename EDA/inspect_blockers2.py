# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
from rapidfuzz import process, fuzz
import warnings
warnings.filterwarnings("ignore")

BASE = r"c:\Users\gerry\OneDrive\GitHub\football-recruitment-dashboard\data"

countries = pd.read_csv(f"{BASE}/transfermarkt/countries.csv", encoding='utf-8')
tm_names = sorted(countries["country_name"].dropna().str.strip().tolist())

print("ALL TM country_name values:")
for n in tm_names:
    print(f"  {n}")
print(f"\nTotal: {len(tm_names)}")

# The 73 unmatched FIFA nationality values from previous run
unmatched = [
    'Afghanistan', 'Angola', 'Antigua and Barbuda', 'Aruba', 'Bahrain',
    'Barbados', 'Belize', 'Benin', 'Bermuda', 'Bosnia and Herzegovina',
    'Botswana', 'Burkina Faso', 'Burundi', 'Cameroon', 'Cape Verde Islands',
    'Central African Republic', 'Chad', 'China PR', 'Congo', 'Congo DR',
    'Cuba', 'Curacao', "Côte d'Ivoire", 'Equatorial Guinea', 'Eritrea',
    'Gabon', 'Gambia', 'Grenada', 'Guam', 'Guinea', 'Guinea Bissau',
    'Guyana', 'Haiti', 'Hong Kong', 'Kenya', 'Korea DPR', 'Korea Republic',
    'Kuwait', 'Liberia', 'Liechtenstein', 'Macau', 'Madagascar', 'Malawi',
    'Mali', 'Mauritania', 'Mauritius', 'Montserrat', 'Mozambique', 'Namibia',
    'New Caledonia', 'Niger', 'Palestine', 'Papua New Guinea',
    'Republic of Ireland', 'Rwanda', 'Saint Kitts and Nevis', 'Saint Lucia',
    'Seychelles', 'Sierra Leone', 'Somalia', 'South Sudan', 'Sudan',
    'Suriname', 'Syria', 'São Tomé e Príncipe', 'Tanzania', 'Togo',
    'Trinidad and Tobago', 'Turkey', 'Vanuatu', 'Yemen', 'Zambia', 'Zimbabwe'
]

print("\n" + "=" * 70)
print("FUZZY MATCH: unmatched FIFA nationalities → nearest TM country_name")
print("=" * 70)
for fifa_name in unmatched:
    result = process.extractOne(fifa_name, tm_names, scorer=fuzz.WRatio)
    if result:
        best_match, score, _ = result
        flag = " *** LIKELY MATCH" if score >= 80 else ""
        print(f"  {fifa_name:<35} → {best_match:<30} (score={score}){flag}")
