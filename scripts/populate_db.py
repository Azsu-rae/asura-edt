from scripts.helpers import create_connection
from scripts.hardcoded import (
    departments,
    formations,
    modules,
    common_modules,
    department_popularities,
    professors_per_department,
    AMPHI_COUNT,
    AMPHI_CAPACITY,
    SALLE_TD_COUNT,
    SALLE_TD_CAPACITY,
)

from faker import Faker

import random
import mysql


def insert_departments(conn, cur):

    print(f"Inserting {len(departments)} depts...")
    for dept in departments:
        try:
            cur.execute("INSERT INTO departements (nom) VALUES (%s)", (dept,))
        except mysql.connector.Error as e:
            print(f"Error inserting department {dept}: {e}")

    conn.commit()
    print("Done.")


def insert_specialites(conn, cur):
    print("Inserting specialites...")
    for dept_name, levels in formations.items():
        try:
            cur.execute("SELECT id FROM departements WHERE nom = %s", (dept_name,))
            row = cur.fetchone()
            if not row:
                print(f"Department '{dept_name}' not found.")
                continue
            dept_id = row[0]
        except mysql.connector.Error as e:
            print(f"Error retrieving department '{dept_name}': {e}")
            continue

        for cycle, specialite_list in levels.items():
            for specialite_name in specialite_list:
                try:
                    cur.execute(
                        "INSERT INTO specialites (nom, cycle, dept_id) VALUES (%s, %s, %s)",
                        (specialite_name, cycle, dept_id),
                    )
                except mysql.connector.Error as e:
                    print(f"Error inserting specialite '{
                          specialite_name}': {e}")

    conn.commit()
    print("Done.")


def insert_formations(conn, cur):
    print("Inserting formations...")
    try:
        cur.execute("SELECT id, cycle FROM specialites")
        specialites_list = cur.fetchall()
    except mysql.connector.Error as e:
        print(f"Error retrieving specialites: {e}")
        return

    for specialite_id, cycle in specialites_list:
        semesters = 6 if cycle == "Licence" else 3
        for semester in range(1, semesters + 1):
            try:
                cur.execute(
                    "INSERT INTO formations (specialite_id, cycle, semestre) VALUES (%s, %s, %s)",
                    (specialite_id, cycle, semester),
                )
            except mysql.connector.Error as e:
                print(f"Error inserting formation for specialite {
                      specialite_id} S{semester}: {e}")

    conn.commit()
    print("Done.")


def insert_modules(conn, cur):
    print("Inserting modules...")
    try:
        cur.execute("""
            SELECT f.id, s.nom, d.nom
            FROM formations f
            JOIN specialites s ON f.specialite_id = s.id
            JOIN departements d ON s.dept_id = d.id
            """)
        formations_list = cur.fetchall()
    except mysql.connector.Error as e:
        print(f"Error retrieving formations: {e}")
        return

    for form_id, form_nom, dept_nom in formations_list:
        # Create 6 modules per formation (semester)

        # Determine how many common modules (1 or 2)
        num_common = random.randint(1, 2)
        num_specialized = 6 - num_common

        # Select common modules
        selected_common = random.sample(common_modules, num_common)

        # Select specialized modules
        dept_modules = modules.get(dept_nom, [])
        selected_specialized = random.sample(dept_modules, num_specialized)

        # Combine
        module_names = selected_common + selected_specialized
        random.shuffle(module_names)

        for module_name in module_names:
            try:
                cur.execute(
                    "INSERT INTO modules (nom, formation_id) VALUES (%s, %s)",
                    (module_name, form_id),
                )
            except mysql.connector.Error as e:
                print(f"Error inserting module '{module_name}': {e}")
    conn.commit()
    print("Done.")


