"""
Salles - Occupation des amphis et salles
"""

import streamlit as st
import pandas as pd
from utils.db import get_connection

st.set_page_config(page_title="Salles", page_icon="🏫", layout="wide")
st.title("Occupation des Salles et Amphitheatres")
st.markdown("---")

try:
    conn = get_connection()
    cur = conn.cursor()

    # === Global Stats ===
    st.subheader("Statistiques Globales")

    col1, col2, col3, col4 = st.columns(4)

    cur.execute("SELECT COUNT(*) FROM lieu_examens WHERE type = 'Amphi'")
    with col1:
        st.metric("Amphitheatres", cur.fetchone()[0])

    cur.execute("SELECT COUNT(*) FROM lieu_examens WHERE type = 'Salle_TD'")
    with col2:
        st.metric("Salles TD", cur.fetchone()[0])

    cur.execute("SELECT SUM(capacite) FROM lieu_examens")
    with col3:
        st.metric("Capacite Totale", f"{cur.fetchone()[0]:,}")

    cur.execute("SELECT COUNT(DISTINCT lieu_examen_id) FROM examens")
    with col4:
        st.metric("Salles Utilisees", cur.fetchone()[0])

    st.markdown("---")

    # === Filters ===
    col1, col2 = st.columns(2)

    with col1:
        room_type = st.selectbox("Type de Salle", ["Tous", "Amphi", "Salle_TD"])

    with col2:
        cur.execute(
            "SELECT date_heure, DISTINCT DATE(date_heure) FROM examens ORDER BY date_heure"
        )
        dates = [row[0] for row in cur.fetchall()]
        date_options = ["Toutes les dates"] + [d.strftime("%d/%m/%Y") for d in dates]
        selected_date = st.selectbox("Date", date_options)

    st.markdown("---")

    # === Occupation Grid ===
    st.subheader("Grille d'Occupation")

    # Build query based on filters
    where_clauses = []
    params = []

    if room_type != "Tous":
        where_clauses.append("l.type = %s")
        params.append(room_type)

    if selected_date != "Toutes les dates":
        where_clauses.append("DATE(ex.date_heure) = %s")
        # Convert back to date
        day, month, year = selected_date.split("/")
        params.append(f"{year}-{month}-{day}")

    # Get occupation data based on filters
    if room_type == "Tous" and selected_date == "Toutes les dates":
        cur.execute("""
            SELECT
                l.nom as salle,
                l.type,
                l.capacite,
                COUNT(ex.id) as utilisations
            FROM lieu_examens l
            LEFT JOIN examens ex ON ex.lieu_examen_id = l.id
            GROUP BY l.id, l.nom, l.type, l.capacite
            ORDER BY l.type DESC, utilisations DESC, l.nom
        """)
    elif room_type != "Tous" and selected_date == "Toutes les dates":
        cur.execute(
            """
            SELECT
                l.nom as salle,
                l.type,
                l.capacite,
                COUNT(ex.id) as utilisations
            FROM lieu_examens l
            LEFT JOIN examens ex ON ex.lieu_examen_id = l.id
            WHERE l.type = %s
            GROUP BY l.id, l.nom, l.type, l.capacite
            ORDER BY utilisations DESC, l.nom
        """,
            (room_type,),
        )
    elif room_type == "Tous" and selected_date != "Toutes les dates":
        day, month, year = selected_date.split("/")
        date_str = f"{year}-{month}-{day}"
        cur.execute(
            """
            SELECT
                l.nom as salle,
                l.type,
                l.capacite,
                COUNT(ex.id) as utilisations
            FROM lieu_examens l
            LEFT JOIN examens ex ON ex.lieu_examen_id = l.id AND DATE(ex.date_heure) = %s
            GROUP BY l.id, l.nom, l.type, l.capacite
            ORDER BY l.type DESC, utilisations DESC, l.nom
        """,
            (date_str,),
        )
    else:
        day, month, year = selected_date.split("/")
        date_str = f"{year}-{month}-{day}"
        cur.execute(
            """
            SELECT
                l.nom as salle,
                l.type,
                l.capacite,
                COUNT(ex.id) as utilisations
            FROM lieu_examens l
            LEFT JOIN examens ex ON ex.lieu_examen_id = l.id AND DATE(ex.date_heure) = %s
            WHERE l.type = %s
            GROUP BY l.id, l.nom, l.type, l.capacite
            ORDER BY utilisations DESC, l.nom
        """,
            (date_str, room_type),
        )

    results = cur.fetchall()
    df = pd.DataFrame(results, columns=["Salle", "Type", "Capacite", "Utilisations"])

    # Calculate occupancy rate
    # 4 slots per day
    cur.execute("SELECT COUNT(DISTINCT DATE(date_heure)) * 4 FROM examens")
    total_slots = cur.fetchone()[0] or 1

    df["Taux"] = (df["Utilisations"] / total_slots * 100).round(1)

    st.dataframe(df, use_container_width=True, height=400)

    st.markdown("---")

    # === Occupation by Time Slot ===
    st.subheader("Occupation par Creneau")

    cur.execute("""
        SELECT
            DATE_FORMAT(date_heure, '%d/%m/%Y') as date,
            DATE_FORMAT(date_heure, '%H:%i') as heure,
            COUNT(*) as examens,
            SUM(l.capacite) as capacite_utilisee
        FROM examens ex
        JOIN lieu_examens l ON ex.lieu_examen_id = l.id
        GROUP BY DATE(date_heure), TIME(date_heure)
        ORDER BY date_heure
    """)

    results = cur.fetchall()
    df_slots = pd.DataFrame(
        results, columns=["Date", "Heure", "Examens", "Capacite Utilisee"]
    )

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Occupation par jour et creneau**")
        st.dataframe(df_slots, use_container_width=True, height=300)

    with col2:
        # Heatmap-like visualization
        if not df_slots.empty:
            pivot = df_slots.pivot(index="Date", columns="Heure", values="Examens")
            st.write("**Nombre d'examens par creneau**")
            st.dataframe(pivot.fillna(0).astype(int), use_container_width=True)

    st.markdown("---")

    # === Room Details ===
    st.subheader("Detail par Salle")

    cur.execute(
        "SELECT id, nom, type, capacite FROM lieu_examens ORDER BY type DESC, nom"
    )
    rooms = cur.fetchall()

    selected_room = st.selectbox(
        "Selectionner une salle",
        ["-- Selectionnez --"] + [f"{r[1]} ({r[2]}, {r[3]} places)" for r in rooms],
    )

    if selected_room != "-- Selectionnez --":
        room_name = selected_room.split(" (")[0]
        room_id = next(r[0] for r in rooms if r[1] == room_name)

        cur.execute(
            """
            SELECT
                DATE_FORMAT(ex.date_heure, '%d/%m/%Y') as date,
                DATE_FORMAT(ex.date_heure, '%H:%i') as heure,
                m.nom as module,
                (SELECT COUNT(*) FROM etudiants e WHERE e.formation_id = m.formation_id) as inscrits
            FROM examens ex
            JOIN modules m ON ex.module_id = m.id
            WHERE ex.lieu_examen_id = %s
            ORDER BY ex.date_heure
        """,
            (room_id,),
        )

        exams = cur.fetchall()
        if exams:
            df_room = pd.DataFrame(
                exams, columns=["Date", "Heure", "Module", "Inscrits"]
            )
            st.dataframe(df_room, use_container_width=True)
        else:
            st.info("Aucun examen planifie dans cette salle.")

    conn.close()

except Exception as e:
    st.error(f"Erreur: {e}")
    import traceback

    st.code(traceback.format_exc())
