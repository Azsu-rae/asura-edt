"""
Optimisation - Generation automatique des plannings
"""

import streamlit as st
import pandas as pd
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.db import get_connection

st.set_page_config(page_title="Optimisation", page_icon="⚡", layout="wide")
st.title("Optimisation des Emplois du Temps")
st.markdown("---")

try:
    conn = get_connection()
    cur = conn.cursor()

    # === Current Status ===
    st.subheader("Etat Actuel")

    col1, col2, col3, col4 = st.columns(4)

    cur.execute("SELECT COUNT(*) FROM modules")
    total_modules = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT module_id) FROM examens")
    scheduled_modules = cur.fetchone()[0]

    with col1:
        st.metric("Modules Total", total_modules)

    with col2:
        st.metric("Modules Planifies", scheduled_modules)

    with col3:
        pct = (scheduled_modules / total_modules * 100) if total_modules > 0 else 0
        st.metric("Couverture", f"{pct:.0f}%")

    cur.execute("SELECT COUNT(*) FROM examens")
    with col4:
        st.metric("Examens", cur.fetchone()[0])

    st.markdown("---")

    # === Constraints Summary ===
    st.subheader("Contraintes d'Optimisation")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Contraintes Etudiants:**
        - Maximum 1 examen par jour par etudiant

        **Contraintes Professeurs:**
        - Maximum 3 surveillances par jour
        - Priorite aux examens du departement
        - Repartition equitable des surveillances
        """)

    with col2:
        st.markdown("""
        **Contraintes Salles:**
        - Respect de la capacite reelle
        - 4 creneaux par jour

        **Periode d'examen:**
        - 3 semaines (18 jours sans vendredis)
        - Creneaux: 08h00, 10h30, 13h00, 15h30
        """)

    st.markdown("---")

    # === Run Optimization ===
    st.subheader("Lancer l'Optimisation")

    st.warning("""
    **Attention:** Lancer l'optimisation va supprimer le planning actuel et en generer un nouveau.
    Cette operation prend environ 1 seconde.
    """)

    if st.button("Lancer l'Optimisation", type="primary"):
        with st.spinner("Optimisation en cours..."):
            try:
                # Import and run optimizer
                from scripts.optimize import optimize_schedule

                start_time = time.time()
                result = optimize_schedule()
                elapsed = time.time() - start_time

                st.success(f"Optimisation terminee en {elapsed:.2f} secondes!")

                # Display results
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Examens Crees", result.get("num_exams", 0))

                with col2:
                    st.metric("Jours Utilises", result.get("num_days", 0))

                with col3:
                    st.metric("Surveillances", result.get("num_surveillances", 0))

                # Check for violations
                violations = result.get("student_violations", 0)
                if violations == 0:
                    st.success("Aucun conflit detecte!")
                else:
                    st.warning(f"{violations} conflits etudiants detectes")

            except Exception as e:
                st.error(f"Erreur lors de l'optimisation: {e}")
                import traceback
                st.code(traceback.format_exc())

    st.markdown("---")

    # === Verification ===
    st.subheader("Verification des Contraintes")

    if st.button("Verifier les Contraintes"):
        with st.spinner("Verification en cours..."):
            results = []

            # Check student constraint
            cur.execute("""
                SELECT COUNT(*) FROM (
                    SELECT i.etudiant_id, DATE(ex.date_heure), COUNT(DISTINCT ex.module_id) as cnt
                    FROM inscriptions i
                    JOIN examens ex ON i.module_id = ex.module_id
                    GROUP BY i.etudiant_id, DATE(ex.date_heure)
                    HAVING cnt > 1
                ) t
            """)
            v = cur.fetchone()[0]
            results.append({
                "Contrainte": "Max 1 examen/jour par etudiant",
                "Statut": "OK" if v == 0 else "ECHEC",
                "Violations": v
            })

            # Check professor constraint
            cur.execute("""
                SELECT COUNT(*) FROM (
                    SELECT s.prof_id, DATE(ex.date_heure), COUNT(*) as cnt
                    FROM surveillances s
                    JOIN examens ex ON s.examen_id = ex.id
                    GROUP BY s.prof_id, DATE(ex.date_heure)
                    HAVING cnt > 3
                ) t
            """)
            v = cur.fetchone()[0]
            results.append({
                "Contrainte": "Max 3 surveillances/jour par professeur",
                "Statut": "OK" if v == 0 else "ECHEC",
                "Violations": v
            })

            # Check room capacity
            cur.execute("""
                SELECT COUNT(*) FROM (
                    SELECT m.id,
                           (SELECT COUNT(*) FROM inscriptions i WHERE i.module_id = m.id) as enroll,
                           SUM(l.capacite) as cap
                    FROM modules m
                    JOIN examens ex ON ex.module_id = m.id
                    JOIN lieu_examens l ON ex.lieu_examen_id = l.id
                    GROUP BY m.id
                    HAVING enroll > cap
                ) t
            """)
            v = cur.fetchone()[0]
            results.append({
                "Contrainte": "Capacite des salles",
                "Statut": "OK" if v == 0 else "ECHEC",
                "Violations": v
            })

            # Check no Fridays
            cur.execute("""
                SELECT COUNT(*) FROM examens
                WHERE DAYOFWEEK(date_heure) = 6
            """)
            v = cur.fetchone()[0]
            results.append({
                "Contrainte": "Pas d'examens le vendredi",
                "Statut": "OK" if v == 0 else "ECHEC",
                "Violations": v
            })

            # Check equal sessions
            cur.execute("""
                SELECT MAX(cnt) - MIN(cnt)
                FROM (SELECT prof_id, COUNT(*) as cnt FROM surveillances GROUP BY prof_id) t
            """)
            diff = cur.fetchone()[0] or 0
            results.append({
                "Contrainte": "Repartition equitable (ecart max 1)",
                "Statut": "OK" if diff <= 1 else "ECHEC",
                "Violations": diff
            })

            # Department priority
            cur.execute("""
                SELECT
                    ROUND(SUM(CASE WHEN p.dept_id = d.id THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
                FROM surveillances s
                JOIN examens ex ON s.examen_id = ex.id
                JOIN modules m ON ex.module_id = m.id
                JOIN formations f ON m.formation_id = f.id
                JOIN specialites sp ON f.specialite_id = sp.id
                JOIN departements d ON sp.dept_id = d.id
                JOIN professeurs p ON s.prof_id = p.id
            """)
            pct = cur.fetchone()[0] or 0
            results.append({
                "Contrainte": "Priorite departement",
                "Statut": f"{pct}%",
                "Violations": "-"
            })

            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True)

            # Overall status
            all_ok = all(r["Statut"] == "OK" or r["Statut"].endswith("%") for r in results)
            if all_ok:
                st.success("Toutes les contraintes sont respectees!")
            else:
                st.error("Certaines contraintes ne sont pas respectees.")

    st.markdown("---")

    # === Performance Metrics ===
    st.subheader("Metriques de Performance")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Repartition des examens par jour**")
        cur.execute("""
            SELECT DATE_FORMAT(date_heure, '%d/%m') as jour, COUNT(*) as examens
            FROM examens
            GROUP BY DATE(date_heure)
            ORDER BY DATE(date_heure)
        """)
        results = cur.fetchall()
        if results:
            df = pd.DataFrame(results, columns=["Jour", "Examens"])
            st.bar_chart(df.set_index("Jour"))

    with col2:
        st.write("**Repartition par creneau horaire**")
        cur.execute("""
            SELECT TIME_FORMAT(TIME(date_heure), '%H:%i') as heure, COUNT(*) as examens
            FROM examens
            GROUP BY TIME(date_heure)
            ORDER BY TIME(date_heure)
        """)
        results = cur.fetchall()
        if results:
            df = pd.DataFrame(results, columns=["Heure", "Examens"])
            st.bar_chart(df.set_index("Heure"))

    conn.close()

except Exception as e:
    st.error(f"Erreur: {e}")
    import traceback
    st.code(traceback.format_exc())
