# 4.3 Qualification AI Act et réflexion éthique

## 1. Qualification réglementaire au sens de l'AI Act Européen

L'Union Européenne structure la gouvernance des systèmes d'intelligence artificielle selon une approche proportionnelle aux risques (Risque Inacceptable, Élevé, Limité, Minimal).

- **Classification retenue : Risque Minimal (ou Faible).**

- **Justification réglementaire** : L'outil d'aide à la décision (OAD) développé ici est strictement dédié à l'optimisation agronomique (détection précoce des stress hydriques, des maladies et des pannes de capteurs IoT). Il n'intervient pas dans la gestion des infrastructures critiques vitales, ne réalise aucune notation sociale, aucun profilage d'individus ni de surveillance biométrique. N'ayant aucun impact direct sur les droits fondamentaux des citoyens, il entre dans la catégorie des applications agtech à risque minimal.

- **Obligations légales** : Le système est exempt d'obligations de certification lourdes ou d'audits pré-mise sur le marché. L'AI Act encourage toutefois l'adoption volontaire de Codes de conduite alignés sur l'état de l'art : transparence des algorithmes, robustesse technique et traçabilité des données d'entraînement (assurée dans notre architecture par l'outil DVC).

## 2. Réflexion éthique et souveraineté des données agricoles

Même si le risque réglementaire au sens de l'AI Act est qualifié de minimal, le croisement des relevés de capteurs terrain avec les données structurelles de la coopérative impose un cadre déontologique et technique rigoureux.

### A. Protection des données personnelles et professionnelles (RGPD)

Le fichier source parcelles.csv manipule des données directement nominatives et identifiables liées aux agriculteurs : Exploitant, Email, Telephone, ainsi que des données professionnelles sensibles comme le NumSIRET.

- **Le risque** : L'exposition de ces données dans le pipeline de modélisation enfreindrait le principe de protection de la vie privée et rendrait le système vulnérable à l'ingénierie sociale.

- **L'action corrective** : Application stricte du principe de minimisation des données. Dès l'étape d'ingestion par le pipeline d'ETL, une isolation complète est opérée. Les colonnes Exploitant, Email, Telephone et NumSIRET sont stockées dans une table sécurisée et cloisonnée. Elles ne sont jamais transmises au modèle. L'identité est substituée par le ParcelleID (faisant office de jeton anonyme). Le Random Forest n'analyse que des caractéristiques agronomiques pures (Surface_ha, TypeCulture, TypeSol, Irrigation), le rendant structurellement aveugle à l'identité des personnes.

### B. Sensibilité de la géolocalisation et secret des affaires

Le dataset intègre les variables géographiques Region et CodePostal. Le croisement de ces localisations avec le TypeCulture et les prédictions d'anomalies (maladies, baisses de rendement) engendre un risque économique majeur.

- **Le risque éthique** : Si ces données de santé des cultures sectorisées par code postal fuitaient, des courtiers en matières premières ou des acteurs tiers pourraient cartographier à l'avance l'état des récoltes d'une région pour spéculer sur les cours ou dévaluer artificiellement la valeur foncière des terres jugées "à risque" par l'IA.

- **L'action corrective** : Conformément au Code de conduite européen sur le partage des données agricoles, la coopérative conserve la souveraineté exclusive de la donnée. Les flux au sein de l'architecture sont sécurisés par un chiffrement robuste (AES-256 au repos, TLS en transit). L'accès aux alertes consolidées par CodePostal est filtré et restreint aux seuls techniciens habilités via des schémas d'authentification stricts appliqués sur les endpoints de notre API FastAPI.

### C. Préservation de l'autonomie et contrôle humain (Human-in-the-loop)

L'intégration de variables opérationnelles clés comme l'Irrigation ou la DateMiseEnCulture dans un modèle prédictif expose l'utilisateur à des biais comportementaux.

- **Le risque éthique** : Le biais d'automatisation pousserait l'agriculteur à suivre aveuglément une fausse alerte du modèle (entraînant un traitement chimique ou un sur-arrosage inutile), ou à l'inverse, à ignorer ses propres observations visuelles si l'IA affiche à tort un statut normal.

- **L'action corrective** : L'interface Streamlit consacre le principe de l'humain dans la boucle (Human-in-the-loop). Le modèle ne livre pas de verdict brut, mais restitue une probabilité (indice de confiance) adossée à une explication en langage clair issue des fonctions d'importance locale (XAI). De plus, l'architecture est conçue pour être contredite : via l'endpoint /feedback, c'est l'expertise de terrain de l'agronome qui valide ou invalide la décision de la machine. L'IA demeure un outil d'augmentation du savoir-faire humain, jamais de substitution.