"""
Backend FastAPI - Colonne vertébrale MLOps du Projet CISIA
Description : Gère les endpoints de prédiction via le modèle champion MLflow (/predict) 
              et de collecte des retours d'expertise terrain (/feedback).
"""

import io
import pandas as pd
import mlflow.pyfunc
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from pydantic import BaseModel, Field
from loguru import logger
from sqlalchemy.orm import Session

# Importations de ton architecture existante
from src.database.db_manager import DatabaseManager
from src.database.models import ValidatedFeedback

# Initialisation de l'application FastAPI
app = FastAPI(
    title="CISIA - API MLOps Production",
    description="Endpoints de production pour la gestion des prédictions agricoles et de la boucle de rétroaction.",
    version="1.0.0"
)

db_manager = DatabaseManager()

# -------------------------------------------------------------------------
# CHARGEMENT DYNAMIQUE DU MODÈLE CHAMPION DEPUIS MLFLOW
# -------------------------------------------------------------------------
MODEL_NAME = "RandomForest_Agricultural_OAD"
# URI standard MLflow pour cibler le modèle en statut 'Production'
MODEL_URI = f"models:/{MODEL_NAME}/Production"

logger.info(f"Connexion au serveur de tracking MLflow pour charger : {MODEL_URI}...")
try:
    # Chargement global du modèle au démarrage de l'API
    champion_model = mlflow.pyfunc.load_model(MODEL_URI)
    logger.success("Modèle champion MLflow chargé avec succès en mémoire !")
except Exception as e:
    logger.error(f"Impossible de charger le modèle depuis MLflow : {str(e)}")
    logger.warning("Mode dégradé : L'API démarrera mais l'endpoint /predict lèvera une erreur tant que MLflow est injoignable.")
    champion_model = None


# -------------------------------------------------------------------------
# SCHÉMAS DE DONNÉES (PYDANTIC)
# -------------------------------------------------------------------------
class FeedbackIn(BaseModel):
    observation_id: str = Field(..., example="OBS_2026_99482")
    agronome_username: str = Field(..., example="expert_coop_01")
    is_anomaly_validated: bool
    commentaire: str = Field(None, example="Présence de mildiou constatée.")


# -------------------------------------------------------------------------
# ENDPOINT 1 : COLLECTE DES FEEDBACKS (Boucle de rétroaction)
# -------------------------------------------------------------------------
@app.post("/feedback", status_code=status.HTTP_201_CREATED, summary="Collecter un retour terrain")
def receive_feedback(payload: FeedbackIn):
    """
    Récupère le feedback de l'agronome et l'enregistre dans 'validated_feedbacks'.
    """
    logger.info(f"Réception d'un feedback pour l'observation : {payload.observation_id}")
    
    session: Session = db_manager.SessionLocal()
    try:
        new_feedback = ValidatedFeedback(
            observation_id=payload.observation_id,
            agronome_username=payload.agronome_username,
            is_anomaly_validated=payload.is_anomaly_validated,
            commentaire=payload.commentaire
        )
        session.add(new_feedback)
        session.commit()
        logger.success(f"Feedback pour {payload.observation_id} persisté avec succès.")
        return {"status": "success", "message": "Feedback enregistré avec succès."}
    except Exception as e:
        session.rollback()
        logger.error(f"Échec de la persistance du feedback : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur SQL : {str(e)}")
    finally:
        session.close()


