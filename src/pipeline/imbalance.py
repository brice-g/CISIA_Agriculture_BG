from typing import Tuple, Dict
import numpy as np
import pandas as pd
from sklearn.utils.class_weight import compute_class_weight
from loguru import logger

def calculate_imbalance_strategies(y_train: pd.Series) -> Tuple[Dict[int, float], float]:
    """
    Calcul et configuration des stratégies de compensation du déséquilibre de classes.
    Calcule les poids pour Scikit-Learn (Random Forest) et XGBoost basés UNIQUEMENT sur le Train set.
    
    CISIA Note : Ajuster la fonction de perte permet de ne pas fausser la réalité biologique
    des données IoT capteurs (contrairement à SMOTE).
    
    Args:
        y_train (pd.Series): La variable cible de l'ensemble d'entraînement.
        
    Returns:
        Tuple[Dict[int, float], float]: 
            - Le dictionnaire des poids de classes (Scikit-Learn)
            - La valeur du paramètre scale_pos_weight (XGBoost)
    """
    logger.info("[PIPELINE] : Calcul des stratégies de gestion du déséquilibre")
    
    try:
        # 1. Calcul des poids théoriques "balanced" pour Scikit-Learn
        classes = np.unique(y_train)
        poids_calcules = compute_class_weight(
            class_weight='balanced', 
            classes=classes, 
            y=y_train
        )
        
        # Sérialisation propre en types natifs Python (Crucial pour l'enregistrement JSON / MLOps)
        dict_class_weight = {int(k): float(v) for k, v in zip(classes, poids_calcules)}
        
        # 2. Calcul du paramètre spécifique pour les algorithmes de Gradient Boosting (XGBoost)
        nb_normal = int(np.sum(y_train == 0))
        nb_anomalie = int(np.sum(y_train == 1))
        
        if nb_anomalie == 0:
            logger.critical("Erreur critique : Aucune anomalie détectée dans y_train. Division par zéro impossible.")
            raise ValueError("Le jeu d'entraînement ne contient aucune anomalie (classe 1).")
            
        scale_pos_weight_value = float(nb_normal / nb_anomalie)
        
        # 3. Inscription du rapport d'audit dans le système de journalisation (Logging)
        logger.info("=" * 60)
        logger.info("         SYNTHÈSE DE LA GESTION DU DÉSÉQUILIBRE             ")
        logger.info("=" * 60)
        logger.info(f"Distribution réelle dans Train : Normales={nb_normal} | Anomalies={nb_anomalie}")
        logger.info(f"Ratio de déséquilibre brut    : 1 anomalie pour {scale_pos_weight_value:.2f} normales.")
        logger.info("-" * 40)
        logger.info(f"Poids configurés (Scikit-Learn) : {dict_class_weight}")
        logger.info(f"Poids configuré  (XGBoost)      : {scale_pos_weight_value:.4f}")
        logger.success("Stratégie de pénalisation calculée avec succès.")
        logger.info("=" * 60)
        
        return dict_class_weight, scale_pos_weight_value

    except Exception as e:
        logger.error(f"Échec du calcul de gestion du déséquilibre : {str(e)}")
        raise e