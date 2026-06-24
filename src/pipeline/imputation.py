from typing import Tuple
import numpy as np
import pandas as pd
from loguru import logger

def clean_agricultural_data(df_obs: pd.DataFrame, df_parc: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Nettoyage physique des données et contrôle de l'intégrité relationnelle.
    Fidèle à la logique agronomique du PoC.
    """
    logger.info("🧹 [PIPELINE] : Début du nettoyage physique des données")
    
    # Copie locale pour éviter les effets de bord (Side Effects)
    df_obs = df_obs.copy()
    df_parc = df_parc.copy()

    # 1. Redressement du NDVI (Bornes strictes [-1, 1])
    logger.info("Formatting NDVI...")
    df_obs.loc[(df_obs['NDVI'] < -1.0) | (df_obs['NDVI'] > 1.0), 'NDVI'] = np.nan

    # 2. Redressement Pluviométrie
    df_obs.loc[df_obs['Pluviometrie_mm'] < 0, 'Pluviometrie_mm'] = 0.0
    df_obs['Pluviometrie_mm'] = df_obs['Pluviometrie_mm'].fillna(0.0)

    # 3. Traitement des anomalies thermiques extrêmes
    df_obs.loc[(df_obs['Temperature'] > 55.0) | (df_obs['Temperature'] < -15.0), 'Temperature'] = np.nan

    # 4. Nettoyage du catalogue des parcelles (Codes postaux masqués)
    df_parc['CodePostal'] = df_parc['CodePostal'].astype(str).replace('XXXXX', np.nan)

    # 5. Redressement des surfaces aberrantes par la médiane de la région
    df_parc.loc[df_parc['Surface_ha'] <= 0, 'Surface_ha'] = np.nan
    # Astuce CISIA : transform('median') applique la valeur du groupe directement à la ligne
    df_parc['Surface_ha'] = df_parc['Surface_ha'].fillna(
        df_parc.groupby('Region')['Surface_ha'].transform('median')
    )

    # 6. Suppression des doublons exacts
    n_obs_dup = df_obs.duplicated().sum()
    df_obs = df_obs.drop_duplicates()
    logger.info(f"-> Observations - Doublons supprimés : {n_obs_dup}")

    n_parc_dup = df_parc.duplicated().sum()
    df_parc = df_parc.drop_duplicates()
    logger.info(f"-> Parcelles - Doublons supprimés : {n_parc_dup}")

    # 7. Contrôle de l'intégrité relationnelle (Orphelins)
    n_obs_before = len(df_obs)
    df_obs = df_obs[df_obs["ParcelleID"].isin(df_parc["ParcelleID"])]
    logger.warning(f"-> Observations orphelines supprimées : {n_obs_before - len(df_obs)}")

    n_parc_before = len(df_parc)
    df_parc = df_parc[df_parc["ParcelleID"].isin(df_obs["ParcelleID"])]
    logger.warning(f"-> Parcelles sans relevés supprimées : {n_parc_before - len(df_parc)}")

    return df_obs, df_parc


def impute_missing_values(df_obs: pd.DataFrame, df_parc: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Imputation ciblée et conditionnelle (Contexte géoclimatique).
    """
    logger.info("[PIPELINE] : Imputation ciblée des valeurs manquantes")
    
    df_obs = df_obs.copy()
    df_parc = df_parc.copy()

    # A. Suppression des parcelles avec CodePostal masqué (Anciens 'XXXXX')
    n_parc_avant_cp = len(df_parc)
    df_parc = df_parc.dropna(subset=['CodePostal'])
    logger.info(f"-> Parcelles - Supprimées pour CodePostal invalide : {n_parc_avant_cp - len(df_parc)}")

    # B. Traitement de sécurité pour les NaN restants de Surface_ha (Repli médiane globale)
    df_parc['Surface_ha'] = df_parc['Surface_ha'].fillna(df_parc['Surface_ha'].median())

    # C. Imputation conditionnelle des Observations
    # Enrichissement temporaire pour obtenir Region et TypeCulture
    df_context = df_parc[['ParcelleID', 'Region', 'TypeCulture']]
    df_obs_imp = df_obs.merge(df_context, on='ParcelleID', how='left')

    # Imputations par groupe
    df_obs_imp['NDVI'] = df_obs_imp['NDVI'].fillna(
        df_obs_imp.groupby(['TypeCulture', 'StadeCulture'])['NDVI'].transform('median')
    )
    df_obs_imp['Temperature'] = df_obs_imp['Temperature'].fillna(
        df_obs_imp.groupby(['Region', 'StadeCulture'])['Temperature'].transform('median')
    )
    df_obs_imp['Humidite'] = df_obs_imp['Humidite'].fillna(
        df_obs_imp.groupby(['Region', 'StadeCulture'])['Humidite'].transform('median')
    )
    df_obs_imp['RendementEstime_t_ha'] = df_obs_imp['RendementEstime_t_ha'].fillna(
        df_obs_imp.groupby(['Region', 'TypeCulture'])['RendementEstime_t_ha'].transform('median')
    )

    # Fallback de sécurité ultime (Médiane globale si le groupe était trop petit)
    cols_manquantes = ['Temperature', 'Humidite', 'NDVI', 'RendementEstime_t_ha']
    for col in cols_manquantes:
        df_obs_imp[col] = df_obs_imp[col].fillna(df_obs_imp[col].median())

    # Restitution de la structure initiale de df_obs
    df_obs = df_obs_imp.drop(columns=['Region', 'TypeCulture'])
    
    logger.success("Nettoyage physique et imputations terminés avec succès.")
    return df_obs, df_parc