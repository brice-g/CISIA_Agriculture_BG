from typing import Tuple, List
import pandas as pd
from sklearn.model_selection import train_test_split
from loguru import logger

def encode_and_stratify_split(
    df_master: pd.DataFrame, 
    seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series, List[str]]:
    """
    Encodage One-Hot des variables catégorielles et double partitionnement
    stratifié (Train, Validation, Test).
    
    Retourne:
        X_train, X_val, X_test, y_train, y_val, y_test ainsi que la liste des features encodées.
    """
    logger.info("[PIPELINE] : Début de l'encodage et du partitionnement stratifié")
    
    df_master = df_master.copy()
    
    try:
        # 1. Nettoyage de la matrice : Exclusion des colonnes non prédictives
        cols_a_exclure = ['ObservationID', 'ParcelleID', 'DateObservation', 'DateMiseEnCulture', 'CodePostal']
        
        # Sécurité CISIA : On vérifie si les colonnes existent avant de les supprimer
        cols_existantes_a_exclure = [c for c in cols_a_exclure if c in df_master.columns]
        df_predictive = df_master.drop(columns=cols_existantes_a_exclure)
        logger.info(f"-> Colonnes non prédictives écartées : {cols_existantes_a_exclure}")

        # 2. Séparation des caractéristiques (X) et de la cible (y)
        if 'AnomalieLabel' not in df_predictive.columns:
            raise KeyError("La colonne cible 'AnomalieLabel' est introuvable dans le dataset.")
            
        X = df_predictive.drop(columns=['AnomalieLabel'])
        y = df_predictive['AnomalieLabel']

        # 3. Encodage One-Hot des variables catégorielles nominales
        colonnes_categorielles = ['Capteur', 'StadeCulture', 'TypeCulture', 'TypeSol', 'Irrigation', 'Region']
        
        # Vérification qu'on a bien toutes les colonnes à encoder
        cols_encodage_valides = [c for c in colonnes_categorielles if c in X.columns]
        
        logger.info("Encodage One-Hot des variables catégorielles via Pandas...")
        X_encoded = pd.get_dummies(X, columns=cols_encodage_valides, drop_first=True, dtype=int)
        
        # On sauvegarde la liste des colonnes de référence (Crucial pour le registre MLOps et l'API !)
        feature_names_reference = X_encoded.columns.tolist()
        logger.success(f"-> Encodage terminé. Nombre total de features en production : {len(feature_names_reference)}")

        # 4. Double Split Stratifié (70% Train / 15% Val / 15% Test)
        logger.info("Application du double split stratifié...")
        
        # Premier split : Isolation de 70% pour le Train
        X_train, X_temp, y_train, y_temp = train_test_split(
            X_encoded, y, 
            test_size=0.30, 
            stratify=y, 
            random_state=seed
        )

        # Second split : Division des 30% temporaires en 50/50 (soit 15% Val et 15% Test)
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, 
            test_size=0.50, 
            stratify=y_temp, 
            random_state=seed
        )

        # 5. Rapport d'audit et de complétude dans les logs professionnels
        logger.info("=" * 60)
        logger.info("          RAPPORT DE PARTITIONNEMENT DU DATASET             ")
        logger.info("=" * 60)
        logger.info(f"Ensemble d'Entraînement (Train) : {X_train.shape[0]} lignes | Taux d'anomalies : {y_train.mean():.2%}")
        logger.info(f"Ensemble de Validation (Val)   : {X_val.shape[0]} lignes | Taux d'anomalies : {y_val.mean():.2%}")
        logger.info(f"Ensemble de Test (Test)         : {X_test.shape[0]} lignes | Taux d'anomalies : {y_test.mean():.2%}")
        logger.info("=" * 60)

        return X_train, X_val, X_test, y_train, y_val, y_test, feature_names_reference

    except Exception as e:
        logger.error(f"Erreur lors de l'encodage et du split : {str(e)}")
        raise e