def insert_students(conn, cur):
    try:
        cur.execute("""
            SELECT f.id, f.cycle, f.semestre, d.nom
            FROM formations f
            JOIN specialites s ON f.specialite_id = s.id
            JOIN departements d ON s.dept_id = d.id
        """)
        formations_list = cur.fetchall()
    except mysql.connector.Error as e:
        print(f"Error retrieving formations: {e}")
        return

    # Constants
    TOTAL_STUDENTS = 13000
    GROUP_SIZE_MIN = 25
    GROUP_SIZE_MAX = 35
    GROUP_SIZE_TARGET = 30

    # Weights for popularity
    pop_weights = {"high": 3.0, "medium": 1.5, "low": 0.8}

    def get_semester_weight(cycle, semestre):
        # Licence
        if cycle == "Licence":
            if semestre in (1, 2):
                return 1.0
            if semestre in (3, 4):
                return 0.6
            if semestre in (5, 6):
                return 0.4
        # Master
        elif cycle == "Master":
            if semestre in (1, 2):
                return 0.2
            if semestre == 3:
                return 0.1

    # First pass: calculate total weight
    formation_weights = {}
    total_weight = 0

    for form_id, cycle, semestre, dept_nom in formations_list:
        pop = department_popularities.get(dept_nom)
        p_weight = pop_weights.get(pop)
        s_weight = get_semester_weight(cycle, semestre)

        final_weight = p_weight * s_weight
        formation_weights[form_id] = final_weight
        total_weight += final_weight

    # Second pass: allocate students with groups
    student_count = 0
    fake = Faker("fr_FR")

    print("Inserting students with groups...")
    for form_id, cycle, semestre, dept_nom in formations_list:
        weight = formation_weights[form_id]
        if total_weight > 0:
            count = int((weight / total_weight) * TOTAL_STUDENTS)
        else:
            count = 0

        # Calculate number of groups for this formation
        if count > 0:
            num_groups = max(1, round(count / GROUP_SIZE_TARGET))
            students_per_group = count // num_groups
            remainder = count % num_groups
        else:
            num_groups = 0
            students_per_group = 0
            remainder = 0

        # Insert students with group assignments
        current_group = 1
        students_in_current_group = 0
        group_target = students_per_group + (1 if current_group <= remainder else 0)

        for _ in range(count):
            student_count += 1
            nom = fake.last_name()
            prenom = fake.first_name()
            try:
                cur.execute(
                    "INSERT INTO etudiants (nom, prenom, formation_id, groupe) VALUES (%s, %s, %s, %s)",
                    (nom, prenom, form_id, current_group),
                )
            except mysql.connector.Error as e:
                print(f"Error inserting student: {e}")

            students_in_current_group += 1

            # Move to next group if current group is full
            if students_in_current_group >= group_target and current_group < num_groups:
                current_group += 1
                students_in_current_group = 0
                group_target = students_per_group + (
                    1 if current_group <= remainder else 0
                )

    print(f"Total students inserted: {student_count}")
    conn.commit()


