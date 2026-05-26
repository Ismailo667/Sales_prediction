import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import plotly.graph_objects as go

# Configuration de la page Streamlit
st.set_page_config(page_title="Carflow Predictor", layout="wide")
st.title("Système d'Analyse et de Prédiction Carflow")
st.write("Ce script automatise le nettoyage de vos rapports de ventes, applique un modèle Random Forest et permet de modifier les contextes mois par mois.")

def parse_carflow_sheet(df):
    """
    Parser spécialisé pour transformer le format croisé Carflow (Mois en colonnes) 
    en un format plat (Time-Series) prêt pour le Machine Learning.
    """
    # 1. Trouver la ligne qui contient les en-têtes de mois
    month_row_idx = None
    for idx, row in df.iterrows():
        if 'JAN' in row.values or 'APR' in row.values:
            month_row_idx = idx
            break
            
    if month_row_idx is None:
        return None

    # 2. Reconstruire les années et les mois
    year_row = df.iloc[month_row_idx - 1].ffill()
    month_row = df.iloc[month_row_idx]
    
    new_headers = []
    liste_mois = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    
    for col_idx in range(len(df.columns)):
        yr = str(year_row.iloc[col_idx]).split('.')[0].strip()
        mnth = str(month_row.iloc[col_idx]).strip()
        
        if mnth in liste_mois:
            new_headers.append(f"{yr}-{mnth}")
        else:
            val_origine = str(df.iloc[month_row_idx].iloc[col_idx]).strip()
            new_headers.append(val_origine if val_origine != 'nan' else f"Col_{col_idx}")

    # 3. Nettoyer le bloc de données
    df_clean = df.iloc[month_row_idx + 1:].copy()
    df_clean.columns = new_headers
    
    label_col = df_clean.columns[0]
    for col in df_clean.columns[:3]:
        if 'Production' in df_clean[col].astype(str).values or 'Retail Sales' in df_clean[col].astype(str).values:
            label_col = col
            break
            
    df_clean[label_col] = df_clean[label_col].astype(str).str.strip()
    
    metrics_recherchees = ['Production', 'Arrival', 'Shipment', 'Retail Sales', 'Stock']
    df_filtered = df_clean[df_clean[label_col].isin(metrics_recherchees)]
    
    if df_filtered.empty:
        return None

    # 4. Melt (Passage Large -> Long)
    date_cols = [c for c in df_clean.columns if '-' in c]
    df_long = pd.melt(df_filtered, id_vars=[label_col], value_vars=date_cols, 
                      var_name='Periode', value_name='Valeur')
    
    df_long['Valeur'] = pd.to_numeric(df_long['Valeur'], errors='coerce').fillna(0)
    
    # 5. Pivot pour réaligner chaque métrique en colonne
    df_final = df_long.pivot_table(index='Periode', columns=label_col, values='Valeur', aggfunc='sum').reset_index()
    
    df_final['Date'] = pd.to_datetime(df_final['Periode'], format='%Y-%b', errors='coerce')
    df_final = df_final.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)
    
    return df_final

# --- Bloc de l'Interface Utilisateur ---

uploaded_file = st.file_uploader("Déposez votre fichier Excel Carflow d'origine", type=["xlsx"])

