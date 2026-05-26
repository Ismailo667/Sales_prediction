import pandas as pd
import numpy as np

# Configuration
np.random.seed(42)
months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
years = [2022, 2023, 2024]

# Création des en-têtes (Format Carflow)
row1 = ['Test Model', '']
row2 = ['', '']
for y in years:
    row1.extend([str(y)] + [''] * 11 + ['TTL'])
    row2.extend(months + ['TTL'])

# Initialisation des lignes de données
data_rows = {
    'Production': ['Production ', ''],
    'Shipment': ['Shipment', ''],
    'Arrival': ['Arrival', ''],
    'Retail Sales': ['Retail Sales', ''],
    'Stock': ['Stock', '']
}

stock_current = 50

# Génération des données mois par mois
for y in years:
    prod_yr, ship_yr, arr_yr, retail_yr = 0, 0, 0, 0
    
    for m in months:
        prod = int(np.random.normal(120, 30))
        ship = int(prod * 0.95 + np.random.normal(0, 10))
        arr = int(ship * 0.90 + np.random.normal(0, 10))
        
        saisonnalite = 1.2 if m in ['OCT', 'NOV', 'DEC'] else 1.0
        retail = int(arr * 0.85 * saisonnalite + np.random.normal(5, 5))
        
        stock_current = stock_current + arr - retail
        
        data_rows['Production'].append(max(0, prod))
        data_rows['Shipment'].append(max(0, ship))
        data_rows['Arrival'].append(max(0, arr))
        data_rows['Retail Sales'].append(max(0, retail))
        data_rows['Stock'].append(max(0, stock_current))
        
        prod_yr += max(0, prod)
        ship_yr += max(0, ship)
        arr_yr += max(0, arr)
        retail_yr += max(0, retail)
        
    data_rows['Production'].append(prod_yr)
    data_rows['Shipment'].append(ship_yr)
    data_rows['Arrival'].append(arr_yr)
    data_rows['Retail Sales'].append(retail_yr)
    data_rows['Stock'].append('')

# Assemblage
rows = [row1, row2, data_rows['Production'], data_rows['Shipment'], data_rows['Arrival'], data_rows['Retail Sales'], data_rows['Stock']]

df = pd.DataFrame(rows)

# Sauvegarde
df.to_excel("Fichier_Test_Format_Carflow.xlsx", index=False, header=False, sheet_name="Test Model")
print("✅ Fichier 'Fichier_Test_Format_Carflow.xlsx' généré avec succès dans le dossier actuel !")
