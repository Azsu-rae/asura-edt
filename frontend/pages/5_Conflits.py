"""
Conflits - Detection et analyse des conflits
"""

import streamlit as st
import pandas as pd
from utils.db import get_connection

st.set_page_config(page_title="Conflits", page_icon="⚠️", layout="wide")
st.title("Detection et Analyse des Conflits")
st.markdown("---")

try:
    conn = get_connection()
    cur = conn.cursor()

    # === Conflict Summary ===
    st.subheader("Resume des Conflits")

    col1, col2, col3 = st.columns(3)

    # Student conflicts (>1 exam per day)
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT i.etudiant_id, DATE(ex.date_heure), COUNT(DISTINCT ex.module_id) as cnt
            FROM inscriptions i
            JOIN examens ex ON i.module_id = ex.module_id
            GROUP BY i.etudiant_id, DATE(ex.date_heure)
            HAVING cnt > 1
        ) t
    """)
    student_conflicts = cur.fetchone()[0]

    with col1:
        if student_conflicts == 0:
            st.success("Conflits Etudiants: 0")
        else:
            st.error(f"Conflits Etudiants: {student_conflicts}")

    # Professor conflicts (>3 exams per day)
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT s.prof_id, DATE(ex.date_heure), COUNT(*) as cnt
            FROM surveillances s
            JOIN examens ex ON s.examen_id = ex.id
            GROUP BY s.prof_id, DATE(ex.date_heure)
            HAVING cnt > 3
        ) t
    """)
    prof_conflicts = cur.fetchone()[0]

    with col2:
        if prof_conflicts == 0:
            st.success("Conflits Professeurs: 0")
        else:
            st.error(f"Conflits Professeurs: {prof_conflicts}")

    # Room capacity conflicts
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT m.id,
                   (SELECT COUNT(*) FROM inscriptions i WHERE i.module_id = m.id) as enrollment,
                   SUM(l.capacite) as capacity
            FROM modules m
            JOIN examens ex ON ex.module_id = m.id
            JOIN lieu_examens l ON ex.lieu_examen_id = l.id
            GROUP BY m.id
            HAVING enrollment > capacity
        ) t
    """)
    room_conflicts = cur.fetchone()[0]

    with col3:
        if room_conflicts == 0:
            st.success("Conflits Capacite: 0")
        else:
            st.error(f"Conflits Capacite: {room_conflicts}")

    st.markdown("---")

    # === Detailed Student Conflicts ===
    st.subheader("Conflits Etudiants (>1 examen/jour)")

    if student_conflicts > 0:
        cur.execute("""
            SELECT
                e.id as etudiant_id,
                CONCAT(e.prenom, ' ', e.nom) as etudiant,
                d.nom as departement,
                DATE_FORMAT(ex.date_heure, '%d/%m/%Y') as date,
                COUNT(DISTINCT ex.module_id) as nb_examens,
                GROUP_CONCAT(DISTINCT m.nom SEPARATOR ', ') as modules
            FROM etudiants e
            JOIN formations f ON e.formation_id = f.id
            JOIN specialites s ON f.specialite_id = s.id
            JOIN departements d ON s.dept_id = d.id
            JOIN inscriptions i ON i.etudiant_id = e.id
            JOIN examens ex ON i.module_id = ex.module_id
            JOIN modules m ON ex.module_id = m.id
            GROUP BY e.id, e.prenom, e.nom, d.nom, DATE(ex.date_heure)
            HAVING COUNT(DISTINCT ex.module_id) > 1
            ORDER BY nb_examens DESC, date
            LIMIT 100
        """)
        results = cur.fetchall()
        df = pd.DataFrame(results,
                          columns=["ID", "Etudiant", "Departement", "Date", "Nb Examens", "Modules"])
        st.dataframe(df, use_container_width=True)
    else:
        st.success("Aucun conflit etudiant detecte. Tous les etudiants ont maximum 1 examen par jour.")

    st.markdown("---")

    # === Conflicts by Department ===
    st.subheader("Taux de Conflits par Departement")

    cur.execute("""
        SELECT
            d.nom as departement,
            COUNT(DISTINCT e.id) as total_etudiants,
            COUNT(DISTINCT CASE WHEN conflict.cnt > 1 THEN conflict.etudiant_id END) as etudiants_en_conflit,
            ROUND(COUNT(DISTINCT CASE WHEN conflict.cnt > 1 THEN conflict.etudiant_id END) * 100.0 /
                  NULLIF(COUNT(DISTINCT e.id), 0), 2) as taux_conflit
        FROM departements d
        JOIN specialites s ON s.dept_id = d.id
        JOIN formations f ON f.specialite_id = s.id
        JOIN etudiants e ON e.formation_id = f.id
        LEFT JOIN (
            SELECT i.etudiant_id, DATE(ex.date_heure) as jour, COUNT(DISTINCT ex.module_id) as cnt
            FROM inscriptions i
            JOIN examens ex ON i.module_id = ex.module_id
            GROUP BY i.etudiant_id, DATE(ex.date_heure)
        ) conflict ON conflict.etudiant_id = e.id
        GROUP BY d.id, d.nom
        ORDER BY taux_conflit DESC
    """)

    results = cur.fetchall()
    df = pd.DataFrame(results,
                      columns=["Departement", "Total Etudiants", "En Conflit", "Taux (%)"])
    st.dataframe(df, use_container_width=True)

    # Bar chart
    if not df.empty:
        st.bar_chart(df.set_index("Departement")["Taux (%)"])

    st.markdown("---")

    # === Conflicts by Formation ===
    st.subheader("Conflits par Formation")

    cur.execute("""
        SELECT
            d.nom as departement,
            CONCAT(sp.nom, ' ', f.cycle, ' S', f.semestre) as formation,
            COUNT(DISTINCT e.id) as total_etudiants,
            COUNT(DISTINCT CASE WHEN conflict.cnt > 1 THEN conflict.etudiant_id END) as en_conflit
        FROM departements d
        JOIN specialites sp ON sp.dept_id = d.id
        JOIN formations f ON f.specialite_id = sp.id
        JOIN etudiants e ON e.formation_id = f.id
        LEFT JOIN (
            SELECT i.etudiant_id, DATE(ex.date_heure) as jour, COUNT(DISTINCT ex.module_id) as cnt
            FROM inscriptions i
            JOIN examens ex ON i.module_id = ex.module_id
            GROUP BY i.etudiant_id, DATE(ex.date_heure)
        ) conflict ON conflict.etudiant_id = e.id
        GROUP BY d.id, d.nom, f.id, sp.nom, f.cycle, f.semestre
        HAVING en_conflit > 0
        ORDER BY en_conflit DESC
        LIMIT 50
    """)

    results = cur.fetchall()
    if results:
        df = pd.DataFrame(results,
                          columns=["Departement", "Formation", "Total", "En Conflit"])
        st.dataframe(df, use_container_width=True)
    else:
        st.success("Aucune formation avec des etudiants en conflit.")

    st.markdown("---")

    # === Professor Workload Analysis ===
    st.subheader("Analyse de la Charge Professeurs")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Professeurs avec plus de 3 surveillances/jour**")
        cur.execute("""
            SELECT
                p.nom as professeur,
                d.nom as departement,
                DATE_FORMAT(ex.date_heure, '%d/%m/%Y') as date,
                COUNT(*) as surveillances
            FROM professeurs p
            JOIN departements d ON p.dept_id = d.id
            JOIN surveillances s ON s.prof_id = p.id
            JOIN examens ex ON s.examen_id = ex.id
            GROUP BY p.id, p.nom, d.nom, DATE(ex.date_heure)
            HAVING COUNT(*) > 3
            ORDER BY surveillances DESC
        """)
        results = cur.fetchall()
        if results:
            df = pd.DataFrame(results, columns=["Professeur", "Departement", "Date", "Surveillances"])
            st.dataframe(df, use_container_width=True)
        else:
            st.success("Aucun professeur ne depasse 3 surveillances par jour.")

    with col2:
        st.write("**Distribution des sessions**")
        cur.execute("""
            SELECT
                CASE
                    WHEN cnt <= 5 THEN '1-5'
                    WHEN cnt <= 8 THEN '6-8'
                    WHEN cnt <= 10 THEN '9-10'
                    ELSE '11+'
                END as tranche,
                COUNT(*) as professeurs
            FROM (
                SELECT prof_id, COUNT(*) as cnt FROM surveillances GROUP BY prof_id
            ) t
            GROUP BY tranche
            ORDER BY MIN(cnt)
        """)
        results = cur.fetchall()
        df = pd.DataFrame(results, columns=["Sessions", "Professeurs"])
        st.dataframe(df, use_container_width=True)

    st.markdown("---")

    # === Validation Status ===
    st.subheader("Statut de Validation")

    all_ok = student_conflicts == 0 and prof_conflicts == 0 and room_conflicts == 0

    if all_ok:
        st.success("""
        ### Emploi du temps VALIDE

        Toutes les contraintes sont respectees:
        - Aucun etudiant n'a plus d'1 examen par jour
        - Aucun professeur n'a plus de 3 surveillances par jour
        - Toutes les salles ont une capacite suffisante
        """)

        if st.button("Valider l'emploi du temps", type="primary"):
            st.balloons()
            st.success("Emploi du temps valide avec succes!")
    else:
        st.error("""
        ### Emploi du temps NON VALIDE

        Des conflits ont ete detectes. Veuillez relancer l'optimisation.
        """)

    conn.close()

except Exception as e:
    st.error(f"Erreur: {e}")
    import traceback
    st.code(traceback.format_exc())
