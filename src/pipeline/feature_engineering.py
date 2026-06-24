import pandas as pd
from loguru import logger

def engineer_features(df_master: pd.DataFrame) -> pd.DataFrame:
    """
    Ingénierie des caractéristiques (Feature Engineering).
    Prend la matrice jointe et calcule les indicateurs agronomiques avancés.
    
    CISIA Note : Cette fonction sera appelée à la fois par le pipeline d'entraînement
    et par l'API FastAPI lors d'une prédiction unitaire (Temps réel).
    """
    logger.info("[PIPELINE] Étape 2.4 : Début de l'ingénierie des caractéristiques")
    
    # Bonne pratique : On travaille sur une copie pour éviter de modifier le DataFrame d'origine
    df_master = df_master.copy()
    
    try:
        # 1. Calcul de l'âge de la culture au moment de l'observation (en jours)
        logger.info("Calcul de l'âge de la culture (AgeCulture_jours)...")
        df_master['AgeCulture_jours'] = (
            pd.to_datetime(df_master['DateObservation']) - pd.to_datetime(df_master['DateMiseEnCulture'])
        ).dt.days
        
        # Sécurité : Si l'âge est négatif à cause d'une mauvaise saisie de date, on redresse à 0
        # (Évite que le modèle Random Forest soit perturbé par des valeurs impossibles)
        df_master.loc[df_master['AgeCulture_jours'] < 0, 'AgeCulture_jours'] = 0


        # 2. Calcul du ratio de rendement par rapport à la moyenne historique de la zone
        logger.info("Calcul du ratio de rendement (RatioRendement)...")
        # CISIA Astuce : Le + 1e-5 s'appelle un "epsilon". Il protège ton code d'un crash global
        # si une zone a un rendement moyen enregistré à 0.
        df_master['RatioRendement'] = df_master['RendementEstime_t_ha'] / (df_master['RendementMoyenZone_t_ha'] + 1e-5)


        # 3. Création de l'indice combiné de stress thermo-hydrique (Hot & Dry proxy)
        logger.info("Calcul de l'indice de stress thermo-hydrique (IndiceStressThermoHydrique)...")
        df_master['IndiceStressThermoHydrique'] = df_master['Temperature'] * (100.0 - df_master['Humidite'])


        # 4. Calcul de la production totale estimée à l'échelle de la parcelle (en tonnes)
        logger.info("Calcul de la production totale estimée (ProductionTotaleEstimee_t)...")
        df_master['ProductionTotaleEstimee_t'] = df_master['Surface_ha'] * df_master['RendementEstime_t_ha']


        # 5. Calcul de l'écart au NDVI typique (médiane par couple TypeCulture / StadeCulture)
        logger.info("Calcul de l'écart au NDVI typique (Ecart_NDVI_Typique)...")
        # On calcule la référence
        mediane_ndvi_ref = df_master.groupby(['TypeCulture', 'StadeCulture'])['NDVI'].transform('median')
        # On mesure l'écart (Vigueur supérieure ou inférieure à la normale)
        df_master['Ecart_NDVI_Typique'] = df_master['NDVI'] - mediane_ndvi_ref


        # 6. Rapport d'exécution et monitoring des données (Data Logging)
        features_creees = [
            'AgeCulture_jours', 'RatioRendement', 
            'IndiceStressThermoHydrique', 'ProductionTotaleEstimee_t', 
            'Ecart_NDVI_Typique'
        ]
        
        logger.success(f"Feature Engineering terminé ! Nouvelle forme du dataset : {df_master.shape}")
        
        #log
        for feature in features_creees:
            summary = df_master[feature].describe()
            logger.info(
                f"[Feature Stats] {feature: <26} -> Moyenne: {summary['mean']: <8.2f} | "
                f"Min: {summary['min']: <8.2f} | Max: {summary['max']: <8.2f}"
            )
            
        return df_master

    except Exception as e:
        logger.error(f"Erreur critique lors du Feature Engineering : {str(e)}")
        raise e