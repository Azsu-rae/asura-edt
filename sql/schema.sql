
SELECT 1;

CREATE TABLE departements (
    nom VARCHAR(255) NOT NULL,

    id INT AUTO_INCREMENT,
    PRIMARY KEY (id)
);

CREATE TABLE specialites (
    nom VARCHAR(255) NOT NULL,

    id INT AUTO_INCREMENT,
    cycle ENUM('Licence', 'Master') NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (id, cycle),

    dept_id INT,
    FOREIGN KEY (dept_id) REFERENCES departements(id)
);

CREATE TABLE formations (

    id INT AUTO_INCREMENT,
    PRIMARY KEY (id),

    specialite_id INT NOT NULL,
    cycle ENUM('Licence', 'Master') NOT NULL,
    FOREIGN KEY (specialite_id, cycle)
        REFERENCES specialites(id, cycle),

    semestre TINYINT UNSIGNED NOT NULL,
    CHECK (
        (cycle = 'Licence' AND semestre BETWEEN 1 AND 6)
        OR
        (cycle = 'Master'  AND semestre BETWEEN 1 AND 3)
    )
);

CREATE TABLE etudiants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(255) NOT NULL,
    prenom VARCHAR(255) NOT NULL,
    formation_id INT NOT NULL,
    groupe TINYINT UNSIGNED NOT NULL,
    FOREIGN KEY (formation_id) REFERENCES formations(id)
);

CREATE TABLE modules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(255) NOT NULL,
    formation_id INT,
    FOREIGN KEY (formation_id) REFERENCES formations(id)
);

CREATE TABLE lieu_examens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(255) NOT NULL,
    capacite INT NOT NULL,
    type ENUM('Salle_TD', 'Amphi') NOT NULL
);

CREATE TABLE professeurs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(255) NOT NULL,
    dept_id INT,
    FOREIGN KEY (dept_id) REFERENCES departements(id)
);

CREATE TABLE examens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    module_id INT,
    lieu_examen_id INT,
    date_heure DATETIME NOT NULL,
    formation_id INT,     -- Which formation's students go to this room
    groupes VARCHAR(50),  -- Comma-separated group numbers (e.g., "1,2" or "3")
    FOREIGN KEY (module_id) REFERENCES modules(id),
    FOREIGN KEY (lieu_examen_id) REFERENCES lieu_examens(id),
    FOREIGN KEY (formation_id) REFERENCES formations(id)
);

CREATE TABLE surveillances (
    examen_id INT,
    prof_id INT,
    PRIMARY KEY (examen_id, prof_id),
    FOREIGN KEY (examen_id) REFERENCES examens(id),
    FOREIGN KEY (prof_id) REFERENCES professeurs(id)
);