if uploaded_file is not None:
    excel_file = pd.ExcelFile(uploaded_file)
    onglets = excel_file.sheet_names
    
    st.success(f"Fichier chargé avec succès ! {len(onglets)} onglets détectés.")
    onglet_selectionne = st.selectbox("Choisissez l'onglet (modèle de véhicule) à analyser :", onglets)
    
    df_raw = pd.read_excel(uploaded_file, sheet_name=onglet_selectionne, header=None)
    
    with st.expander("Voir la structure brute de l'onglet Excel"):
        st.dataframe(df_raw.head(10))
        
    with st.spinner("Restructuration de la matrice de données en cours..."):
        df_traite = parse_carflow_sheet(df_raw)
        
    if df_traite is not None:
        st.subheader(f"Données restructurées et prêtes pour le Machine Learning ({onglet_selectionne})")
        st.dataframe(df_traite)
        
        colonnes_dispo = df_traite.columns.tolist()
        
        st.sidebar.header("Configuration du Modèle")
        col_cible = st.sidebar.selectbox("Variable à prédire (Target)", [c for c in ['Retail Sales', 'Stock'] if c in colonnes_dispo])
        col_features = st.sidebar.multiselect(
            "Variables explicatives (Contextes)", 
            [c for c in ['Production', 'Arrival', 'Shipment', 'Stock'] if c != col_cible and c in colonnes_dispo], 
            default=[c for c in ['Production', 'Arrival'] if c in colonnes_dispo]
        )
        
        st.sidebar.subheader("Simuler des variables externes")
        add_context = st.sidebar.checkbox("Ajouter Facteurs Marketing/Prix")
        
        if add_context:
            if 'Budget_Marketing' not in df_traite.columns:
                df_traite['Budget_Marketing'] = np.random.uniform(2000, 8000, size=len(df_traite))
                df_traite['Prix_Carburant'] = np.random.uniform(1.75, 1.95, size=len(df_traite))
            if 'Budget_Marketing' not in col_features:
                col_features.extend(['Budget_Marketing', 'Prix_Carburant'])

        # --- ENTRAÎNEMENT ---
        if st.button("Lancer l'entraînement du Random Forest"):
            if not col_features:
                st.error("Veuillez sélectionner au moins une variable explicative.")
            else:
                df_traite['Mois'] = df_traite['Date'].dt.month
                features_finales = col_features + ['Mois']
                
                X = df_traite[features_finales]
                y = df_traite[col_cible]
                
                model_rf = RandomForestRegressor(n_estimators=50, random_state=42)
                model_rf.fit(X, y)
                
                st.session_state['modele'] = model_rf
                st.session_state['features'] = features_finales
                st.session_state['df_traite'] = df_traite
                st.session_state['col_cible'] = col_cible
                
                st.success("Modèle entraîné et sauvegardé en mémoire !")

        # --- EDITEUR DE SCÉNARIO MOIS PAR MOIS & GRAPHIQUE ---
        if 'modele' in st.session_state:
            model_rf = st.session_state['modele']
            features_finales = st.session_state['features']
            df_m = st.session_state['df_traite']
            c_cible = st.session_state['col_cible']
            
            st.markdown("---")
            st.header("🔮 Construction du Scénario Prévisionnel")
            
            # Paramètres de l'horizon de simulation
            col1, col2 = st.columns(2)
            with col1:
                horizon = st.slider("Horizon total de la courbe de prédiction (en mois)", 1, 24, 12)
            with col2:
                max_offset = max(0, len(df_m) - 1)
                offset = st.slider("Offset (Recul dans l'historique en mois)", 0, max_offset, min(6, max_offset))
            
            # 1. Génération de l'axe temporel de la prédiction
            dates_projection = []
            total_history = len(df_m)
            
            for k in range(horizon):
                idx = total_history - offset + k
                if idx < total_history:
                    date_courante = df_m['Date'].iloc[idx]
                else:
                    months_ahead = idx - total_history + 1
                    date_courante = df_m['Date'].iloc[-1] + pd.DateOffset(months=months_ahead)
                dates_projection.append(date_courante)
            
            # 2. Construction de la matrice initiale à afficher dans le st.data_editor
            features_sans_mois = [f for f in features_finales if f != 'Mois']
            init_rows = []
            
            for k in range(horizon):
                idx = total_history - offset + k
                row_dict = {"Période": dates_projection[k].strftime('%Y-%b')}
                
                if idx < total_history:
                    # Remplissage automatique avec le réel historique pour la zone d'offset
                    real_row = df_m.iloc[idx]
                    for f in features_sans_mois:
                        row_dict[f] = float(real_row[f])
                    row_dict["Type de Ligne"] = "Historique (Vrai Contexte)"
                else:
                    # Remplissage par défaut avec la moyenne pour les lignes futures
                    for f in features_sans_mois:
                        row_dict[f] = round(float(df_m[f].mean()), 1)
                    row_dict["Type de Ligne"] = "Futur (À ajuster si besoin)"
                
                init_rows.append(row_dict)
                
            df_scenario_init = pd.DataFrame(init_rows)
            
            st.write("### 📝 Lignes de contexte configurées :")
            st.caption("Double-cliquez sur une case numérique pour modifier le contexte de ce mois spécifique (ex: augmenter la production d'un mois futur ou changer le budget marketing).")
            
            # Affichage du tableau éditable
            df_scenario_edite = st.data_editor(
                df_scenario_init,
                disabled=["Période", "Type de Ligne"], # Bloquer la modification des colonnes indicatrices
                use_container_width=True,
                key="editor_carflow_context"
            )
            
            # 3. Calcul lors du clic sur le bouton
            if st.button("Calculer la prévision globale et mettre à jour le graphe"):
                val_preds = []
                
                # Exécuter l'algorithme ligne par ligne sur la matrice modifiée
                for k in range(horizon):
                    date_courante = dates_projection[k]
                    row_edite = df_scenario_edite.iloc[k]
                    
                    vecteur_prediction = []
                    for f in features_finales:
                        if f == 'Mois':
                            vecteur_prediction.append(date_courante.month)
                        else:
                            vecteur_prediction.append(row_edite[f])
                    
                    res = model_rf.predict([vecteur_prediction])
                    val_preds.append(max(0, int(res[0])))
                
                # --- STRUCTURE DU GRAPHIQUE COMPATIBLE OFFSET ---
                st.write(f"### Évolution et Simulation de : {c_cible}")
                
                fig = go.Figure()
                
                # Trace 1 : Historique Réel complet issu du fichier importé
                fig.add_trace(go.Scatter(
                    x=df_m['Date'], 
                    y=df_m[c_cible],
                    mode='lines+markers',
                    name='Historique Complet (Réel)',
                    line=dict(color='#1f77b4', width=3),
                    marker=dict(size=6)
                ))
                
                # Connexion graphique fluide : on rattache le début des pointillés au point réel juste avant l'offset
                conn_idx = total_history - offset - 1
                if conn_idx >= 0:
                    dates_plot = [df_m['Date'].iloc[conn_idx]] + dates_projection
                    vals_plot = [df_m[c_cible].iloc[conn_idx]] + val_preds
                else:
                    dates_plot = dates_projection
                    vals_plot = val_preds

                # Trace 2 : Courbe de projection Random Forest (générée à partir de vos lignes éditées)
                fig.add_trace(go.Scatter(
                    x=dates_plot,
                    y=vals_plot,
                    mode='lines+markers',
                    name='Courbe Prévisionnelle (Modèle ML)',
                    line=dict(color='#ff7f0e', width=3, dash='dash'),
                    marker=dict(size=7, symbol='diamond')
                ))
                
                fig.update_layout(
                    xaxis_title='Période',
                    yaxis_title=f'Volume ({c_cible})',
                    hovermode='x unified',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
    else:
        st.error("Impossible de détecter la structure attendue dans cet onglet.")
