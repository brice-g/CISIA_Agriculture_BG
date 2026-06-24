"""
Interface Utilisateur Streamlit - Projet CISIA
Description : Portail d'aide à la décision agronomique connecté à FastAPI.
              Intègre la visualisation des risques, l'explicabilité (XAI),
              la collecte de feedbacks terrain et le monitoring du Concept Drift.
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
from src.database.db_manager import DatabaseManager
import pydeck as pdk

# Initialise l'ID sélectionné dans la session pour qu'il survive aux rechargements
if "selected_parcelle_id" not in st.session_state:
    st.session_state["selected_parcelle_id"] = None

# Configuration de la page Streamlit
st.set_page_config(
    page_title="CISIA - Interface Opérationnelle MLOps",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# URL de l'API FastAPI (Backend centralisé)
API_BASE_URL = "http://localhost:8000"

# -------------------------------------------------------------------------
# SEUILS AGRONOMIQUES CENTRAUX (Source unique de vérité Métier & XAI)
# -------------------------------------------------------------------------
SEUIL_STRESS_CRITIQUE = 500.0
SEUIL_STRESS_WARNING = 300.0

SEUIL_NDVI_CRITIQUE = -0.12
SEUIL_NDVI_WARNING = -0.05

SEUIL_RENDEMENT_CRITIQUE = 0.75
SEUIL_RENDEMENT_WARNING = 0.85

st.title("Plateforme d'Aide à la Décision - Suivi des Anomalies")

# -------------------------------------------------------------------------
# STRUCTURE GÉOCLIMATIQUE ET JITTER DÉTERMINISTE
# -------------------------------------------------------------------------
REGION_CENTROIDS = {
    "Occitanie": (43.60, 1.44),
    "Nouvelle-Aquitaine": (44.83, -0.57),
    "Centre-Val de Loire": (47.90, 1.90),
    "Grand Est": (48.58, 7.75),
    "Bretagne": (48.11, -1.67)
}

def apply_deterministic_jitter(row):
    """
    Calcule des coordonnées uniques et fixes pour chaque parcelle
    en appliquant un décalage basé sur le hash de son identifiant de parcelle.
    """
    base_lat, base_lon = REGION_CENTROIDS.get(row['region'], (46.5, 2.5))
    
    # Utilisation d'un hash reproductible pour stabiliser la position sur la carte
    hash_val = int(pd.util.hash_pandas_object(pd.Series([row['parcelle_id']])).iloc[0])
    
    # Décalage fin pour étaler les parcelles sans chevauchement exact
    lat_jitter = ((hash_val % 300) - 150) / 1000.0
    lon_jitter = (((hash_val // 300) % 300) - 150) / 1000.0
    
    return pd.Series([base_lat + lat_jitter, base_lon + lon_jitter])


@st.cache_data(ttl=60)
def load_dashboard_data():
    """
    Charge les dernières observations depuis le Feature Store PostgreSQL.
    """
    db = DatabaseManager()
    query = """
    SELECT 
        observation_id, parcelle_id, region, code_postal, type_culture, stade_culture,
        ndvi, ecart_ndvi_typique, ratio_rendement, indice_stress_thermo_hydrique,
        type_sol, pluviometrie_mm, date_observation, anomalie_label
    FROM features
    ORDER BY date_observation DESC
    LIMIT 1000;
    """
    with db.engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    if not df.empty:
        df = df.drop_duplicates(subset=['parcelle_id'], keep='first')

        df[['latitude', 'longitude']] = df.apply(apply_deterministic_jitter, axis=1)
        
    return df


# Chargement initial des données
try:
    df_parcelles = load_dashboard_data()
except Exception as e:
    st.error(f"Impossible de charger les données depuis PostgreSQL : {e}")
    df_parcelles = pd.DataFrame()

# Variables pivots pour l'interaction inter-sections
selected_parcelle = None
current_observation_id = None

if not df_parcelles.empty:    
    # logique de coloration des parcelles (RGBA)
    def assign_color_and_tier(row):
        """
        Système de tri hybride : IA (anomalie_label) + Règles Métiers (Signaux faibles)
        Opacité réglée à 220 pour un bon compromis visuel.
        """
        # 1. Priorité absolue à l'IA : Si le modèle Random Forest lève une anomalie
        if row['anomalie_label'] == 1:
            return [239, 68, 68, 220], "Critique (IA)"
        
        # 2. Signaux faibles : L'IA dit 0, mais des indicateurs agronomiques dérivent
        has_warning = (
            row['indice_stress_thermo_hydrique'] > SEUIL_STRESS_WARNING or 
            row['ecart_ndvi_typique'] < SEUIL_NDVI_WARNING or 
            row['ratio_rendement'] < SEUIL_RENDEMENT_WARNING
        )
        if has_warning:
            return [249, 115, 22, 220], "Vigilance (Signal Faible)"
        
        # 3. Parcelle totalement saine
        return [34, 197, 94, 220], "Saine"

    # Application des couleurs et des libellés de risques
    res = df_parcelles.apply(assign_color_and_tier, axis=1)
    df_parcelles['color'] = [r[0] for r in res]
    df_parcelles['statut_text'] = [r[1] for r in res]

    # Création des deux grandes colonnes de niveau supérieur (50% / 50%)
    col_gauche_principal, col_droite_principal = st.columns([0.6, 0.4])

    # -------------------------------------------------------------------------
    # 1. CARTOGRAPHIE DYNAMIQUE DES RISQUES (SORTIES) col_gauche_principal
    # -------------------------------------------------------------------------
    with col_gauche_principal:
        st.header("1. Cartographie Dynamique des Risques")
        col_map, col_legend = st.columns([3, 1])
        
        with col_map:
            # Configuration de la couche de points PyDeck
            layer = pdk.Layer(
                "ScatterplotLayer",
                df_parcelles,
                id="parcelles-layer",
                get_position=["longitude", "latitude"],
                get_fill_color="color",
                get_radius=400,  # Taille du point en mètres sur la carte
                radius_min_pixels=6,
                radius_max_pixels=15,
                pickable=True,     # Permet l'interaction (clic / survol)
                auto_highlight=True
            )
            
            # Centrage initial de la carte sur la moyenne des parcelles
            view_state = pdk.ViewState(
                latitude=df_parcelles["latitude"].mean() if not df_parcelles.empty else 46.5,
                longitude=df_parcelles["longitude"].mean() if not df_parcelles.empty else 2.5,
                zoom=5,
                pitch=0,
            )
            
            # Affichage de la carte ET écoute de l'événement de sélection
            map_event = st.pydeck_chart(
                pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                    tooltip={
                        "html": """
                            <b>Parcelle :</b> {parcelle_id}<br/>
                            <b>Culture :</b> {type_culture} ({stade_culture})<br/>
                            <b>Statut :</b> {statut_text}<br/>
                            <b>NDVI :</b> {ndvi}<br/>
                            <b>Stress Thermo-Hydrique :</b> {indice_stress_thermo_hydrique}
                        """,
                        "style": {"backgroundColor": "#6f42c1", "color": "white", "fontFamily": "sans-serif", "zIndex": 10000}
                    }
                ),
                on_select="rerun",              # Déclenche un rafraîchissement au clic
                selection_mode="single-object", # Sélection d'un seul point à la fois
                key="map_parcelles"             # Clé unique pour le widget
            )
            
            # Extraction de l'ID cliqué et mise à jour du state
            if map_event and "selection" in map_event:
                selected_points = map_event["selection"].get("objects", {}).get("parcelles-layer", [])
                if selected_points:
                    st.session_state["selected_parcelle_id"] = selected_points[0]["parcelle_id"]
                else:
                    if st.session_state["selected_parcelle_id"] is not None:
                        st.session_state["selected_parcelle_id"] = None
                        st.rerun()
            
        with col_legend:
            st.markdown("**Légende des Alertes :**")
            st.error("🔴 Risque Critique (Urgence Forte)")
            st.warning("🟠 Risque Modéré (À surveiller)")
            st.success("🟢 Parcelle Saine")
            
            total_critique = len(df_parcelles[df_parcelles['anomalie_label'] == 1])
            total_modere = len(df_parcelles[df_parcelles['statut_text'] == "Vigilance (Signal Faible)"])
            
            st.metric(label="Alertes Critiques 🔴", value=total_critique)
            st.metric(label="Risques Modérés 🟠", value=total_modere)

    # -------------------------------------------------------------------------
    # 2. INTERPRÉTABILITÉ MÉTIER - XAI (SORTIES) col_droite_principal
    # -------------------------------------------------------------------------
    with col_droite_principal:
        st.header("2. Analyse Explicative des Alertes (XAI)")
        
        # Bannière informative si aucune anomalie critique globale
        parcelles_en_alerte = df_parcelles[df_parcelles['anomalie_label'] == 1]['parcelle_id'].unique()
        if len(parcelles_en_alerte) == 0:
            st.success("Aucune anomalie critique globale signalée sur les parcelles de la coopérative.")

        # Liste complète pour permettre le clic sur n'importe quel point de la carte
        liste_toutes_parcelles = list(df_parcelles['parcelle_id'].unique())

        if len(liste_toutes_parcelles) > 0:
            # crée une liste d'options contenant un choix neutre au début
            options_selectbox = ["--- Choisir une parcelle ---"] + liste_toutes_parcelles

            # calcule l'index. Si aucun ID n'est en mémoire, on pointe sur le choix neutre (index 0)
            default_index = 0
            if st.session_state["selected_parcelle_id"] in liste_toutes_parcelles:
                default_index = options_selectbox.index(st.session_state["selected_parcelle_id"])

            selected_option = st.selectbox(
                "Sélectionner une parcelle à auditer :", 
                options=options_selectbox,
                index=default_index  # Se synchronise automatiquement avec le clic carte !
            )
            
            if selected_option != "--- Choisir une parcelle ---":
                selected_parcelle = selected_option
                st.session_state["selected_parcelle_id"] = selected_parcelle

                p_data = df_parcelles[df_parcelles['parcelle_id'] == selected_parcelle].iloc[0]
                
                # Capture de l'identifiant pour la boucle de rétroaction
                current_observation_id = p_data['observation_id']
                
                statut_actuel = p_data['statut_text']

                st.subheader(f"Diagnostic Agronomique : Parcelle {selected_parcelle}")
                # Permet un affichage propre si c'est un format de date reconnu par Pandas, sinon affiche brut
                raw_date = p_data['date_observation']
                date_affiche = raw_date.strftime('%d/%m/%Y') if hasattr(raw_date, 'strftime') else str(raw_date)
                st.markdown(f"**Date d'observation :** {date_affiche}")
                st.markdown(f"**Contexte terrain :** Culture de **{p_data['type_culture']}** au stade **{p_data['stade_culture']}** (Région : {p_data['region']} | Sol : {p_data['type_sol']}).")
                

                # Construction dynamique du rapport de symptômes physiques
                symptomes = []
                
                # Analyse du rendement
                if p_data['ratio_rendement'] < SEUIL_RENDEMENT_CRITIQUE:
                    symptomes.append(f"**Rendement Critique :** Rendement estimé inférieur de **{int((1-p_data['ratio_rendement'])*100)}%** par rapport à la moyenne locale de la zone.")
                elif p_data['ratio_rendement'] < SEUIL_RENDEMENT_WARNING:
                    symptomes.append(f"**Rendement en baisse :** Décrochage modéré constaté par rapport à la zone (**-{int((1-p_data['ratio_rendement'])*100)}%**).")
                    
                # Analyse de la vigueur (NDVI)
                if p_data['ecart_ndvi_typique'] < SEUIL_NDVI_CRITIQUE:
                    symptomes.append(f"**Vigueur Végétale Critique :** L'écart NDVI de **{p_data['ecart_ndvi_typique']:.2f}** traduit une anomalie ou une perte sévère de biomasse active.")
                elif p_data['ecart_ndvi_typique'] < SEUIL_NDVI_WARNING:
                    symptomes.append(f"**Baisse de Vigueur :** Dérive légère de l'indice NDVI (**{p_data['ecart_ndvi_typique']:.2f}**) par rapport au profil saisonnier type.")
                    
                # Analyse du Stress Thermo-Hydrique
                if p_data['indice_stress_thermo_hydrique'] > SEUIL_STRESS_CRITIQUE:
                    symptomes.append(f"**Stress Thermo-Hydrique Critique :** L'indice atteint **{p_data['indice_stress_thermo_hydrique']:.1f}**, combinant fortes chaleurs et déficit en eau sévère.")
                elif p_data['indice_stress_thermo_hydrique'] > SEUIL_STRESS_WARNING:
                    symptomes.append(f"**Stress Thermo-Hydrique Modéré :** Risque thermique ou hydrique naissant (**{p_data['indice_stress_thermo_hydrique']:.1f}**).")

                # Affichage adapté selon la catégorie unique calculée à la section 1
                if statut_actuel == "Critique (IA)":
                    st.error("### Statut : Anomalie Globale Validée par l'IA")
                    st.markdown("**Facteurs physiques probables ayant déclenché l'alerte du modèle :**")
                    if symptomes:
                        st.markdown("\n".join(symptomes))
                    else:
                        st.markdown("• *Anomalie multifactorielle complexe détectée par le modèle sur la base de corrélations croisées.*")
                        
                elif statut_actuel == "Vigilance (Signal Faible)":
                    st.warning("### Statut : Vigilance Agronomique (Hors IA)")
                    st.markdown("**Le modèle IA n'a pas validé de rupture globale, mais les capteurs terrain affichent des dérives importantes :**")
                    st.markdown("\n".join(symptomes))
                    
                else:
                    st.success("### Statut : Parcelle Saine & Stable")
                    st.markdown("Aucun signal de stress, de baisse de vigueur ou de perte de rendement n'a été détecté. Les indicateurs sont nominaux.")

                # Métriques clés en colonnes
                st.markdown("<br>", unsafe_allow_html=True)
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("NDVI Actuel", f"{p_data['ndvi']:.2f}", delta=f"{p_data['ecart_ndvi_typique']:.2f}", delta_color="inverse")
                col2.metric("Stress Thermo-Hydrique", f"{p_data['indice_stress_thermo_hydrique']:.1f}", delta="Alerte" if p_data['indice_stress_thermo_hydrique'] > SEUIL_STRESS_WARNING else None, delta_color="off")
                col3.metric("Ratio de Rendement", f"{p_data['ratio_rendement']:.2f}", delta=f"{int((p_data['ratio_rendement'] - 1)*100)}% vs zone")
                col4.metric("Pluviométrie (Cumul)", f"{p_data['pluviometrie_mm']:.1f} mm")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 3. TABLEAU DE BORD DE PRIORISATION (SORTIES)
    # -------------------------------------------------------------------------
    st.header("3. Tableau de Priorisation des Interventions")
    st.markdown("Les parcelles nécessitant une visite sont triées par priorité d'anomalie.")
    
    df_sorted = df_parcelles.sort_values(by="anomalie_label", ascending=False)
    st.dataframe(
        df_sorted[['parcelle_id', 'region', 'type_culture', 'stade_culture', 'ndvi', 'anomalie_label']],
        column_config={
            "parcelle_id": "Code Parcelle",
            "region": "Région",
            "type_culture": "Culture",
            "stade_culture": "Stade",
            "ndvi": st.column_config.NumberColumn("Indice NDVI", format="%.2f"),
            "anomalie_label": st.column_config.ProgressColumn(
                "Niveau de Risque", help="Anomalie détectée par l'IA (0 ou 1)", min_value=0, max_value=1, format="%d"
            ),
        },
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 4. INTERACTIONS ET COLLECTE DE DONNÉES QUALIFIÉES (ENTRÉES)
    # -------------------------------------------------------------------------
    st.header("4. Actions Métier & Collecte de Données Qualifiées")
    
    tab_feedback, tab_predict = st.tabs([
        "Validation Terrain (Endpoint /feedback)", 
        "Forçage Manuel & Recalcul (Endpoint /predict)"
    ])
    
    # Validation Terrain (Saisie par l'agronome)
    with tab_feedback:
        st.subheader("Saisie du retour d'expertise agronomique")
        
        if current_observation_id:
            st.write(f"Rapport d'inspection pour la parcelle **{selected_parcelle}** (ID Obs: `{current_observation_id}`)")
            
            with st.form("form_feedback", clear_on_submit=True):
                agronome_name = st.text_input("Identifiant technique de l'agronome :", value="expert_coop_01")
                
                feedback_status = st.radio(
                    "Constat constaté de visu :",
                    options=["Anomalie Confirmée (Vrai Positif)", "Saine / Fausse Alerte (Faux Positif)"]
                )
                
                nature_probleme = st.selectbox(
                    "Nature principale de la dérive observée :",
                    options=["Stress hydrique", "Maladie", "Ravageur", "Autre / Non applicable"]
                )
                
                commentaire_libre = st.text_area("Observations terrain additionnelles :")
                submit_feedback = st.form_submit_button("Transmettre la Validation Terrain")
                
                if submit_feedback:
                    is_validated = True if "Anomalie Confirmée" in feedback_status else False
                    
                    # Alignement strict avec le modèle Pydantic de FastAPI
                    payload = {
                        "observation_id": current_observation_id,
                        "agronome_username": agronome_name,
                        "is_anomaly_validated": is_validated,
                        "commentaire": f"[{nature_probleme}] {commentaire_libre}".strip()
                    }
                    
                    try:
                        response = requests.post(f"{API_BASE_URL}/feedback", json=payload)
                        if response.status_code in [200, 201]:
                            st.success("Feedback enregistré ! Données ajoutées à la table 'validated_feedbacks'.")
                            st.cache_data.clear() # Force le rafraîchissement des performances
                        else:
                            st.error(f"Erreur de transmission à l'API (Code {response.status_code}).")
                    except Exception as err:
                        st.error(f"Impossible de joindre l'endpoint /feedback : {err}")
        else:
            st.warning("Veuillez sélectionner une parcelle active sur la carte ou dans la section 2 'XAI' pour envoyer une validation.")

    # Section Predict
    with tab_predict:
        st.subheader("Recalcul instantané d'une parcelle")
        st.markdown("Téléversez les nouvelles observations pour écraser et recalculer instantanément le risque.")
        
        uploaded_file = st.file_uploader("Choisir un fichier d'observations au format CSV...", type=["csv"])
        
        if uploaded_file is not None:
            if st.button("Déclencher le calcul prioritaire"):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                    response = requests.post(f"{API_BASE_URL}/predict", files=files)
                    
                    if response.status_code == 200:
                        st.success("Recalcul en temps réel opéré avec succès par l'API.")
                        st.json(response.json())
                    else:
                        st.error(f"Erreur lors du calcul de prédiction (Code {response.status_code}).")
                except Exception as err:
                    st.error(f"Impossible de joindre l'endpoint /predict : {err}")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 5. CLÔTURE DE LA BOUCLE DE RÉTROACTION & MONITORING (FEEDBACK LOOP)
    # -------------------------------------------------------------------------
    # st.header("5. Clôture de la Boucle MLOps & Suivi du Concept Drift")
    
    # try:
    #     metrics_response = requests.get(f"{API_BASE_URL}/metrics/field-performance")
    #     if metrics_response.status_code == 200:
    #         metrics = metrics_response.json()
            
    #         col_m1, col_m2, col_m3 = st.columns(3)
    #         f1_actuel = metrics["f1_score"]
    #         status_drift = metrics["concept_drift_alert"]
            
    #         with col_m1:
    #             if status_drift:
    #                 st.metric(label="F1-Score Terrain (Alerte Drift)", value=f"{f1_actuel:.2f}", delta="- Dégradation")
    #                 st.error("Concept Drift : Écart constaté entre les prédictions mathématiques et la réalité terrain.")
    #             else:
    #                 st.metric(label="F1-Score Terrain Actuel", value=f"{f1_actuel:.2f}", delta="Optimal")
    #                 st.success("Modèle en adéquation totale avec le terrain.")
            
    #         with col_m2:
    #             st.metric(label="Précision du Modèle", value=f"{metrics['precision']:.2%}")
    #             st.caption(f"Vrais Positifs validés par les experts : {metrics['true_positives']}")
                
    #         with col_m3:
    #             st.metric(label="Rappel (Recall) Réel", value=f"{metrics['recall']:.2%}")
    #             st.caption(f"Fausses alertes signalées : {metrics['false_positives']}")
                
    #         st.markdown("#### Progression avant le déclenchement du réentraînement automatique")
    #         current_feedbacks = metrics["total_feedbacks"]
    #         seuil_retrain = 50
            
    #         progression = min(current_feedbacks / seuil_retrain, 1.0)
    #         st.progress(progression)
    #     else:
    #         st.warning("Impossible de récupérer les métriques de performance depuis l'API.")

    # except Exception as e:
    #     st.error(f"Erreur de connexion au serveur de monitoring backend : {e}")