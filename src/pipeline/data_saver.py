import os
from pathlib import Path
import pandas as pd
from loguru import logger

def save_pipeline_artifacts(
    df_master_clean: pd.DataFrame,
    X_train: pd.DataFrame,
    X_val: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_val: pd.Series,
    y_test: pd.Series,
    base_dir: str = "data/processed"
) -> Path:
    """
    Étape MLOps : Matérialisation des artéfacts de données sur le disque.
    Crée la structure des dossiers et sauvegarde les fichiers CSV qui seront
    ensuite verrouillés et versionnés par DVC.
    """
    logger.info(f"[DVC PREPARATION] Sauvegarde des artéfacts de données dans '{base_dir}'...")
    
    # Création sécurisée du répertoire s'il n'existe pas
    output_path = Path(base_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # 1. Sauvegarde du dataset maître complet (utile pour l'audit ou l'exploration future)
        df_master_clean.to_csv(output_path / "df_master_clean.csv", index=False)
        
        # 2. Sauvegarde des caractéristiques (X) pour chaque split
        X_train.to_csv(output_path / "X_train.csv", index=False)
        X_val.to_csv(output_path / "X_val.csv", index=False)
        X_test.to_csv(output_path / "X_test.csv", index=False)
        
        # 3. Sauvegarde des cibles (y) pour chaque split
        y_train.to_csv(output_path / "y_train.csv", index=False)
        y_val.to_csv(output_path / "y_val.csv", index=False)
        y_test.to_csv(output_path / "y_test.csv", index=False)
        
        logger.success(f"Tous les fichiers de données ont été matérialisés dans {output_path}/")
        logger.info(f"Fichiers prêts à être verrouillés par DVC : {os.listdir(output_path)}")
        
        return output_path

    except Exception as e:
        logger.error(f"Erreur lors de l'écriture des artéfacts de données : {str(e)}")
        raise e