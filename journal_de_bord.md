# JOURNAL DE BORD : SYSTÈME D'AGRICULTURE DE PRECISION - DÉTECTION D'ANOMALIES PARCELLAIRES

**Contexte** : Face aux dérives du changement climatique, à la pression croissante sur les ressources en eau et à l'émergence de nouvelles maladies, le secteur agricole doit impérativement optimiser ses interventions et réduire l'usage d'intrans chimiques. Mandaté par une coopérative agricole régionale, ce projet s'inscrit dans l'exploitation des volumes massifs de données générés par les exploitations modernes (capteurs IoT au sol, images satellites, drones, stations météo, relevés manuels).

**Objectif** : Développer, optimiser et concevoir l'architecture d'un Outil d'Aide à la Décision (OAD) permettant la détection d’anomalies parcellaires à partir de données d’observation historiques, basé sur un modèle d'intelligence artificielle.

## Session 1 : Cadrage Métier, Ingestion et Audit de Qualité (RGPD & Anomalies)

* **Objectif de la session** : 
    * Réaliser le profilage et l'analyse exploratoire (EDA) des référentiels de données de la coopérative.

    * Évaluer la qualité physique des variables environnementales et déceler les anomalies ou valeurs aberrantes.

    * Mesurer le déséquilibre de la variable cible pour orienter la stratégie de validation et de modélisation.

    * Auditer la conformité réglementaire (RGPD / AI Act) concernant les données d'identification des exploitants.

    * Définir l'architecture technique globale du pipeline d'ingestion et de traitement des flux.

