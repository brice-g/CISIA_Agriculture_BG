#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de Surveillance et Déclenchement (Triggers) MLOps
Description : Évalue les conditions de Data Drift (PSI >= 0.20) et de boucle de rétroaction
              (Feedbacks >= 50) sur la table 'validated_feedbacks' pour lancer le réentraînement.
"""

import sys
import numpy as np
import pandas as pd
from loguru import logger

# Importations de l'orchestrateur et de ton gestionnaire de base de données
from run_pipeline import run_global_pipeline
from src.database.db_manager import DatabaseManager

# Seuils issus des règles métier du projet (CISIA)
PSI_THRESHOLD = 0.20
FEEDBACK_THRESHOLD = 50


def calculate_psi(reference: pd.Series, actual: pd.Series, num_bins: int = 10) -> float:
    """
    Calcule le Population Stability Index (PSI) entre la distribution d'entraînement
    et les nouvelles données IoT reçues du terrain.
    """
    ref_clean = reference.dropna()
    act_clean = actual.dropna()

    if ref_clean.empty or act_clean.empty:
        logger.warning("Une des séries est vide. Calcul du PSI annulé.")
        return 0.0

    bins = np.percentile(ref_clean, np.linspace(0, 100, num_bins + 1))
    bins[0] = -np.inf
    bins[-1] = np.inf

    ref_counts, _ = np.histogram(ref_clean, bins=bins)
    act_counts, _ = np.histogram(act_clean, bins=bins)

    P = act_counts / len(act_clean)
    Q = ref_counts / len(ref_clean)

    epsilon = 1e-4
    P = np.where(P == 0, epsilon, P)
    Q = np.where(Q == 0, epsilon, Q)

    psi_value = np.sum((P - Q) * np.log(P / Q))
    return float(psi_value)


def check_feedback_count(db_manager: DatabaseManager) -> int:
    """
    Interroge la table SQL 'validated_feedbacks' pour compter les validations
    terrain rapportées par les agronomes.
    """
    query = "SELECT COUNT(*) FROM validated_feedbacks;"
    try:
        with db_manager.engine.connect() as connection:
            result = connection.execute(pd.io.sql.text(query))
            count = result.scalar()
            return int(count) if count is not None else 0
    except Exception as e:
        logger.error(f"Erreur lors de la lecture de la table 'validated_feedbacks' : {e}")
        return 0


def archive_consumed_feedbacks(db_manager: DatabaseManager):
    """
    Nettoie ou archive les feedbacks consommés pour éviter les réentraînements en boucle.
    Note : Idéalement, on les transfère dans une table 'archived_feedbacks' pour garder l'historique.
    Pour faire simple et efficace ici, on va vider la table de travail.
    """
    logger.info("Archivage et nettoyage des feedbacks consommés...")
    query_archive = "INSERT INTO archived_feedbacks SELECT * FROM validated_feedbacks;"
    query_delete = "TRUNCATE TABLE validated_feedbacks;"
    
    try:
        with db_manager.engine.connect() as connection:
            with connection.begin(): # Utilisation d'une transaction sécurisée
                # Si tu as créé la table d'archive, décommente la ligne suivante :
                # connection.execute(pd.io.sql.text(query_archive))
                connection.execute(pd.io.sql.text(query_delete))
        logger.success("Table 'validated_feedbacks' réinitialisée. Prête pour le prochain cycle.")
    except Exception as e:
        logger.error(f"Impossible de réinitialiser les feedbacks : {e}")


def evaluate_triggers():
    """
    Vérifie l'état des verrous et déclenche le réentraînement si un indicateur vire au rouge.
    """
    logger.info("[MONITORING] Analyse des indicateurs de déclenchement...")
    db_manager = DatabaseManager()
    trigger_retraining = False
    
    # -------------------------------------------------------------------------
    # 1. ÉVALUATION DU DATA DRIFT (SUR LA COLONNE NDVI)
    # -------------------------------------------------------------------------
    ref_path = "data/processed/X_train.csv"
    try:
        if pd.io.common.file_exists(ref_path):
            df_ref = pd.read_csv(ref_path)
            
            query_latest = "SELECT ndvi FROM features ORDER BY date_observation DESC LIMIT 5000;"
            with db_manager.engine.connect() as conn:
                df_latest = pd.read_sql(query_latest, conn)
            
            if "ndvi" in df_ref.columns and not df_latest.empty:
                psi_ndvi = calculate_psi(df_ref["ndvi"], df_latest["ndvi"])
                logger.info(f"Indicateur de dérive (PSI NDVI) : {psi_ndvi:.4f}")
                
                if psi_ndvi >= PSI_THRESHOLD:
                    logger.warning(f"DRIFT ALERTE : Le PSI ({psi_ndvi:.4f}) a franchi le seuil de {PSI_THRESHOLD}")
                    trigger_retraining = True
            else:
                logger.warning("Vérification du drift impossible (Données récentes manquantes ou colonne absente).")
        else:
            logger.info("Données de référence (X_train.csv) absentes. Initialisation requise.")
            trigger_retraining = True
    except Exception as e:
        logger.error(f"Échec de l'évaluation du Data Drift : {e}")

    # -------------------------------------------------------------------------
    # 2. ÉVALUATION DU SEUIL DE FEEDBACKS (BOUCLE DE RÉTROACTION)
    # -------------------------------------------------------------------------
    feedback_count = check_feedback_count(db_manager)
    logger.info(f"Retours terrain collectés : {feedback_count}/{FEEDBACK_THRESHOLD}")
    
    if feedback_count >= FEEDBACK_THRESHOLD:
        logger.warning(f"BOUCLE DE RÉTROACTION : Seuil de {FEEDBACK_THRESHOLD} feedbacks atteint.")
        trigger_retraining = True

    # -------------------------------------------------------------------------
    # DÉCISION DU RÉENTRAÎNEMENT
    # -------------------------------------------------------------------------
    if trigger_retraining:
        logger.success("[TRIGGER VALIDÉ] Relance automatique du pipeline global d'entraînement...")
        try:
            # Exécution de ton vrai pipeline
            run_global_pipeline()
            
            # CLÔTURE DE LA BOUCLE : On réinitialise pour le prochain tour
            archive_consumed_feedbacks(db_manager)
            
        except Exception as e:
            logger.error(f"Le pipeline global a échoué, annulation du nettoyage des feedbacks : {e}")
    else:
        logger.info("[STATUS] Indicateurs sous contrôle. Pas de réentraînement nécessaire.")


if __name__ == "__main__":
    evaluate_triggers()