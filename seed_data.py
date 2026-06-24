"""
Script de Seeding pour le projet CISIA
Description : Injecte des données initiales de test dans la table 'features'
              en utilisant la méthode native du DatabaseManager.
"""

from datetime import datetime, timedelta
import pandas as pd
from loguru import logger
from src.database.db_manager import DatabaseManager

def seed_database():
    logger.info("Préparation des données de test (Mock Data)...")
    
    # Date du jour et date de mise en culture (ex: il y a 60 jours)
    date_obs = datetime.now()
    date_culture_1 = date_obs - timedelta(days=45)
    date_culture_2 = date_obs - timedelta(days=30)

    # Création du dictionnaire avec TOUTES les clés PascalCase attendues par ton mapping
    mock_data = {
        'ObservationID': ['OBS_2026_001', 'OBS_2026_002'],
        'ParcelleID': ['PARCELLE_TOULOUSE_01', 'PARCELLE_RENNES_02'],
        'DateObservation': [date_obs, date_obs],
        'DateMiseEnCulture': [date_culture_1, date_culture_2],
        'CodePostal': ['31000', '35000'],
        'Capteur': ['Drone_DJI_P4', 'Satellite_Sentinel2'],
        'StadeCulture': ['Montaison', 'Levée'],
        'TypeCulture': ['Blé tendre', 'Maïs'],
        'TypeSol': ['Argilo-calcaire', 'Limoneux'],
        'Irrigation': ['Goutte-à-goutte', 'Pluviométrie naturelle'],
        'Region': ['Occitanie', 'Bretagne'],
        'Temperature': [28.5, 19.2],
        'Humidite': [35.2, 72.1],
        'Surface_ha': [12.5, 24.0],
        'NDVI': [0.42, 0.78],
        'RendementEstime_t_ha': [4.2, 7.5],
        'RendementMoyenZone_t_ha': [5.8, 7.2],
        'AgeCulture_jours': [45, 30],
        'RatioRendement': [0.72, 1.04],
        'IndiceStressThermoHydrique': [3.8, 0.9],
        'ProductionTotaleEstimee_t': [52.5, 180.0],
        'Ecart_NDVI_Typique': [-0.22, 0.03],
        'AnomalieLabel': [1, 0]  # 1 = Alerte Rouge (Occitanie), 0 = Sain (Bretagne)
    }
    
    # Conversion en DataFrame Pandas
    df_mock = pd.DataFrame(mock_data)
    
    # Instanciation de ton DatabaseManager (qui charge automatiquement ton .env local)
    manager = DatabaseManager()
    
    try:
        logger.info("🔌 Connexion à la base locale et injection via save_features_dataframe()...")
        # Appel de ta fonction existante
        manager.save_features_dataframe(df_mock)
        logger.success("Seeding terminé avec succès ! Les données sont disponibles.")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du seeding : {str(e)}")

if __name__ == "__main__":
    seed_database()