import os
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import optuna
import mlflow
import mlflow.sklearn
from loguru import logger

# Désactiver les logs verbeux d'Optuna pour garder une console de production propre
optuna.logging.set_verbosity(optuna.logging.WARNING)

def train_and_optimize_champion(
    X_train: pd.DataFrame,
    X_val: pd.DataFrame,
    y_train: pd.Series,
    y_val: pd.Series,
    seed: int = 42,
    n_trials: int = 30
) -> RandomForestClassifier:
    """
    Optimisation des hyperparamètres du Random Forest via Optuna.
    Fidèle au search space et à la stratégie de maximisation du F1-Score du PoC.
    """
    logger.info(f"[PIPELINE] : Lancement de l'optimisation Optuna ({n_trials} tentatives)...")
    
    # Définition de la fonction objectif interne pour Optuna
    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "max_depth": trial.suggest_int("max_depth", 5, 30),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 10),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 5),
            "class_weight": "balanced",
            "random_state": seed,
            "n_jobs": -1,
        }
        
        model = RandomForestClassifier(**params)
        model.fit(X_train, y_train)
        
        # Prédiction sur le jeu de validation pour guider l'optimisation
        preds = model.predict(X_val)
        
        # Maximisation du F1-score comme défini dans la stratégie OAD
        return float(f1_score(y_val, preds, zero_division=0))

    # Création et exécution de l'étude Optuna
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    
    logger.success(f"Meilleure tentative Optuna complétée avec un F1-Score de : {study.best_value:.4f}")
    logger.info(f"Hyperparamètres retenus : {study.best_params}")
    
    # Reconstruction et entraînement du modèle Champion final
    logger.info("Entraînement final du modèle Champion...")
    best_params_full = study.best_params.copy()
    best_params_full["class_weight"] = "balanced"
    best_params_full["random_state"] = seed
    best_params_full["n_jobs"] = -1
    
    model_champion = RandomForestClassifier(**best_params_full)
    model_champion.fit(X_train, y_train)
    
    return model_champion, study.best_params


def log_champion_to_mlflow(
    model_champion: RandomForestClassifier,
    best_params: dict,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    processed_data_dir: str = "data/processed",
    seed: int = 42
) -> None:
    """
    Enregistrement du modèle champion et de ses métriques dans MLflow.
    Intègre la configuration du seuil opérationnel OAD à 0.7377.
    """
    logger.info("[PIPELINE] Connexion et enregistrement dans MLflow...")
    
    # Configuration de l'expérience MLflow
    mlflow.set_experiment("Agriculture_Precision_Anomaly_Detection")
    best_model_name = "RandomForest"
    
    with mlflow.start_run(run_name=f"{best_model_name}-optuna-best") as run:
        # 1. Enregistrement des hyperparamètres optimisés
        mlflow.log_params(best_params)
        
        # 2. Configuration et enregistrement du seuil OAD issu de la cartographie
        operational_threshold = 0.7377
        mlflow.log_param("operational_threshold", operational_threshold)
        
        # 2. Métriques (Validation & OAD)
        y_pred_opt = model_champion.predict(X_val)
        y_proba_opt = model_champion.predict_proba(X_val)[:, 1]
        
        mlflow.log_metric("val_f1", f1_score(y_val, y_pred_opt, zero_division=0))
        mlflow.log_metric("val_precision", precision_score(y_val, y_pred_opt, zero_division=0))
        
        y_pred_oad = (y_proba_opt >= operational_threshold).astype(int)
        mlflow.log_metric("oad_f1_at_0.7377", f1_score(y_val, y_pred_oad, zero_division=0))
        
        # 4. SÉCURITÉ & TRAÇABILITÉ MLOps : Enregistrement du Dataset d'entraînement
        # On demande à MLflow de copier tout le contenu du dossier data/processed dans le serveur d'artéfacts
        logger.info(f"[MLflow Artifacts] Téléversement des datasets depuis '{processed_data_dir}'...")
        if os.path.exists(processed_data_dir) and os.listdir(processed_data_dir):
            # Le paramètre artifact_path="datasets" crée un sous-dossier propre dans MLflow
            mlflow.log_artifact(local_path=processed_data_dir, artifact_path="datasets")
            logger.success("Datasets d'entraînement (Splits CSV) figés et liés au Run MLflow.")
        else:
            logger.warning(f"Aucun fichier trouvé dans {processed_data_dir}. Le lignage des données n'a pas pu être établi.")

        # 4. Enregistrement et enregistrement physique du modèle
        mlflow.sklearn.log_model(
            sk_model=model_champion,
            artifact_path="model",
            registered_model_name="RandomForest_Agricultural_OAD"
        )

    logger.success(f"Modèle et données enregistrés avec succès (Run ID: {run.info.run_id})")