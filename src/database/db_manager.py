import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger
from dotenv import load_dotenv
from src.database.models import Base

# Charge les variables du fichier .env situé à la racine du projet
load_dotenv()

# Récupération des variables individuelles de ton .env
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "agriculture_db")

# Reconstruction dynamique de l'URL pour SQLAlchemy
# Si DATABASE_URL est déjà fournie (ex: en prod), on l'utilise, sinon on assemble tes variables
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

class DatabaseManager:
    def __init__(self, db_url: str = DATABASE_URL):
        self.engine = create_engine(db_url, pool_pre_ping=True, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def init_db(self):
        """Crée toutes les tables définies dans les modèles si elles n'existent pas."""
        try:
            logger.info("Initialisation des tables PostgreSQL...")
            Base.metadata.create_all(bind=self.engine)
            logger.success("Base de données PostgreSQL synchronisée avec succès.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la base : {str(e)}")
            raise e

    def save_features_dataframe(self, df: pd.DataFrame):
        """
        Sauvegarde le dataframe df_master dans la table 'features'.
        Gère la conversion implicite des colonnes PascalCase vers le format attendu.
        """
        logger.info(f"Sauvegarde de {df.shape[0]} lignes dans la table 'features'...")
        
        mapping_cols = {
            'ObservationID': 'observation_id', 'ParcelleID': 'parcelle_id',
            'DateObservation': 'date_observation', 'DateMiseEnCulture': 'date_mise_en_culture',
            'CodePostal': 'code_postal', 'Capteur': 'capteur', 'StadeCulture': 'stade_culture',
            'TypeCulture': 'type_culture', 'TypeSol': 'type_sol', 'Irrigation': 'irrigation',
            'Region': 'region', 'Temperature': 'temperature', 'Humidite': 'humidite', 'Pluviometrie_mm': 'pluviometrie_mm',
            'Surface_ha': 'surface_ha', 'NDVI': 'ndvi', 'RendementEstime_t_ha': 'rendement_estime_t_ha',
            'RendementMoyenZone_t_ha': 'rendement_moyen_zone_t_ha', 'AgeCulture_jours': 'age_culture_jours',
            'RatioRendement': 'ratio_rendement', 'IndiceStressThermoHydrique': 'indice_stress_thermo_hydrique',
            'ProductionTotaleEstimee_t': 'production_totale_estimee_t', 'Ecart_NDVI_Typique': 'ecart_ndvi_typique',
            'AnomalieLabel': 'anomalie_label'
        }
        
        try:
            df_to_sql = df.copy()
            df_to_sql = df_to_sql.rename(columns={k: v for k, v in mapping_cols.items() if k in df_to_sql.columns})
            
            if 'date_observation' in df_to_sql.columns:
                df_to_sql['date_observation'] = pd.to_datetime(df_to_sql['date_observation']).dt.date
            if 'date_mise_en_culture' in df_to_sql.columns:
                df_to_sql['date_mise_en_culture'] = pd.to_datetime(df_to_sql['date_mise_en_culture']).dt.date

            # LA CORRECTION ICI : On génère le timestamp d'ingestion directement pour Pandas
            df_to_sql['created_at'] = pd.Timestamp.utcnow()

            # Injection en masse optimisée via Pandas .to_sql
            df_to_sql.to_sql(
                name="features",
                con=self.engine,
                if_exists="append", 
                index=False
            )
            logger.success("Données injectées avec succès dans le Feature Store PostgreSQL.")
        except Exception as e:
            logger.error(f"Échec de l'injection SQL des features : {str(e)}")
            raise e