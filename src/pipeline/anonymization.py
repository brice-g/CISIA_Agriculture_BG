# src/pipeline/anonymization.py
import pandas as pd
from loguru import logger
from src.core.security import generate_parcelle_id

def join_and_anonymize_dataset(df_obs: pd.DataFrame, df_parc: pd.DataFrame) -> pd.DataFrame:
    """
    Jointure sécurisée, exclusion des données personnelles (PII) 
    et hachage cryptographique du ParcelleID pour une conformité RGPD totale.
    """
    logger.info("[PIPELINE] : Jointure sécurisée et anonymisation RGPD")

    # 1. Définition des colonnes utiles (Exclusion stricte des PII)
    cols_parcelles_utiles = [
        'ParcelleID', 'Region', 'Surface_ha', 'TypeCulture', 
        'TypeSol', 'Irrigation', 'DateMiseEnCulture', 'CodePostal'
    ]
    
    # Extraction du catalogue propre
    df_parc_anonyme = df_parc[cols_parcelles_utiles].copy()

    # 2. APPLICATION DU PRIVACY-BY-DESIGN SUR LE PARCELLE ID
    # On applique la fonction de hachage déterministe sur les deux dataframes AVANT la jointure
    logger.info("Chiffrement des identifiants pivots (ParcelleID)...")
    df_parc_anonyme['ParcelleID'] = df_parc_anonyme['ParcelleID'].astype(str).apply(generate_parcelle_id)
    df_obs = df_obs.copy()
    df_obs['ParcelleID'] = df_obs['ParcelleID'].astype(str).apply(generate_parcelle_id)

    # 3. Opération de jointure interne (Inner Join)
    n_obs_avant_jointure = len(df_obs)
    df_master = pd.merge(df_obs, df_parc_anonyme, on='ParcelleID', how='inner')
    
    logger.info(f"-> Observations avant jointure : {n_obs_avant_jointure}")
    logger.info(f"-> Observations après jointure : {len(df_master)}")

    # 4. Rapport d'audit de conformité automatique pour le journal de production
    pii_interdites = ['Exploitant', 'Email', 'Telephone', 'NumSIRET']
    pii_detectees = [col for col in pii_interdites if col in df_master.columns]

    if len(pii_detectees) == 0:
        logger.success("SÉCURITÉ : Aucune donnée personnelle (PII) détectée dans la matrice finale.")
    else:
        logger.critical(f"ALERTE CONFORMITÉ : Des variables interdites ont fui : {pii_detectees}")
        raise ValueError("Violation de conformité RGPD : Présence de PII dans le dataset final.")

    return df_master