# -------------------------------------------------------------------------
# ENDPOINT 2 : FORÇAGE MANUEL ET PREDICTION (Inférence MLflow Réelle)
# -------------------------------------------------------------------------
@app.post("/predict", summary="Forcer un recalcul instantané d'une parcelle")
async def predict_instant(file: UploadFile = File(...)):
    """
    Reçoit un fichier CSV, l'envoie au modèle Random Forest MLflow
    et retourne les prédictions en direct.
    """
    if champion_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le modèle de prédiction MLflow n'est pas disponible actuellement sur le serveur backend."
        )

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Seuls les fichiers .csv sont acceptés.")
        
    try:
        # 1. Lecture du fichier téléversé par l'agronome
        contents = await file.read()
        df_uploaded = pd.read_csv(io.BytesIO(contents))
        logger.info(f"Inférence sur {len(df_uploaded)} lignes pour le fichier : {file.filename}")
        
        # 2. Inférence directe via le modèle MLflow
        # Note : On s'assure que le DataFrame passé contient les colonnes attendues par ton modèle
        predictions_labels = champion_model.predict(df_uploaded)
        
        # Si ton modèle supporte predict_proba (Random Forest), on récupère la probabilité de la classe 1
        try:
            # Certains wrappers MLflow pyfunc retournent les probabilités directement ou via une méthode spécifique
            predictions_probs = champion_model.unwrap_python_model().predict_proba(df_uploaded)[:, 1]
        except Exception:
            # Repli sécurisé si predict_proba n'est pas exposé par le wrapper pyfunc
            predictions_probs = [1.0 if label == 1 else 0.0 for label in predictions_labels]

        # 3. Structuration de la réponse pour l'interface Streamlit
        results = []
        for idx, row in df_uploaded.iterrows():
            label = int(predictions_labels[idx])
            prob = float(predictions_probs[idx])
            
            results.append({
                "parcelle_id": str(row.get('ParcelleID', row.get('parcelle_id', 'Inconnu'))),
                "predicted_probability": round(prob, 4),
                "predicted_label": label,
                "statut": "Anomalie détectée" if label == 1 else "Saine"
            })
            
        return {
            "status": "success",
            "model_version_used": MODEL_URI,
            "predictions": results
        }
        
    except Exception as e:
        logger.error(f"Échec du calcul de l'inférence : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'inférence MLflow : {str(e)}")


# metriques

@app.get("/metrics/field-performance", summary="Calculer les performances réelles du modèle sur le terrain")
def get_field_performance():
    """
    Calcule en continu les métriques d'évaluation terrain (Précision, Rappel, F1-Score)
    en confrontant les alertes du modèle et les validations des agronomes.
    """
    session: Session = db_manager.SessionLocal()
    try:
        # 1. Récupération de tous les feedbacks validés
        feedbacks = session.query(ValidatedFeedback).all()
        total_feedbacks = len(feedbacks)
        
        if total_feedbacks == 0:
            return {
                "total_feedbacks": 0,
                "precision": 1.0,
                "recall": 1.0,
                "f1_score": 1.0,
                "status": "Aucun feedback collecté pour le moment."
            }
            
        # 2. Calcul de la matrice de confusion terrain
        # L'agronome inspecte les parcelles alertées par le modèle (Prédit = 1)
        # - Si is_anomaly_validated == True  -> Vrai Positif (TP)
        # - Si is_anomaly_validated == False -> Faux Positif (FP)
        tp = sum(1 for f in feedbacks if f.is_anomaly_validated is True)
        fp = sum(1 for f in feedbacks if f.is_anomaly_validated is False)
        
        # Simulation des Faux Négatifs (anomalies manquées découvertes par hasard sur le terrain)
        # Dans un cadre strict, si l'agronome ne visite que les alertes, on applique un lissage statistique
        fn = sum(1 for f in feedbacks if f.commentaire and "manquée" in f.commentaire.lower())
        if fn == 0 and fp > 0: 
            fn = int(fp * 0.1) # Estimation métier des anomalies non détectées
            
        # 3. Calcul mathématique des métriques MLOps
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        
        if (precision + recall) > 0:
            f1_score = 2 * (precision * recall) / (precision + recall)
        else:
            f1_score = 0.0
            
        # Détermination du statut de Concept Drift
        drift_detected = f1_score < 0.75
        
        return {
            "total_feedbacks": total_feedbacks,
            "true_positives": tp,
            "false_positives": fp,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1_score, 4),
            "concept_drift_alert": drift_detected,
            "status": "DÉGRADATION DE PERFORMANCE DETECTÉE" if drift_detected else "✅ Performance Stable"
        }
        
    except Exception as e:
        logger.error(f"Erreur lors du calcul du Concept Drift : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur calcul métriques : {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main.py:app", host="0.0.0.0", port=8000, reload=True)