* **Travail Réalisé & Choix Techniques** :
    * **Ingestion et volumétrie des sources** : Chargement via Pandas de deux fichiers CSV :

        * data/observations.csv : 10 000 lignes et 12 colonnes (suivi des relevés capteurs et terrain).

        * data/parcelles.csv : 500 lignes et 12 colonnes (référentiel structurel des exploitations).

    * **Analyse de la variable cible (AnomalieLabel)** :

        * Quantification précise : 8 832 situations normales (0) et 1 168 situations d'anomalies (1).

        * Constat de déséquilibre : Le jeu de données présente un déséquilibre significatif avec 11,7 % d'anomalies contre 88,3 % de cas normaux.

        * Décision méthodologique : Rejet de la métrique d'exactitude (Accuracy) en raison de l'Accuracy Trap (un modèle naïf atteindrait 88,3 % d'exactitude sans détecter aucune anomalie). Orientation du projet vers des métriques adaptées : F1-Score, Rappel (pour ne rater aucune anomalie) et Précision (pour limiter les fausses alertes).

        * Choix de découpage : Obligation d'utiliser une validation croisée ou un découpage stratifié (stratify=y ou StratifiedKFold) afin de maintenir la proportion de 11,7 % d'anomalies dans les sous-ensembles d'entraînement et de test.

    * **Analyses graphiques et visualisations :**

        * **Histogrammes** : Confirmation visuelle des erreurs de capteurs (points isolés à l'extrême droite des distributions). Identification d'une distribution bimodale des rendements (expliquée par la coexistence de cultures différentes comme la vigne et le maïs) et d'une distribution asymétrique à droite pour la pluviométrie.

        * **Matrice de corrélation** : Identification de la pluviométrie (0,41) et du NDVI (-0,25) comme les principaux prédicteurs linéaires d'anomalies. Constat de relations faibles ou non-linéaires pour la température et l'humidité, légitimant l'usage futur de modèles non-linéaires (arbres de décision, Random Forest, XGBoost).

        * **Boxplots par statut d'anomalie** : Démonstration que les valeurs aberrantes physiques (ex: humidité > 120 %) apparaissent majoritairement dans la classe "Normal" (0). Le label désigne donc des anomalies agronomiques réelles et non des pannes matérielles.

        * **Analyse par type de capteur** : Le taux d'anomalie reste strictement plat à ~11,7 % quelle que soit la source (IoT, satellite, drone, manuel). La variable Capteur n'a aucun pouvoir prédictif.

        * **Analyse temporelle (Saisonnalité)** : Le taux mensuel fluctue légèrement entre 10 % et 13,4 % au rythme des campagnes agricoles. Ce signal impose d'abandonner le découpage purement aléatoire au profit d'un Time-Based Split (ex: train sur 2024, test sur 2025) ou d'un TimeSeriesSplit pour interdire tout Data Leakage (fuite de données du futur).

        * **Heatmap des valeurs manquantes** : Distribution diffuse et indépendante de type MCAR (Missing Completely At Random), confirmant qu'il s'agit de micro-coupures de capteurs et non d'une panne réseau globale. 

* **Problèmes rencontrés & Solutions** :

| # | Anomalies constatées à l'Audit | Quantification | Solution & Impact Architectural
--- | --- | --- | ---
1 | **Exposition de données PII** (Email, Téléphone, NumSIRET) | 95,40 % des fiches affectées (477 Email / 464 Tel / 453 SIRET) | Couche Sécurité & RGPD : Extraction et chiffrement des données personnelles vers un coffre-fort numérique externe. Remplacement de l'identité par un jeton anonyme (ExploitantID) dans le pipeline ML.
2 | **Données manquantes** (NDVI et variables physiques) | 307 manques NDVI (3,07 %) / 539 lignes physiques cumulées (5,39 %) | Couche de Nettoyage : Rejet de la suppression brute de lignes. Application d'une stratégie d'imputation robuste par la médiane (ou KNNImputer) calculée par type et stade de culture.
3 | **Aberrations du NDVI** (Hors de l'intervalle strict [-1, 1]) | 68 occurrences (0,68 %) avec un maximum irréaliste à 2,4537 | Écrêtage logique (clipping) pour maintenir strictement les valeurs de l'indice entre -1 et 1 afin d'éviter la distorsion des gradients.
4 | **Pluviométries négatives** (Erreur de zéro logique de l'IoT) | 90 occurrences (0,90 %) avec un minimum à -10,0 mm | Redressement systématique des valeurs négatives à 0,0 mm pour éviter le Shortcut Learning (le modèle apprendrait la signature de la panne).
5 | **Outliers thermiques et d'humidité** (Surchauffe matérielle) | 108 occurrences thermiques (1,08 %) avec un max à 79,8°C et humidité à 148,6% | Filtrage et écrêtage automatique via un bloc de pré-traitement technique en amont de la modélisation agronomique.
6 | **Incohérences de la table parcelles** (Surfaces et codes postaux) | 18 CP invalides ("XXXXX" - 3,60 %) / 28 Surfaces ≤ 0 (5,60 %) | Rectification/exclusion des surfaces aberrantes (min à -4,56 ha). Typage de la colonne DateMiseEnCulture (actuellement en object) vers le format datetime64.
7 | **Multicolonnalité critique entre les rendements** | Corrélation linéaire élevée à 0,85 entre RendementEstimé et RendementMoyenZone | Arbitrage lors de la Feature Selection : suppression d'une des variables ou orientation de l'architecture vers des modèles d'arbres tolérant cette redondance.
8 | **Variable non-discriminante** (Capteur) | Profil parfaitement plat à ~11,7 % d'anomalies | Exclusion définitive de la colonne Capteur du dataset final pour éviter la création de colonnes d'encodage (One-Hot) inutiles et alléger l'IA.

* **Prochaines Étapes (To-Do List)** :
    * Procéder à la fusion (merge) logique des tables nettoyées sur la clé ParcelleID.
    * Exécuter le pipeline de remédiation : anonymisation RGPD, imputation des données manquantes, redressement des pluviométries négatives et écrêtage du NDVI.
    * Procéder à l'ingénierie des caractéristiques (Feature Engineering).

---

## Session 2 : Préparation des Données et Questionnement du Traitement Éthique

* **Objectif de la session** : 
    * Exécuter le pipeline de nettoyage technique et de redressement des variables biophysiques, météorologiques et structurelles.

    * Mettre en œuvre une stratégie d'imputation intelligente basée sur la connaissance métier (médiane conditionnelle groupée).

    * Réaliser la jointure relationnelle des tables et appliquer les verrous RGPD de Privacy by Design (anonymisation irréversible).

    * Enrichir le signal agronomique par la création de variables dérivées non-linéaires (Feature Engineering).

    * Procéder à la vectorisation (encodage One-Hot) et au partitionnement stratifié (Train/Val/Test) des données.

    * Configurer mathématiquement les pénalisations de la fonction de coût pour traiter le déséquilibre de la classe cible.

    * Conduire l'analyse d'impact éthique sur le profilage comportemental et la documentation du cycle de vie des données.

* **Travail Réalisé & Choix Techniques** :
    * **Nettoyage et alignement des lois physiques** (Étape 2.1) :

        * **NDVI** : Conversion en NaN des aberrations logicielles (hors de l'intervalle strict [−1,1], maximum à 2,4537) pour centraliser le traitement et prémunir les modèles contre la distorsion des gradients.

        * **Pluviométrie** : Redressement immédiat des anomalies matérielles (valeurs négatives jusqu'à -10,0 mm) et des NaN par la constante 0.0 (hypothèse métier du jour sec), bloquant le risque que les modèles apprennent des règles efficaces sur des tests standards mais peu robustes en conditions réelles (Shortcut Learning).

        * **Température** : Neutralisation des pannes et surchauffes de boîtiers (hors des bornes régionales [−15∘C,55∘C], maximum à 79,8°C) par leur mutation en NaN afin de stabiliser la variance de la variable.

        * **Référentiel géomarketing** : 
            * **Codes potaux** : Remplacement de l'erreur 'XXXXX' par NaN dans la colonne CodePostal.
            * **Surfaces des parcelles** : Transformation des surfaces invalides administratvement (≤0 ha, minimum à -4,56 ha) en NaN avant redressement.

        * **Validation structurelle (Doublons & Intégrité Relationnelle)** : Le pipeline confirme 0 doublon exact et 0 observation orpheline. Volume après filtrage : 10 000 observations et 482 parcelles valides (18 parcelles supprimées définitivement pour cause de CodePostal invalide). NaNs restants à ce stade : Température (322), Humidité (146), NDVI (375), RendementEstime_t_ha (231).

    * **Imputation ciblée par connaissance métier** (Étape 2.2) :

        * Rejet de l'imputation par moyenne/médiane globale (qui écrase la variance et lisse les anomalies recherchées) et du KNN pur (aveugle aux réalités spatio-temporelles).

        * Choix d'une Domain-Knowledge Imputation par médiane conditionnelle groupée :

            * **Surface_ha** : Médiane par Region + repli (fallback) sur la médiane globale pour sécuriser les parcelles isolées.

            * **NDVI** : Médiane groupée par TypeCulture et StadeCulture pour respecter scrupuleusement la cinétique de croissance et la vigueur propre à chaque espèce.

            * **Température & Humidité** : Médiane groupée par Region et StadeCulture pour émuler la panne d'un capteur IoT par les valeurs des parcelles voisines au même instant climatique.

        * **Résultat** : Validation du module avec 0 NaN restant sur l'ensemble des jeux de données.

    * **Jointure relationnelle et Anonymisation RGPD** (Étape 2.3) :

        * **Fusion par jointure interne** (Inner Join) sur la clé pivot `ParcelleID` pour aligner les relevés de capteurs dynamiques avec les caractéristiques structurelles stables des sols (TypeSol, Irrigation).

        * **Gouvernance & Sécurité** : Exclusion stricte, sélective et définitive des colonnes d'identification directe (Exploitant, Email, Telephone, NumSIRET) avant la jointure.

        * **Métriques du flux** : Passage de 10 000 observations à 9 665 lignes dans la matrice finale df_master (335 lignes d'observations légitimement éliminées par l'absence des 18 parcelles aux codes postaux corrompus). Audit automatisé validé à 100% avec 0 Donnée à Caractère Personnel (DCP) détectée dans la matrice d'apprentissage.

    * **Ingénierie des caractéristiques / Feature Engineering** (Étape 2.4) : Création et injection de 5 nouvelles variables dérivées basées sur des interactions physiques et agronomiques :

        * `AgeCulture_jours` (DateObservation−DateMiseEnCulture) : Indicateur continu de maturité biologique. Statistiques : Moyenne = 156,0 jours | Min = 0,0 | Max = 634,0.

        * `RatioRendement` (RendementEstime_t_ha/RendementMoyenZone_t_ha) : Révélateur direct de sous-performance locale sous le seuil de 1,0. Statistiques : Moyenne = 0,98 | Min = 0,16 | Max = 3,65.

        * `IndiceStressThermoHydrique` (Temperature×(100−Humidite)) : Interaction non-linéaire émulant la sécheresse intense (valeurs positives élevées) et le gel (valeurs négatives). Statistiques : Moyenne = 584,5 | Min = -1235,4 | Max = 3602,6.

        * `ProductionTotaleEstimee_t` (Surface_ha×RendementEstime_t_ha) : Prise en compte de l'effet d'échelle de la biomasse et du poids systémique de la parcelle. Statistiques : Moyenne = 534,8 t | Min = 1,95 t | Max = 2275,5 t.

        * `Ecart_NDVI_Typique` (NDVI−Meˊdiane(NDVI) par couple Culture/Stade) : Isolat de la perte de vigueur végétale réelle déconnectée du cycle naturel de jaunissement de la plante. Statistiques : Moyenne = ~0,00 | Min = -0,56 | Max = 0,35.

        * Dimension finale de la matrice analytique globale (lignes, colonnes): (9665, 24).

    * **Encodage et partitionnement stratifié** (Étape 2.5) :

        * **Purge des colonnes techniques ou brutes non prédictives** : ObservationID, ParcelleID, DateObservation, DateMiseEnCulture (capturée par l'âge) et CodePostal.

        * **Encodage nominal** : Application du One-Hot Encoding sur Capteur, StadeCulture, TypeCulture, TypeSol, Irrigation et Region, portant le dataset à 39 caractéristiques mathématiques (features).

        * Découpage tripartite et étanche avec stratification stricte (stratify=y, random_state=42) pour figer la représentativité face au déséquilibre :

            * **Ensemble d'Entraînement (Train)** : 6 765 lignes | Taux d'anomalies : 11,66 %

            * **Ensemble de Validation (Val)** : 1 450 lignes | Taux d'anomalies : 11,66 %

            * **Ensemble de Test (Test)** : 1 450 lignes | Taux d'anomalies : 11,66 %

    * **Gestion industrielle du déséquilibre de classe** (Étape 2.6) :

        * **Rejet de l'Option A** (Ne rien faire : maximisation de l'Accuracy au détriment du Rappel, catastrophique pour la détection des risques).

        * **Rejet de l'Option B** (SMOTE : exclu car la création par interpolation de points synthétiques dans un espace encodé à haute dimension engendre des hallucinations biologiques et des combinaisons physiques impossibles sur le terrain).

        * **Sélection de l'Option C** : Ajustement des poids de la fonction de perte (Cost-sensitive learning) pour sur-pénnaliser les erreurs sur la classe minoritaire sans altérer la stricte réalité biologique des mesures IoT.

        * Paramétrage des vecteurs de modélisation :

            * Poids Scikit-Learn (Dictionnaire) : {0: 0.5660140562248996, 1: 4.287072243346008}

            * Poids XGBoost (scale_pos_weight) : 7.5741 (Ratio de 1 anomalie pour 7,57 situations normales).

* **Réflexion Architecturale, Réglementaire & Éthique** (Étape 2.7) :

    * **Analyse de la feature Exploitant** : Bien qu'historiquement corrélée aux motifs d'anomalies (ex: taille d'infrastructure différente), l'inclusion de l'identité de l'agriculteur est totalement inacceptable :

        * **Technique** : Elle génère un biais de mémorisation massif (surapprentissage) qui détruit la capacité de généralisation de l'IA lors d'un changement de nom du propriétaire ou de l'arrivée de nouveaux adhérents à la coopérative.

        * **Réglementaire** : Elle viole gravement les principes du RGPD de minimisation des données (Art. 5.1.c) et de limitation des finalités (Art. 5.1.b) en détournant une finalité d'optimisation agronomique vers du profilage comportemental sans consentement explicite.

        * **Éthique & Sociale** : Elle induit un risque de dérive de surveillance et de notation sociale, transformant l'outil d'aide à la décision en un système d'évaluation automatique capable de discriminer un agriculteur.

    * **Adéquation de la Datasheet de Gebru** : Standard indispensable retenu pour assurer la gouvernance et la traçabilité industrielle du projet. Elle consigne la motivation (résilience climatique), verrouille la conformité de la purge des PII (Composition), documente les limites et pannes (Collection Process), justifie scientifiquement le choix du calcul des poids face au SMOTE (Preprocessing) et sécurise la propriété collective ainsi que la souveraineté des données de la coopérative (Uses & Maintenance).

* **Prochaines Étapes (To-Do List)** :
    * Initialiser la phase de modélisation en entraînant les architectures non-linéaires sélectionnées (Random Forest, XGBoost).

    * Soumettre les algorithmes aux matrices de coûts configurées (class_weight / scale_pos_weight).

    * Évaluer les performances sur le sous-ensemble de validation via les métriques prioritaires : F1-Score, Rappel et Précision.

---

## Session 3 : Construction, Évaluation des Modèles et Architecture MLOps

* **Objectif de la session** : 
    * Entraîner une Baseline linéaire et benchmarker trois architectures avancées basées sur des arbres de décision.

    * Sélectionner le modèle champion selon les exigences métiers (compromis Précision/Rappel) et l'optimiser via Optuna.

    * Assurer la traçabilité et la gouvernance du cycle de vie du modèle optimal à l'aide de MLflow.

    * Valider définitivement les performances de généralisation de la solution sur le jeu de test confidentiel.

    * Modéliser l'architecture MLOps cible pour industrialiser, monitorer et réentraîner le modèle face aux dérives climatiques.

    * Concevoir l'interface opérationnelle (Streamlit) comme composant actif des boucles de rétroaction de production.

* **Travail Réalisé & Choix Techniques** :
    * **Baseline - Régression Logistique** (Étape 3.1) :

        * **Préparation** : Application d'un StandardScaler configuré exclusivement sur l'ensemble d'entraînement pour empêcher tout phénomène de fuite de données (Data Leakage). Activation de la pondération class_weight='balanced' calculée en section 2.6.

        * **Résultats de validation** : Score ROC AUC de 0,8391 et Accuracy de 0,8345. Sur la classe critique (Anomalie), le modèle affiche une Précision de 0,38 (générant près de 62 % de fausses alertes) et un Rappel insuffisant de 0,69 (69 %). La saturation des équipes et le manque de sécurité des récoltes entraînent le rejet de ce modèle linéaire.

    * **Benchmark de 3 modèles supplémentaires** (Étape 3.2) :

        * Mise en compétition de trois algorithmes non-linéaires entraînés sur la matrice brute (insensibles à l'échelle) : **Random Forest** (scikit-learn), **XGBoost** (xgboost) et **Gradient Boosting** (scikit-learn).

        * Tableau comparatif des performances (Validation) :

            * **Régression Logistique** : Accuracy = 0,8345 | Précision = 0,3836 | Rappel = 0,6923 | F1 = 0,4937 | ROC AUC = 0,8391

            * **Random Forest** : Accuracy = 0,9745 | Précision = 0,9714 | Rappel = 0,8047 | F1 = 0,8803 | ROC AUC = 0,9129

            * **XGBoost** : Accuracy = 0,9724 | Précision = 0,9574 | Rappel = 0,7988 | F1 = 0,8710 | ROC AUC = 0,9165

            * **Gradient Boosting** : Accuracy = 0,9717 | Précision = 0,9571 | Rappel = 0,7929 | F1 = 0,8673 | ROC AUC = 0,9136

        * **Sélection du Champion** : Bien que XGBoost détienne la meilleure discrimination globale (ROC AUC de 0,9165), le modèle Random Forest est désigné champion. Il présente une réduction drastique du bruit industriel (Précision de 97,14 %) et offre le meilleur compromis métier avec un Rappel maximal (80,47 %) et le F1-score le plus élevé (0,8803).

    * **Interprétabilité et Feature Importance** (Étape 3.3) :

        * L'audit des structures décisionnelles du Random Forest démontre la supériorité de l'expertise agronomique sur le signal brut :

            * `RatioRendement` se classe au 1er rang (~19 %) comme le signal d'alarme le plus puissant.

            * `Ecart_NDVI_Typique` se positionne au 2e rang (~14 %) pour identifier les anomalies de croissance (maladies, ravageurs).

            * Les variables dérivées écrasent les métriques brutes de l'IoT (NDVI brut, Pluviométrie, Humidité, Température), validant la phase de Feature Engineering.

    * **Optimisation des hyperparamètres via Optuna** (Étape 3.4) :

        * Recherche bayésienne des hyperparamètres optimaux pour le Random Forest : {'n_estimators': 267, 'max_depth': 23, 'min_samples_split': 8, 'min_samples_leaf': 3}.

        * **Résultat** : Le score ROC AUC sur l'ensemble de validation **progresse à 0,9202**.

    * **Gouvernance et Enregistrement dans MLflow** (Étape 3.5) :

        Réentraînement du modèle optimal et sanctuarisation dans le MLflow Model Registry sous le nom de run : Random Forest-optuna-best. Les paramètres, les artefacts binaires et le score ROC AUC (0,9202) y sont consignés de manière immuable pour les futures phases de comparaison.

    * **Évaluation finale sur le jeu de test** (Étape 3.6) :

        * Confrontation finale et définitive du modèle optimisé sur le jeu de test étanche (1 450 lignes dont 169 anomalies) :

            * Précision globale (Anomalie) : 94,63 % (Seulement 8 fausses alertes sur 1 450 parcelles surveillées).

            * Rappel global (Anomalie) : 83,43 % (Plus de 83 % des sinistres réels sont détectés).

            * F1-Score : 0,8868 | Accuracy : 0,9752 | ROC AUC : 0,9212.

        * Généralisation : Le score ROC AUC sur le jeu de test (0,9212) surpasse la validation (0,9202), écartant tout risque de surapprentissage et qualifiant scientifiquement le pipeline pour la production.

* **Réflexion Architecturale — MLOps** (Étape 3.7) : Le déploiement en environnement de production s'articule autour de cinq piliers clés

    * **A. Stratégie de Déploiement (Serving)** : Architecture conteneurisée via Docker Compose isolant l'API, PostgreSQL et Streamlit. Inférence hybride associant un mode Batch nocturne (Cron job pour rafraîchir globalement les statuts) et un mode Request-Response (API FastAPI avec schémas Pydantic via le endpoint POST /predict) permettant aux techniciens de forcer un recalcul immédiat après un survol de drone ou un relevé IoT. Intégration d'un cache local pour contrer les coupures réseau en zone blanche rurale.

    * **B. Registre et Gouvernance** : Utilisation de DVC (Data Version Control) pour tracer les versions de données et atténuer les biais de déclaration identifiés sur les capteurs manuels. Centralisation des artefacts dans le MLflow Model Registry. L'automatisation CI/CD bloque toute promotion en production si le gain de performance du candidat est inférieur à un seuil strict (ΔF1-Score≥0,02) par rapport au modèle actif. Historisation des transitions dans la table PostgreSQL model_promotions.

    * **C. Monitoring des Dérives (Drift)** : Calcul continu du PSI (Population Stability Index) sur les caractéristiques numériques hautement sensibles aux pannes ou à l'usure matérielle (Humidite_Sol, Pluviometrie). Un seuil critique PSI≥0,20 déclenche une alerte immédiate de dégradation de calibration (Data Drift). Surveillance du Concept Drift via l'exposition du endpoint POST /feedback mesurant en temps réel l'évolution du F1-Score réel face aux nouvelles pratiques culturales.

    * **D. Entraînement Continu (CT) et Sécurisation** : Automatisation de la boucle de réentraînement par le script `triggers.py` selon trois déclencheurs logiques : atteinte d'un volume critique de 50 nouveaux feedbacks validés par le terrain, dérive confirmée (PSI≥0,20), ou clôture calendaire d'une campagne de récolte. Ré-optimisation automatique par Optuna. Sécurisation des déploiements via un protocole en Shadow Mode : duplication transparente des requêtes réelles dans la table shadow_predictions pour s'assurer que les micro-imputations quotidiennes (de type MCAR) ne créent aucun artefact ou distorsion mathématique avant la bascule officielle.

    * **E. Vue Opérationnelle (Interface Streamlit)** : L'interface utilisateur est intégrée comme le maillon actif de la boucle MLOps :

        * **Restitution (Sorties)** : Cartographie dynamique des risques (vert/orange/rouge), tableau de bord trié par score d'urgence pour prioriser les tournées, et module d'explicabilité XAI traduisant en langage clair l'importance locale des variables (ex : « Alerte déclenchée par une baisse de 15 % du RatioRendement... »).

        * **Interactions (Entrées)** : Forçage manuel via l'interface (envoi de fichiers vers le endpoint /predict traité par FastAPI) et Validation terrain par une simple case à cocher (Vrai/Faux Positif, nature du stress : hydrique, maladie, ravageur) reliée au endpoint /feedback.

        * **Clôture de la boucle** : Les feedbacks enrichissent en continu la table PostgreSQL, activant le script `triggers.py` dès que le seuil des 50 retours qualifiés est franchi, ce qui ré-optimise le modèle sur les réalités courantes du terrain.

* **Prochaines Étapes (To-Do List)** :
    * **Optimisation Opérationnelle et Arbitrage Économique**

        * Modéliser les risques métiers : Cartographier les quatre quadrants de décision (Vrais Positifs, Faux Négatifs, Faux Positifs, Vrais Négatifs) en fonction de leur impact sur le rendement et les ressources de la coopérative.

        * Optimiser le seuil de décision sur la courbe Précision-Rappel pour gérer la contrainte de ressources.

        * Appliquer le seuil recommandé
    
    * **Plan de correction des biais pour la Version 2**
    * **Conformité AI Act, RGPD et Éthique**

---

## Session 4 : Analyse des Risques, Qualification Réglementaire et Éthique du Système

* **Objectif de la session** : 
    * Traduire les prédictions mathématiques en décisions opérationnelles à l'aide d'une matrice d'impact économique.

    * Optimiser le seuil de classification pour calibrer l'Outil d'Aide à la Décision (OAD) selon les contraintes de ressources de la coopérative.

    * Identifier et documenter les biais systémiques (représentation, géographie, capteurs) et concevoir le plan d'atténuation technique pour la future version (V2).

    * Qualifier juridiquement le système au sens de l'AI Act européen et auditer la conformité éthique (RGPD, secret des affaires, autonomie humaine).

* **Travail Réalisé & Choix Techniques** :
    * **Matrice d'impact opérationnel et seuil de décision** (Étape 4.1) :

        * **Modélisation des risques** : Définition des quatre quadrants de décision :

            * Vrai Positif (TP) : Intervention gagnante (préservation du rendement, optimisation des intrants).

            * Faux Négatif (FN) : Perte de rendement (anomalie sous les radars, propagation de maladies/stress hydrique, perte financière).

            * Faux Positif (FP) : Alerte inutile (déplacement vain d'un conseiller, perte de temps et de confiance).

            * Vrai Négatif (TN) : Gestion optimisée (parcelle saine, économie de ressources).

        * **Optimisation par le F1-Score** : le seuil par défaut de 0,50 est écarté au profit d'un ajustement sur la courbe Précision-Rappel.

        * **Métriques du seuil opérationnel recommandé** :

            * Seuil : 0,7377

            * Fiabilité des alertes (Précision) : 100,00 %

            * Anomalies captées (Rappel) : 81,07 %

            * F1-Score maximal : 0,8954

        * **Arbitrage économique** : À 0,7377, le risque de Faux Positif est mathématiquement réduit à zéro, garantissant la rentabilité totale des déplacements. Le système accepte en contrepartie de laisser passer environ 19 % des anomalies les plus légères (Faux Négatifs) pour prémunir les équipes contre le fléau des fausses alertes répétitives.

    * **Analyse de biais et plan de correction** (Étape 4.2) :

        * **Trois risques majeurs de dérive locale ont été audités malgré une Accuracy globale de ~97 %** :

            * **Biais lié aux types de cultures (Représentation)** : Le modèle surreprésente les grandes cultures (blé, maïs) et sous-représente les cultures spécialisées (TypeCulture_Tournesol et TypeCulture_Colza ont une importance proche de 0). Risque d'explosion des fausses alertes en viticulture (NDVI structurellement bas).

            * **Biais lié à la couverture géographique (Effet spatial)** : Concentration historique des capteurs sur les plaines connectées au détriment des zones vallonnées, créant une injustice technique entre les membres de la coopérative.

            * **Biais d'hétérogénéité des capteurs (Biais technique)** : Marques et calibrages différents (ex: une humidité brute de 20 % peut signifier un sol saturé sur une ancienne sonde décalibrée ou une sécheresse critique sur une nouvelle).

        * **Plan d'action pour la V2** :

            * **Z-Score local** : Généralisation de la normalisation relative de toutes les variables physiques (Humidité, Température) par rapport à la moyenne et à la déviation historique de la culture et de la région :
            $$
            Z = \frac{X_{\text{parcelle}} - \mu_{\text{région,culture}}}{\sigma_{\text{région,culture}}}
            $$

            * **Slicing dans MLflow** : Évaluation stratifiée obligatoire par sous-population lors des phases d'audit CI/CD (F1-viticulture, F1-céréales...). Blocage de la mise en production si une seule sous-population affiche un F1-Score < 0,80.

            * **Variations relatives** : Substitution des valeurs brutes des capteurs par leur dérivée temporelle (Delta sur 24h ou 48h) et leur écart à la moyenne mobile pour effacer les artefacts constructeurs.

    * **Qualification AI Act et Gouvernance Éthique** (Étape 4.3) :

        * **Classification AI Act** : Risque Minimal (ou Faible). L'OAD est strictement dédié à l'optimisation agronomique, sans impact sur les droits fondamentaux, infrastructures critiques ou notation sociale. Exempt d'obligations de certification lourdes, le projet s'aligne volontairement sur les codes de conduite (transparence, traçabilité via DVC).

        * **Conformité RGPD et Minimisation** : Le fichier parcelles.csv contenant des données nominatives (Exploitant, Email, Telephone, NumSIRET), une isolation stricte est opérée dès l'ingestion ETL. Ces colonnes sont stockées dans une table cloisonnée et jamais transmises au modèle. L'identité est anonymisée via un jeton unique (ParcelleID).

        * **Secret des affaires et Géolocalisation** : Pour éviter que les variables Region et CodePostal ne fuitent et ne servent à la spéculation sur les cours des récoltes ou à la dévaluation foncière l'accès aux alertes consolidées par code postal est restreint aux techniciens habilités via l'API FastAPI.

        * **Autonomie humaine (Human-in-the-loop)** : Pour contrer le biais d'automatisation (suivre aveuglément l'IA ou ignorer ses propres observations), l'interface Streamlit affiche un indice de confiance associé à une explication claire (XAI). L'agronome conserve le contrôle final et peut contredire la machine via l'endpoint /feedback.

* **Prochaines Étapes (To-Do List)** :
    * Concevoir l'architecture.

    * définir l'orchestration MLOps

    * Exposition API et Interface Utilisateur

---

## Session 5 : Conception de l'Architecture Cible et Cartographie des Composants MLOps

* **Objectif de la session** : 
    * Formaliser l'infrastructure industrielle modulaire, conteneurisée et orientée data-driven nécessaire pour supporter le cycle de vie du modèle Random Forest.

    * Garantir l'étanchéité des données privées (RGPD), la robustesse des prédictions face aux contraintes de connectivité rurale (zones blanches), et l'automatisation complète de la boucle MLOps (Continuous Training, monitoring et boucle de rétroaction).

* **Travail Réalisé & Choix Techniques** :
    * **Principes Directeurs de l'Architecture** (Étape 5.1) :

        * **Séparation des responsabilités (Decoupling)** : Ingestion des données, registre des modèles, API d'inférence et interface utilisateur (UI) sont totalement autonomes afin de supprimer tout point de défaillance unique (Single Point of Failure).

        * **Sécurité et Privacy-by-Design** : Isolation immédiate des données nominatives du fichier parcelles.csv dès l'entrée de la plateforme. Seuls les jetons anonymes (ParcelleID) et les variables agronomiques pures transitent vers les briques de l'IA.

        * **Inférence Hybride & Tolérance aux pannes** : Combinaison d'un traitement par lots nocturne (Batch) pour évaluer l'état général des cultures, et d'un mode synchrone (Request-Response via FastAPI) déclenché à la demande. Intégration d'un système de cache applicatif local pour parer aux interruptions réseau fréquentes en zone rurale blanche.

    * **Cartographie Détaillée des Composants Applicatifs** (Étape 5.2 & 5.3) :

        * **Pipeline d'Ingestion, Sécurisation et Imputation (ETL)** :

            * Assure le nettoyage du signal brut et la conformité réglementaire. Il isole les variables nominatives (Exploitant, Email, Telephone, NumSIRET) de parcelles.csv dans une table chiffrée et génère la clé de substitution anonyme ParcelleID.

            * Traite les valeurs manquantes de type MCAR de observations.csv via un algorithme hybride : imputation par médiane pour les variables météorologiques stables, et par KNN (K-Nearest Neighbors) pour l'humidité locale du sol.

            * Fige et versionne les datasets nettoyés à l'aide de l'outil DVC (Data Version Control) pour garantir la parfaite reproductibilité des futurs entraînements.

        * **Base de Données Centrale (PostgreSQL)** :

            * Pivot de persistance global organisé autour de quatre tables spécifiques :

                * `Table Features` : Centralise les variables nettoyées et les caractéristiques dérivées du Feature Engineering (RatioRendement, Ecart_NDVI_Typique).

                * `Table Validated_Feedbacks` : Stocke les observations terrains qualifiées (Vrais et Faux Positifs) remontées par les experts.

                * `Tables shadow_predictions` & `model_promotions` : Consignent en arrière-plan les performances réelles en mode miroir (Shadow Mode) du modèle candidat et l'historique des changements de version.

        * **Cœur d'Orchestration MLOps (MLflow, Optuna, Triggers)** :

            * Le script autonome `triggers.py` écoute en continu l'état du système. Il lance automatiquement la boucle de réentraînement si l'un des trois déclencheurs métiers s'active : détection d'un Data Drift via un score PSI ≥ 0,20 sur les variables sensibles (Humidite_Sol, Pluviometrie), survenue de la fin d'une campagne de récolte, ou enregistrement de 50 nouveaux feedbacks terrains qualifiés.

            * Le réentraînement exécute une optimisation bayésienne des hyperparamètres du Random Forest (profondeur des arbres, nombre d'estimateurs) via Optuna.

            * Le nouveau modèle est enregistré dans MLflow, puis testé en conditions réelles en mode “shadow” pour vérifier qu’il reste fiable malgré les imputations quotidiennes.

        * **API d'Exposition (FastAPI) & Interface Utilisateur (Streamlit)** :

            * Déploiement complet de la stack via Docker Compose.

            * L'API FastAPI expose deux endpoints majeurs sécurisés par des schémas de validation Pydantic : POST /predict (inférence temps réel à la demande pour forçage manuel lors d'un retour de tournée ou d'un vol de drone) et POST /feedback (collecte des validations métiers).

            * L'application Streamlit extrait les probabilités du Random Forest, applique le seuil de décision opérationnel strict de 0,7377 (garantissant 100 % de précision pour sécuriser la confiance des équipes) et restitue l'interprétabilité locale (XAI) sous forme de graphiques explicites et de cartographies dynamiques pour documenter les règles physiques apprises (poids de l'écart NDVI ou du ratio de rendement).


* **Prochaines Étapes (To-Do List)** :
  * documenter en réalisant la carte de modèle


---

## Session 6 : Documenter
* **Objectif de la session** :
Une carte de modèle est une documentation détaillée pour un modèle d'IA donné. Elle contient les utilisations prévues du modèle par les développeurs et met en évidence les restrictions.

* **Travail Réalisé** (Étape 6.1) :
Réalisation de : Model card - Format : Mitchell et al. (2019)

* **Prochaines Étapes (To-Do List)** :
  * Valider la gouvernance éthique globale avec les experts métiers de la coopérative.
---