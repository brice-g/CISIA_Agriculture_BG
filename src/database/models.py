from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Date, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class FeatureStore(Base):
    """
    1. Table Features (Feature Store léger)
    Stocke le dataset complet nettoyé et enrichi AVANT encodage One-Hot.
    """
    __tablename__ = "features"

    observation_id = Column(String(50), primary_key=True, index=True)
    parcelle_id = Column(String(50), nullable=False, index=True)
    date_observation = Column(Date, nullable=False)
    date_mise_en_culture = Column(Date, nullable=False)
    code_postal = Column(String(10), nullable=False)
    
    # Variables catégorielles (mots réels, lisibles)
    capteur = Column(String(50), nullable=False)
    stade_culture = Column(String(50), nullable=False)
    type_culture = Column(String(50), nullable=False)
    type_sol = Column(String(50), nullable=False)
    irrigation = Column(String(50), nullable=False)
    region = Column(String(50), nullable=False)
    
    # Variables physiques IoT et météo
    temperature = Column(Float, nullable=False)
    humidite = Column(Float, nullable=False)
    pluviometrie_mm = Column(Float, nullable=False)
    surface_ha = Column(Float, nullable=False)
    ndvi = Column(Float, nullable=False)
    rendement_estime_t_ha = Column(Float, nullable=False)
    rendement_moyen_zone_t_ha = Column(Float, nullable=False)
    
    # Variables dérivées agronomiques (Feature Engineering)
    age_culture_jours = Column(Integer, nullable=False)
    ratio_rendement = Column(Float, nullable=False)
    indice_stress_thermo_hydrique = Column(Float, nullable=False)
    production_totale_estimee_t = Column(Float, nullable=False)
    ecart_ndvi_typique = Column(Float, nullable=False)
    
    # Cible d'entraînement
    anomalie_label = Column(Integer, nullable=False)
    
    # Métadonnées techniques MLOps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ValidatedFeedback(Base):
    """
    2. Table Validated_Feedbacks
    Centralise les retours d'observations des agronomes sur le terrain (Vrais/Faux Positifs).
    Le trigger d'orchestration écoutera le nombre de lignes ici (Alerte à 50 lignes).
    """
    __tablename__ = "validated_feedbacks"

    feedback_id = Column(Integer, primary_key=True, autoincrement=True)
    # Référence lâche ou stricte à l'observation d'origine
    observation_id = Column(String(50), nullable=False, index=True)
    agronome_username = Column(String(100), nullable=False)
    
    # Validation métier : True = Vraie anomalie constatée | False = Fausse alerte du modèle
    is_anomaly_validated = Column(Boolean, nullable=False)
    commentaire = Column(Text, nullable=True)
    
    validated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ShadowPrediction(Base):
    """
    3. Table shadow_predictions
    Stocke en arrière-plan les prédictions en conditions réelles du modèle candidat
    évalué en mode miroir (Shadow Mode) avant sa bascule officielle.
    """
    __tablename__ = "shadow_predictions"

    prediction_id = Column(Integer, primary_key=True, autoincrement=True)
    observation_id = Column(String(50), nullable=False, index=True)
    
    # Permet de savoir quel Run ID MLflow ou quelle version a fait la prédiction
    model_version = Column(String(100), nullable=False, index=True)
    
    # Score brut sorti par le modèle (proba entre 0 et 1)
    predicted_probability = Column(Float, nullable=False)
    # Label final après application du seuil OAD (0 ou 1)
    predicted_label = Column(Integer, nullable=False)
    
    # ground_truth sera rempli a posteriori quand la réalité terrain ou le feedback arrivera
    ground_truth = Column(Integer, nullable=True)
    
    predicted_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ModelPromotion(Base):
    """
    4. Table model_promotions
    Historique des changements de version et états des modèles (Shadow, Production, Archivé).
    """
    __tablename__ = "model_promotions"

    promotion_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), nullable=False, unique=True) # ID unique MLflow
    model_name = Column(String(100), default="RandomForest_Agricultural_OAD", nullable=False)
    model_version = Column(String(50), nullable=False)
    
    # Statut du cycle de vie : 'SHADOW', 'PRODUCTION', 'ARCHIVED'
    status = Column(String(20), nullable=False, index=True)
    
    promoted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    promoted_by = Column(String(100), default="CI-CD_Pipeline", nullable=False)
    
    # Stockage flexible des métriques clés (F1-score, Precision...) lors de la promotion
    performance_metrics = Column(JSON, nullable=True)