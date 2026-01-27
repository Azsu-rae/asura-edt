"""
Dashboard - KPIs et statistiques globales
"""

import streamlit as st
import pandas as pd
from utils.db import get_connection, execute_with_timing

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("Dashboard - KPIs Academiques")
st.markdown("---")

try:
    conn = get_connection()
    cur = conn.cursor()

    # === Section 1: KPIs principaux ===
    st.subheader("Indicateurs Cles")

    col1, col2, col3, col4, col5 = st.columns(5)

    cur.execute("SELECT COUNT(*) FROM etudiants")
    with col1:
        st.metric("Etudiants", f"{cur.fetchone()[0]:,}")

    cur.execute("SELECT COUNT(*) FROM formations")
    with col2:
        st.metric("Formations", f"{cur.fetchone()[0]:,}")

    cur.execute("SELECT COUNT(DISTINCT module_id) FROM examens")
    with col3:
        st.metric("Modules Planifies", cur.fetchone()[0])

    cur.execute("SELECT COUNT(*) FROM surveillances")
    with col4:
        st.metric("Surveillances", f"{cur.fetchone()[0]:,}")

    cur.execute("SELECT COUNT(DISTINCT DATE(date_heure)) FROM examens")
    with col5:
        st.metric("Jours d'Examen", cur.fetchone()[0])

    st.markdown("---")

    # === Section 2: Heures professeurs ===
    st.subheader("Charge des Professeurs")

    col1, col2 = st.columns(2)

    with col1:
        cur.execute("""
            SELECT MIN(cnt), AVG(cnt), MAX(cnt)
            FROM (SELECT prof_id, COUNT(*) as cnt FROM surveillances GROUP BY prof_id) t
        """)
        row = cur.fetchone()
        if row and row[0]:
            st.metric("Sessions Min/Moy/Max", f"{row[0]} / {row[1]:.1f} / {row[2]}")

            # Distribution des sessions
            cur.execute("""
                SELECT cnt as sessions, COUNT(*) as professeurs
                FROM (SELECT prof_id, COUNT(*) as cnt FROM surveillances GROUP BY prof_id) t
                GROUP BY cnt ORDER BY cnt
            """)
            df = pd.DataFrame(cur.fetchall(), columns=["Sessions", "Professeurs"])
            st.bar_chart(df.set_index("Sessions"))

    with col2:
        # Professeurs par departement
        cur.execute("""
            SELECT d.nom, COUNT(p.id) as profs,
                   COALESCE(SUM(surv.cnt), 0) as total_sessions
            FROM departements d
            LEFT JOIN professeurs p ON p.dept_id = d.id
            LEFT JOIN (
                SELECT prof_id, COUNT(*) as cnt FROM surveillances GROUP BY prof_id
            ) surv ON surv.prof_id = p.id
            GROUP BY d.id, d.nom
            ORDER BY total_sessions DESC
        """)
        df = pd.DataFrame(cur.fetchall(), columns=["Departement", "Professeurs", "Sessions"])
        st.dataframe(df, use_container_width=True)

    st.markdown("---")

    # === Section 3: Taux d'utilisation des salles ===
    st.subheader("Utilisation des Salles")

    col1, col2 = st.columns(2)

    with col1:
        # Taux d'occupation global
        cur.execute("SELECT COUNT(DISTINCT DATE(date_heure)) FROM examens")
        num_days = cur.fetchone()[0] or 1

        cur.execute("SELECT COUNT(*) FROM lieu_examens")
        total_rooms = cur.fetchone()[0]

        total_slots = num_days * 4 * total_rooms  # 4 slots per day

        cur.execute("SELECT COUNT(*) FROM examens")
        used_slots = cur.fetchone()[0]

        occupancy = (used_slots / total_slots * 100) if total_slots > 0 else 0
        st.metric("Taux d'Occupation Global", f"{occupancy:.1f}%")

        # Par type de salle
        cur.execute("""
            SELECT l.type, COUNT(DISTINCT l.id) as salles,
                   COUNT(e.id) as utilisations
            FROM lieu_examens l
            LEFT JOIN examens e ON e.lieu_examen_id = l.id
            GROUP BY l.type
        """)
        df = pd.DataFrame(cur.fetchall(), columns=["Type", "Nombre", "Utilisations"])
        st.dataframe(df, use_container_width=True)

    with col2:
        # Occupation par jour
        cur.execute("""
            SELECT DATE(date_heure) as jour, COUNT(*) as examens
            FROM examens
            GROUP BY DATE(date_heure)
            ORDER BY jour
        """)
        df = pd.DataFrame(cur.fetchall(), columns=["Jour", "Examens"])
        if not df.empty:
            df["Jour"] = pd.to_datetime(df["Jour"]).dt.strftime("%d/%m")
            st.bar_chart(df.set_index("Jour"))

    st.markdown("---")

    # === Section 4: Statistiques par departement ===
    st.subheader("Statistiques par Departement")

    cur.execute("""
        SELECT
            d.nom as departement,
            COUNT(DISTINCT e.id) as etudiants,
            COUNT(DISTINCT m.id) as modules,
            COUNT(DISTINCT ex.id) as examens,
            COUNT(DISTINCT p.id) as professeurs
        FROM departements d
        LEFT JOIN specialites s ON s.dept_id = d.id
        LEFT JOIN formations f ON f.specialite_id = s.id
        LEFT JOIN etudiants e ON e.formation_id = f.id
        LEFT JOIN modules m ON m.formation_id = f.id
        LEFT JOIN examens ex ON ex.module_id = m.id
        LEFT JOIN professeurs p ON p.dept_id = d.id
        GROUP BY d.id, d.nom
        ORDER BY etudiants DESC
    """)
    df = pd.DataFrame(cur.fetchall(),
                      columns=["Departement", "Etudiants", "Modules", "Examens", "Professeurs"])
    st.dataframe(df, use_container_width=True)

    st.markdown("---")

    # === Section 5: Benchmarks Performance ===
    st.subheader("Benchmarks Performance")

    benchmarks = []

    # Test queries
    queries = [
        ("Count etudiants", "SELECT COUNT(*) FROM etudiants"),
        ("Count formations", "SELECT COUNT(*) FROM formations"),
        ("Examens avec jointures", """
            SELECT e.id, m.nom, l.nom, e.date_heure
            FROM examens e
            JOIN modules m ON e.module_id = m.id
            JOIN lieu_examens l ON e.lieu_examen_id = l.id
            LIMIT 100
        """),
        ("Conflits etudiants", """
            SELECT COUNT(*) FROM (
                SELECT e.id, DATE(ex.date_heure), COUNT(DISTINCT ex.module_id)
                FROM etudiants e
                JOIN modules m ON e.formation_id = m.formation_id
                JOIN examens ex ON m.id = ex.module_id
                GROUP BY e.id, DATE(ex.date_heure)
                HAVING COUNT(DISTINCT ex.module_id) > 1
            ) t
        """),
        ("Sessions par professeur", """
            SELECT p.id, p.nom, COUNT(s.examen_id)
            FROM professeurs p
            LEFT JOIN surveillances s ON s.prof_id = p.id
            GROUP BY p.id, p.nom
        """),
    ]

    for name, query in queries:
        _, _, elapsed = execute_with_timing(query)
        benchmarks.append({"Requete": name, "Temps (ms)": f"{elapsed*1000:.2f}"})

    df = pd.DataFrame(benchmarks)
    st.dataframe(df, use_container_width=True)

    conn.close()

except Exception as e:
    st.error(f"Erreur: {e}")
