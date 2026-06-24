#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Orchestrateur Central du Pipeline MLOps
"""

import sys
import time
from pathlib import Path
import pandas as pd
from loguru import logger

# Configuration du logger pour le suivi de production
logger.remove()
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}", level="INFO")

# Importations calquées strictement sur tes modules et signatures réels
try:
    from src.pipeline.imputation import clean_agricultural_data, impute_missing_values
    from src.pipeline.anonymization import join_and_anonymize_dataset
    from src.pipeline.feature_engineering import engineer_features
    from src.pipeline.encoding_split import encode_and_stratify_split
    from src.pipeline.imbalance import calculate_imbalance_strategies
    from src.pipeline.modeling import train_and_optimize_champion, log_champion_to_mlflow
    from src.database.db_manager import DatabaseManager
    from src.pipeline.data_saver import save_pipeline_artifacts
except ImportError as e:
    logger.critical(f"Erreur d'importation des modules du projet. Détails : {e}")
    sys.exit(1)


def run_global_pipeline():
    """
    Exécute séquentiellement l'intégralité du pipeline de production.
    """
    start_global_time = time.time()
    logger.info("Démarrage de l'orchestration globale du pipeline...")

    raw_obs_path = "data/raw/observations.csv"
    raw_parc_path = "data/raw/parcelles.csv"
    processed_dir = "data/processed"
    
    try:
        # 1. Ingestion des données brutes
        logger.info("Étape 1 : Chargement des fichiers CSV bruts depuis data/raw/...")
        if not Path(raw_obs_path).exists() or not Path(raw_parc_path).exists():
            raise FileNotFoundError("Fichiers 'observations.csv' ou 'parcelles.csv' manquants dans data/raw/")
        
        df_obs = pd.read_csv(raw_obs_path)
        df_parc = pd.read_csv(raw_parc_path)

        # 2. Nettoyage physique et contrôle d'intégrité relationnelle
        logger.info("Étape 2 : Nettoyage physique des données (clean_agricultural_data)...")
        df_obs_clean, df_parc_clean = clean_agricultural_data(df_obs, df_parc)

        # 3. Imputation ciblée et conditionnelle (Contexte géoclimatique)
        logger.info("Étape 3 : Imputation des valeurs manquantes (impute_missing_values)...")
        df_obs_imp, df_parc_imp = impute_missing_values(df_obs_clean, df_parc_clean)

        # 4. Jointure et Anonymisation RGPD (reçoit les dataframes nettoyés et imputés)
        logger.info("Étape 4 : Jointure et anonymisation des données...")
        df_anon = join_and_anonymize_dataset(df_obs_imp, df_parc_imp)

        # 5. Feature Engineering (Calcul des indices agronomiques)
        logger.info("Étape 5 : Calcul des features (engineer_features)...")
        df_master_clean = engineer_features(df_anon)

        # 6. Sauvegarde dans PostgreSQL avant encodage One-Hot
        logger.info("Étape 6 : Persistance du df_master_clean dans PostgreSQL...")
        db_manager = DatabaseManager()
        db_manager.save_features_dataframe(df_master_clean)

        # 7. Encodage et Stratification (Capture des 7 éléments du tuple)
        logger.info("Étape 7 : Encodage et fractionnement des données (Train/Val/Test)...")
        X_train, X_val, X_test, y_train, y_val, y_test, categorical_cols = encode_and_stratify_split(df_master_clean, seed=42)

        # 8. Évaluation du déséquilibre des classes
        logger.info("Étape 8 : Analyse du déséquilibre des classes...")
        class_weights, imbalance_ratio = calculate_imbalance_strategies(y_train)

        # 9. Matérialisation physique sur le disque (Préparation DVC)
        logger.info("Étape 9 : Matérialisation des artéfacts via save_pipeline_artifacts...")
        save_pipeline_artifacts(
            df_master_clean=df_master_clean,
            X_train=X_train,
            X_val=X_val,
            X_test=X_test,
            y_train=y_train,
            y_val=y_val,
            y_test=y_test,
            base_dir=processed_dir
        )

        # 10. Optimisation Optuna et Entraînement final (Modèle + Meilleurs hyperparamètres)
        logger.info("Étape 10 : Recherche du champion via train_and_optimize_champion...")
        model_champion, best_params = train_and_optimize_champion(
            X_train=X_train,
            X_val=X_val,
            y_train=y_train,
            y_val=y_val,
            seed=42,
            n_trials=30
        )

        # 11. Enregistrement centralisé dans MLflow (Modèle, Paramètres et Lignage de données)
        logger.info("Étape 11 : Téléversement du modèle et des artéfacts de données dans MLflow...")
        log_champion_to_mlflow(
            model_champion=model_champion,
            best_params=best_params,
            X_val=X_val,
            y_val=y_val,
            processed_data_dir=processed_dir,
            seed=42
        )

        total_duration = time.time() - start_global_time
        logger.success(f"[SUCCÈS] Le pipeline global a été exécuté avec succès en {total_duration:.2f} secondes.")

    except Exception as e:
        logger.critical(f"[ÉCHEC CRITIQUE] Interruption du pipeline. Cause : {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run_global_pipeline()