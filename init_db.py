"""
Script d'initialisation des tables PostgreSQL pour le projet CISIA
"""

from loguru import logger
from src.database.db_manager import DatabaseManager

# TRÈS IMPORTANT : On doit importer les modèles pour que SQLAlchemy 
# lise le fichier et "sache" que les tables existent avant de lancer la création.
from src.database.models import FeatureStore, ValidatedFeedback, ShadowPrediction, ModelPromotion

def main():
    logger.info("Lancement du script de création des tables...")
    
    # Instanciation de ton manager (il va lire le .env et se connecter à fastia_data)
    manager = DatabaseManager()
    
    try:
        # Appel de ta méthode qui contient Base.metadata.create_all
        manager.init_db()
        logger.success("Toutes les tables ont été injectées dans PostgreSQL avec succès !")
    except Exception as e:
        logger.error(f"Échec de l'initialisation : {e}")

if __name__ == "__main__":
    main()