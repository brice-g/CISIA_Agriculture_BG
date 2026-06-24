# DATASHEET FOR DATASETS — PROJET CISIA AGRICULTURE

**Version du document :** 1.0
**Date d'audit :** 10 juin 2026
**Statut :** Officiel / Validé pour l'OAD

---

## 1. MOTIVATION (MOTIVATION)

* **Pour quel objectif le jeu de données a-t-il été créé ?**
  Le jeu de données a été conçu pour l'optimisation agronomique, le renforcement de la résilience climatique au sein de la coopérative agricole et le développement d'un Outil d'Aide à la Décision (OAD) capable de détecter de manière précoce les anomalies sur les parcelles agricoles. Cette définition claire sanctuarise une finalité légitime au sens du RGPD et interdit contractuellement toute dérive de surveillance ou de notation abusive des exploitants partenaires.

* **Qui a créé le jeu de données (par exemple, quelle équipe, quelle organisation) ?**
  L'équipe d'ingénierie des données et de recherche agronomique de la coopérative agricole.

* **Qui a financé la création du jeu de données ?**
  *Question a pauser au client* 
  Le projet a-t'il été intégralement financé par la coopérative agricole ? 

---

## 2. COMPOSITION (COMPOSITION & GESTION DES PII)

* **Que représentent les instances du jeu de données ?**
  Chaque instance (ligne) représente un relevé d'indicateurs biophysiques et environnementaux rattaché à une parcelle agricole et à une période d'observation spécifiques.

* **Combien d'instances y a-t-il au total (par exemple, nombre de lignes, de fichiers) ?**
  Le jeu de données initial est structuré autour de deux fichiers CSV principaux :

    * data/observations.csv : 10 000 lignes et 12 colonnes.

    * data/parcelles.csv : 500 lignes et 12 colonnes.

* **Le jeu de données contient-il des informations permettant d'identifier directement ou indirectement des personnes (PII) ?**
  Non. Dans le cadre d'une politique stricte de Privacy by Design, toutes les variables d'identification directe telles que Exploitant, Email, Telephone et NumSIRET ont été purgées et définitivement supprimées lors de l'ingestion afin de protéger la vie privée des exploitants et d'assurer une conformité totale avec le RGPD.

* **Quelles sont les variables majeures conservées pour l'analyse ?**
  Le dataset comprend des descripteurs biophysiques critiques : Temperature, Humidite, Pluviometrie_mm, NDVI (Indice de végétation), RendementEstime_t_ha, RendementMoyenZone_t_ha, et la variable cible AnomalieLabel.

---

## 3. COLLECTION PROCESS (PROCESSUS DE COLLECTE & FIABILITÉ IOT)

* **Comment les données ont-elles été collectées ?**
  Les données proviennent de flux hétérogènes et multi-sources combinant des capteurs IoT fixes (Stations météo au sol), de l'imagerie aérienne par Drone, des relevés de télédétection par Satellite, ainsi que des saisies Manuelles effectuées directement sur le terrain par les techniciens agricoles.

* **Quels sont les biais, erreurs ou limites connus du processus de collecte ?**
  L'audit de collecte met en évidence une fiabilité variable des capteurs terrain. Deux limites majeures sont documentées :

    * *Mécanismes de panne* : Présence de pertes de signal ou de dysfonctionnements matériels induisant d'importants volumes de données manquantes.

    * *Biais de couverture géographique* : Hétérogénéité territoriale marquée. Certaines régions historiques de la coopérative agricole sont sur-équipées en stations au sol, tandis que d'autres dépendent principalement de l'imagerie satellite, créant des disparités de densité et de précision de données.

---

## 4. PREPROCESSING/CLEANING/LABELING (TRAÇABILITÉ DU PIPELINE)

