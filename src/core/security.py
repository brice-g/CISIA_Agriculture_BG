import hashlib
import os
from loguru import logger

def generate_parcelle_id(raw_identifier: str, secret_salt: str = None) -> str:
    """
    Génère un identifiant anonyme, unique et déterministe (ParcelleID) à partir d'une donnée nominative.
    
    Concept CISIA : On utilise SHA-256 pour que l'action soit irréversible (RGPD).
    On ajoute un 'salt' (sel) secret pour éviter les attaques par dictionnaire (arc-en-ciel).
    
    Args:
        raw_identifier (str): La donnée nominative (ex: "Exploitant_Dupont_Parcelle_A1").
        secret_salt (str, optional): Clé secrète. Si None, cherche dans les variables d'environnement.
        
    Returns:
        str: Le hash SHA-256 tronqué à 16 caractères pour servir de ParcelleID propre.
    """
    # Si aucun sel n'est fourni, on le récupère de l'environnement (sécurité accrue)
    if not secret_salt:
        secret_salt = os.getenv("SECRET_SALT_RGPD", "CleSecreteDeSecoursCooperative2026")

    if not raw_identifier or not isinstance(raw_identifier, str):
        logger.error("L'identifiant brut fourni est invalide ou vide.")
        raise ValueError("L'identifiant brut doit être une chaîne de caractères non vide.")

    # Concaténation de la donnée et du sel secret
    salted_data = f"{raw_identifier}{secret_salt}"
    
    # Application du protocole de hachage (encodage en bytes requis pour hashlib)
    hash_object = hashlib.sha256(salted_data.encode('utf-8'))
    
    # Récupération de la version hexadécimale du hash
    full_hash = hash_object.hexdigest()
    
    # On retourne les 16 premiers caractères : suffisant pour éviter les collisions sur une coopérative
    return f"PRC-{full_hash[:16].upper()}"