def insert_inscriptions(conn, cur):
    try:
        # Get all students with their formation, specialty, semester, and department
        cur.execute("""
            SELECT e.id, e.formation_id, f.specialite_id, f.semestre, s.dept_id
            FROM etudiants e
            JOIN formations f ON e.formation_id = f.id
            JOIN specialites s ON f.specialite_id = s.id
        """)
        students = cur.fetchall()

        # Get all modules mapped by formation
        cur.execute("SELECT id, formation_id FROM modules")
        all_modules = cur.fetchall()

        # Get formations by specialty with their semesters
        cur.execute("""
            SELECT f.id, f.specialite_id, f.semestre, s.dept_id
            FROM formations f
            JOIN specialites s ON f.specialite_id = s.id
        """)
        formations_data = cur.fetchall()
    except mysql.connector.Error as e:
        print(f"Error retrieving data for inscriptions: {e}")
        return

    # Organize modules by formation_id
    modules_by_formation = {}
    for mod_id, form_id in all_modules:
        if form_id not in modules_by_formation:
            modules_by_formation[form_id] = []
        modules_by_formation[form_id].append(mod_id)

    # Organize formations by specialty and by department
    formations_by_specialty = {}
    formations_by_dept = {}
    for form_id, spec_id, semester, dept_id in formations_data:
        if spec_id not in formations_by_specialty:
            formations_by_specialty[spec_id] = []
        formations_by_specialty[spec_id].append((form_id, semester))

        if dept_id not in formations_by_dept:
            formations_by_dept[dept_id] = []
        formations_by_dept[dept_id].append((form_id, semester))

    for student_id, formation_id, specialite_id, current_semester, dept_id in students:
        # Enroll in all modules of their formation (6 modules)
        formation_modules = modules_by_formation.get(formation_id, [])
        modules_to_enroll = set(formation_modules)

        # Target: 10-14 modules per student for ~130k total enrollments
        total_modules_target = random.randint(10, 14)

        # Strategy: Add retakes from up to 2 previous semesters of same specialty
        # This keeps chromatic number manageable while achieving enrollment target
        if current_semester > 1:
            previous_formations = [
                f_id for f_id, sem in formations_by_specialty.get(specialite_id, [])
                if current_semester - 2 <= sem < current_semester
            ]
            previous_modules = []
            for f_id in previous_formations:
                previous_modules.extend(modules_by_formation.get(f_id, []))

            attempts = 0
            while len(modules_to_enroll) < total_modules_target and previous_modules and attempts < 50:
                extra_mod = random.choice(previous_modules)
                modules_to_enroll.add(extra_mod)
                attempts += 1

        for mod_id in modules_to_enroll:
            try:
                cur.execute(
                    "INSERT INTO inscriptions (etudiant_id, module_id) VALUES (%s, %s)",
                    (student_id, mod_id),
                )
            except mysql.connector.Error:
                # Ignore duplicate entries
                pass

    conn.commit()


def insert_professors(conn, cur):
    try:
        cur.execute("SELECT id, nom FROM departements")
        departments_list = cur.fetchall()
    except mysql.connector.Error as e:
        print(f"Error retrieving departments: {e}")
        return

    fake = Faker("fr_FR")
    prof_count = 0

    print("Inserting professors...")
    for dept_id, dept_nom in departments_list:
        profs_for_dept = professors_per_department.get(dept_nom, 50)
        for _ in range(profs_for_dept):
            prof_count += 1
            nom = fake.last_name()
            try:
                cur.execute(
                    "INSERT INTO professeurs (nom, dept_id) VALUES (%s, %s)",
                    (nom, dept_id),
                )
            except mysql.connector.Error as e:
                print(f"Error inserting professor: {e}")

    print(f"Total professors inserted: {prof_count}")
    conn.commit()


def insert_exam_locations(conn, cur):

    total_capacity = 0
    locations = []

    for i in range(AMPHI_COUNT):
        locations.append((f"Amphi {i + 1}", AMPHI_CAPACITY, "Amphi"))
        total_capacity += AMPHI_CAPACITY

    for i in range(SALLE_TD_COUNT):
        locations.append((f"Salle {i + 1}", SALLE_TD_CAPACITY, "Salle_TD"))
        total_capacity += SALLE_TD_CAPACITY

    print(f"Inserting {len(locations)
                       } exam locations (Total Capacity: {total_capacity})...")

    for nom, cap, type_loc in locations:
        try:
            cur.execute(
                "INSERT INTO lieu_examens (nom, capacite, type) VALUES (%s, %s, %s)",
                (nom, cap, type_loc),
            )
        except mysql.connector.Error as e:
            print(f"Error inserting location {nom}: {e}")

    conn.commit()


if __name__ == "__main__":

    conn = create_connection()
    cur = conn.cursor()

    insert_departments(conn, cur)
    insert_specialites(conn, cur)
    insert_formations(conn, cur)
    insert_students(conn, cur)
    insert_modules(conn, cur)
    insert_professors(conn, cur)
    insert_exam_locations(conn, cur)
    insert_inscriptions(conn, cur)

    conn.close()