* **Quelles étapes de nettoyage ou de prétraitement ont été appliquées aux données ?** *Audit de qualité initial* : Le rapport d'audit a quantifié les anomalies de saisie et les manques physiques, dénombrant notamment 307 occurrences de valeurs manquantes sur le NDVI (3,07 %), 322 sur la Température, 146 sur l'Humidité, et 231 sur le Rendement Estimé.

    * *Imputation avancée* : Pour éviter les biais d'une suppression brute, les valeurs manquantes et aberrantes sur les colonnes biophysiques ont été imputées mathématiquement à l'aide d'un algorithme des k-plus proches voisins via l'objet KNNImputer(n_neighbors=5, weights='distance').

    * *Feature Engineering* : Création de la variable pivot RatioRendement (rapport entre le rendement estimé de la parcelle et le rendement moyen historique de sa zone agronomique). Une constante de sécurité epsilon (1e−5) a été formellement injectée au dénominateur pour prémunir le pipeline logiciel contre toute division par zéro accidentelle.

* **Comment la variable cible (anomalie) a-t-elle été définie ?**
  La variable binaire AnomalieLabel qualifie la présence d'un dysfonctionnement ou d'un stress agronomique aigu sur la parcelle.
  *Question a pauser au client* : 
  Par qui et sur quelle base la variable AnomalieLabel est-elle déterminée ?

---

## 5. UTILISATIONS & LOGIQUE DÉCISIONNELLE

* **À quelles tâches le jeu de données est-il destiné ?**
  Le dataset est exclusivement dédié à l'entraînement, la validation et le benchmark de modèles de classification supervisée (Régression Logistique en baseline atteignant un ROC AUC de 0,8405, puis algorithmes de type Random Forest, XGBoost et Gradient Boosting optimisés via Optuna) afin d'alimenter le moteur d'alerte de l'OAD.

* **Quelle configuration opérationnelle spécifique a été dictée par ce dataset ?**
  Pour immuniser la coopérative agricole contre le coût économique et organisationnel désastreux des fausses alertes (déplacements inutiles, perte de crédibilité auprès des agriculteurs), l'outil de décision sur le terrain a été configuré avec un seuil de probabilité optimal strict de 0,7390 (et non l'habituel 0,50). Ce calibrage minutieux permet d'atteindre une Précision parfaite de 100,00 % contre les fausses alarmes tout en maximisant le F1-Score à 0,8954.

* **Existe-t-il des restrictions ou des usages hors-scope ?**
  Oui. Le jeu de données ne doit en aucun cas être utilisé pour des prises de décision automatisées à 100 % sans validation ou supervision par un conseiller agronomique humain.

---

## 6. DISTRIBUTION

* Comment le jeu de données est-il distribué et stocké ?
  Le dataset est la propriété exclusive de la coopérative  agricole. Il est stocké sur des serveurs sécurisés et géré via le registre de données MLOps de la stack (notamment tracé à l'aide de MLflow). Il est soumis à un contrôle d'accès strict et n'est pas accessible au public.

---

## 7. MAINTENANCE (ÉVOLUTIVITÉ & ENTRAINEMENT CONTINU)

* **Qui soutient et assure la maintenance du jeu de données ?**
  L'équipe d'Architecture IA et le comité de gouvernance des données de la coopérative agricole.

* **Quelle est la stratégie de mise à jour face à l'évolution des données ?**

    * *Évolutivité technique (Découplage)* : L'architecture du système d'ingestion est conçue de manière totalement découplée (Message Queue & API-First) afin de permettre l'intégration future de nouvelles flux hétérogènes (flux de prévisions météo quotidiens, imagerie satellite haute résolution) via des connecteurs API dédiés, sans altérer le cœur du pipeline existant.

    * *Gestion des versions* : Le dataset applique un versionnage strict. La version actuelle basée sur les capteurs physiques terrain est étiquetée v1.0. L'intégration des API externes marquera le passage à la version v2.0.

    * *Continuous Training* (Réentraînement continu) : Un réentraînement automatisé du modèle est obligatoire à la fin de chaque campagne agricole afin de capturer les nouvelles variations et perturbations climatiques.

    * *Conditions de revalidation d'urgence* : Un audit immédiat des seuils de l'OAD et du dataset est déclenché par le système de monitoring si un Data Drift (dérive des données) significatif est détecté sur les capteurs, ou si le F1-score global descend en dessous du seuil critique de 0,80 en production.
