departments = [
    "Physique",
    "Chimie",
    "Mathématique",
    "Informatique",
    "Agronomie",
    "Biologie",
    "Géologie",
]

department_popularities = {
    "Physique": "low",
    "Agronomie": "low",
    "Mathématique": "low",
    "Chimie": "medium",
    "Géologie": "medium",
    "Biologie": "high",
    "Informatique": "high",
}

formations = {
    "Physique": {
        "Licence": [
            "Physique Fondamentale",
            "Physique des Matériaux",
            "Physique Énergétique",
        ],
        "Master": [
            "Physique des Matériaux Avancés",
            "Physique des Rayonnements",
            "Physique Appliquée",
        ],
    },
    "Chimie": {
        "Licence": [
            "Chimie Générale",
            "Chimie des Matériaux",
            "Chimie Analytique",
        ],
        "Master": [
            "Chimie Organique Avancée",
            "Chimie Analytique Avancée",
            "Chimie des Matériaux Avancés",
        ],
    },
    "Mathématique": {
        "Licence": [
            "Mathématiques Fondamentales",
            "Mathématiques Appliquées",
        ],
        "Master": [
            "Mathématiques Appliquées",
            "Analyse et Modélisation",
            "Statistiques et Probabilités",
        ],
    },
    "Informatique": {
        "Licence": [
            "Informatique Générale",
            "Systèmes Informatiques",
            "Développement Logiciel",
        ],
        "Master": [
            "Génie Logiciel",
            "Intelligence Artificielle",
            "Systèmes d’Information",
            "Cybersécurité",
        ],
    },
    "Agronomie": {
        "Licence": [
            "Production Végétale",
            "Production Animale",
            "Protection des Végétaux",
        ],
        "Master": [
            "Agronomie Durable",
            "Production Végétale Avancée",
            "Gestion des Ressources Agricoles",
        ],
    },
    "Biologie": {
        "Licence": [
            "Biologie Générale",
            "Biologie Cellulaire",
            "Biologie des Organismes",
        ],
        "Master": [
            "Biologie Moléculaire",
            "Physiologie Animale",
            "Biochimie Appliquée",
        ],
    },
    "Géologie": {
        "Licence": [
            "Géologie Générale",
            "Géosciences",
            "Géologie de l’Environnement",
        ],
        "Master": [
            "Géologie Appliquée",
            "Hydrogéologie",
            "Géologie des Ressources Minérales",
        ],
    },
}

modules = {
    "Informatique": [
        "Programmation Avancée",
        "Algorithmes et Structures de Données",
        "Bases de Données",
        "Réseaux Informatiques",
        "Systèmes d'Exploitation",
        "Génie Logiciel",
        "Intelligence Artificielle",
        "Machine Learning",
        "Deep Learning",
        "Sécurité Informatique",
        "Cloud Computing",
        "DevOps",
        "Architecture Logicielle",
        "Conception Orientée Objet",
        "Développement Web",
        "Développement Mobile",
        "Big Data",
        "IoT",
        "Compilation",
        "Théorie des Langages",
    ],
    "Mathématique": [
        "Algèbre Linéaire",
        "Analyse Réelle",
        "Analyse Complexe",
        "Probabilités",
        "Statistiques",
        "Optimisation",
        "Équations Différentielles",
        "Topologie",
        "Théorie des Graphes",
        "Analyse Numérique",
        "Calcul Scientifique",
        "Mathématiques Financières",
        "Cryptographie",
        "Théorie des Nombres",
    ],
    "Physique": [
        "Mécanique Classique",
        "Mécanique Quantique",
        "Électromagnétisme",
        "Thermodynamique",
        "Optique",
        "Physique Statistique",
        "Relativité",
        "Physique du Solide",
        "Physique Nucléaire",
        "Astrophysique",
        "Acoustique",
    ],
    "Chimie": [
        "Chimie Générale",
        "Chimie Organique",
        "Chimie Inorganique",
        "Thermochimie",
        "Électrochimie",
        "Spectroscopie",
        "Chimie Analytique",
        "Chimie des Polymères",
        "Chimie Industrielle",
        "Catalyse",
        "Chimie Verte",
    ],
    "Biologie": [
        "Biologie Cellulaire",
        "Biologie Moléculaire",
        "Génétique",
        "Microbiologie",
        "Biochimie",
        "Immunologie",
        "Écologie",
        "Physiologie",
        "Évolution",
        "Biotechnologie",
        "Bioinformatique",
        "Neurosciences",
    ],
    "Géologie": [
        "Géologie Générale",
        "Pétrologie",
        "Stratigraphie",
        "Tectonique",
        "Hydrogéologie",
        "Géophysique",
        "Paléontologie",
        "Géomorphologie",
        "Cartographie",
        "SIG",
        "Géologie Marine",
        "Ressources Minérales",
    ],
    "Agronomie": [
        "Agronomie Générale",
        "Science du Sol",
        "Production Végétale",
        "Production Animale",
        "Protection des Cultures",
        "Irrigation et Drainage",
        "Agroécologie",
        "Phytopathologie",
        "Entomologie Agricole",
        "Amélioration des Plantes",
        "Machinisme Agricole",
        "Gestion des Exploitations Agricoles",
    ],
}

common_modules = [
    "Méthodologie du Travail Universitaire",
    "Statistiques Appliquées",
    "Informatique de Base",
    "Anglais Scientifique",
    "Communication Scientifique",
    "Éthique et Déontologie Universitaire",
    "Entrepreneuriat",
    "Méthodologie de la Recherche",
]

# Professors per department (varies by department size/popularity)
professors_per_department = {
    "Physique": 68,
    "Chimie": 77,
    "Mathématique": 62,
    "Informatique": 105,
    "Agronomie": 66,
    "Biologie": 96,
    "Géologie": 66,
}

# Exam location constants
AMPHI_COUNT = 55  # Enough for large groups (>20 students) per slot with buffer
AMPHI_CAPACITY = 60

SALLE_TD_COUNT = 110
SALLE_TD_CAPACITY = 20
