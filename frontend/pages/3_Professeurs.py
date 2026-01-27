"""
Professeurs - Planning de surveillance par professeur
"""

import streamlit as st
import pandas as pd
from fpdf import FPDF
from utils.db import get_connection

st.set_page_config(page_title="Professeurs", page_icon="👨‍🏫", layout="wide")
st.title("Planning des Professeurs")
st.markdown("---")


def sanitize_text(text):
    """Remove or replace non-ASCII characters for PDF compatibility."""
    if text is None:
        return ""
    replacements = {
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "É": "E",
        "È": "E",
        "Ê": "E",
        "Ë": "E",
        "à": "a",
        "â": "a",
        "ä": "a",
        "á": "a",
        "À": "A",
        "Â": "A",
        "Ä": "A",
        "Á": "A",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ú": "u",
        "Ù": "U",
        "Û": "U",
        "Ü": "U",
        "Ú": "U",
        "î": "i",
        "ï": "i",
        "í": "i",
        "ì": "i",
        "Î": "I",
        "Ï": "I",
        "Í": "I",
        "Ì": "I",
        "ô": "o",
        "ö": "o",
        "ó": "o",
        "ò": "o",
        "Ô": "O",
        "Ö": "O",
        "Ó": "O",
        "Ò": "O",
        "ç": "c",
        "Ç": "C",
        "ñ": "n",
        "Ñ": "N",
        "œ": "oe",
        "Œ": "OE",
        "æ": "ae",
        "Æ": "AE",
        "\u2019": "'",
        "\u2018": "'",
        "\u201c": '"',
        "\u201d": '"',  # Smart quotes
        """: "'", """: "'",
        '"': '"',
        '"': '"',
        "–": "-",
        "—": "-",  # Dashes
        "…": "...",
        "•": "*",
    }
    result = str(text)
    for old, new in replacements.items():
        result = result.replace(old, new)
    # Remove any remaining non-ASCII characters
    result = result.encode("ascii", "ignore").decode("ascii")
    return result


class PDFProfSchedule(FPDF):
    """Custom PDF for professor schedules."""

    def __init__(self, title):
        super().__init__()
        self.title_text = sanitize_text(title)

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, self.title_text, ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def generate_prof_pdf(prof_name, dept_name, schedule_df):
    """Generate PDF for a professor's schedule."""
    pdf = PDFProfSchedule(f"Planning de Surveillance - {prof_name}")
    pdf.add_page()

    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 8, sanitize_text(f"Departement: {dept_name}"), ln=True)
    pdf.cell(0, 8, f"Nombre de sessions: {len(schedule_df)}", ln=True)
    pdf.ln(5)

    # Table header
    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("Helvetica", "B", 9)
    col_widths = [25, 20, 70, 35, 40]
    headers = ["Date", "Heure", "Module", "Salle", "Formation"]

    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, header, border=1, fill=True, align="C")
    pdf.ln()

    # Table content
    pdf.set_font("Helvetica", size=8)
    for _, row in schedule_df.iterrows():
        pdf.cell(col_widths[0], 7, sanitize_text(row["Date"]), border=1)
        pdf.cell(col_widths[1], 7, sanitize_text(row["Heure"]), border=1, align="C")
        module = sanitize_text(row["Module"])
        module = module[:35] + "..." if len(module) > 35 else module
        pdf.cell(col_widths[2], 7, module, border=1)
        pdf.cell(col_widths[3], 7, sanitize_text(row["Salle"]), border=1)
        formation = sanitize_text(row["Formation"])[:20] if row["Formation"] else "-"
        pdf.cell(col_widths[4], 7, formation, border=1)
        pdf.ln()

    return pdf.output()


try:
    conn = get_connection()
    cur = conn.cursor()

    # === Filters ===
    col1, col2 = st.columns(2)

    # Get departments
    cur.execute("SELECT id, nom FROM departements ORDER BY nom")
    departments = cur.fetchall()

    with col1:
        dept_options = ["Tous"] + [d[1] for d in departments]
        selected_dept = st.selectbox("Departement", dept_options)

    # Get professors
    if selected_dept == "Tous":
        cur.execute("""
            SELECT p.id, p.nom, d.nom as dept,
                   (SELECT COUNT(*) FROM surveillances s WHERE s.prof_id = p.id) as sessions
            FROM professeurs p
            JOIN departements d ON p.dept_id = d.id
            ORDER BY p.nom
        """)
    else:
        dept_id = next(d[0] for d in departments if d[1] == selected_dept)
        cur.execute(
            """
            SELECT p.id, p.nom, d.nom as dept,
                   (SELECT COUNT(*) FROM surveillances s WHERE s.prof_id = p.id) as sessions
            FROM professeurs p
            JOIN departements d ON p.dept_id = d.id
            WHERE p.dept_id = %s
            ORDER BY p.nom
        """,
            (dept_id,),
        )

    professors = cur.fetchall()

    with col2:
        prof_options = ["-- Selectionnez --"] + [
            f"{p[1]} ({p[3]} sessions)" for p in professors
        ]
        selected_prof = st.selectbox("Professeur", prof_options)

    st.markdown("---")

    if selected_prof != "-- Selectionnez --":
        # Extract professor info
        prof_name = selected_prof.split(" (")[0]
        prof_data = next(p for p in professors if p[1] == prof_name)
        prof_id, prof_name, dept_name, sessions = prof_data

        # Get professor's schedule
        cur.execute(
            """
            SELECT
                DATE_FORMAT(ex.date_heure, '%d/%m/%Y') as date,
                DATE_FORMAT(ex.date_heure, '%H:%i') as heure,
                m.nom as module,
                l.nom as salle,
                CONCAT(sp.nom, ' ', f.cycle, ' S', f.semestre) as formation
            FROM surveillances s
            JOIN examens ex ON s.examen_id = ex.id
            JOIN modules m ON ex.module_id = m.id
            JOIN lieu_examens l ON ex.lieu_examen_id = l.id
            JOIN formations f ON m.formation_id = f.id
            JOIN specialites sp ON f.specialite_id = sp.id
            WHERE s.prof_id = %s
            ORDER BY ex.date_heure
        """,
            (prof_id,),
        )

        results = cur.fetchall()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Professeur", prof_name)
        with col2:
            st.metric("Departement", dept_name)
        with col3:
            st.metric("Sessions de surveillance", sessions)

        if results:
            df = pd.DataFrame(
                results, columns=["Date", "Heure", "Module", "Salle", "Formation"]
            )

            st.subheader("Planning de Surveillance")
            st.dataframe(df, use_container_width=True, height=400)

            # Check if professor is respecting max 3/day constraint
            cur.execute(
                """
                SELECT DATE(ex.date_heure) as jour, COUNT(*) as cnt
                FROM surveillances s
                JOIN examens ex ON s.examen_id = ex.id
                WHERE s.prof_id = %s
                GROUP BY DATE(ex.date_heure)
                HAVING COUNT(*) > 3
            """,
                (prof_id,),
            )
            violations = cur.fetchall()

            if violations:
                st.error(f"Attention: Ce professeur depasse 3 surveillances sur {
                         len(violations)} jour(s)")
            else:
                st.success("Contrainte respectee: Maximum 3 surveillances par jour")

            # PDF Export
            col1, col2 = st.columns([1, 4])
            with col1:
                pdf_bytes = generate_prof_pdf(prof_name, dept_name, df)
                st.download_button(
                    label="Telecharger PDF",
                    data=pdf_bytes,
                    file_name=f"Planning_{prof_name.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                )

            # Daily breakdown
            st.markdown("---")
            st.subheader("Repartition par Jour")

            cur.execute(
                """
                SELECT DATE_FORMAT(ex.date_heure, '%d/%m/%Y') as jour, COUNT(*) as sessions
                FROM surveillances s
                JOIN examens ex ON s.examen_id = ex.id
                WHERE s.prof_id = %s
                GROUP BY DATE(ex.date_heure)
                ORDER BY DATE(ex.date_heure)
            """,
                (prof_id,),
            )
            daily = cur.fetchall()
            df_daily = pd.DataFrame(daily, columns=["Jour", "Sessions"])
            st.bar_chart(df_daily.set_index("Jour"))

        else:
            st.info("Aucune surveillance assignee a ce professeur.")

    else:
        # Show summary of all professors
        st.subheader("Resume des Professeurs")

        cur.execute("""
            SELECT
                d.nom as departement,
                COUNT(p.id) as professeurs,
                SUM(COALESCE(surv.cnt, 0)) as total_sessions,
                AVG(COALESCE(surv.cnt, 0)) as moy_sessions
            FROM departements d
            LEFT JOIN professeurs p ON p.dept_id = d.id
            LEFT JOIN (
                SELECT prof_id, COUNT(*) as cnt FROM surveillances GROUP BY prof_id
            ) surv ON surv.prof_id = p.id
            GROUP BY d.id, d.nom
            ORDER BY d.nom
        """)
        results = cur.fetchall()
        df = pd.DataFrame(
            results, columns=["Departement", "Professeurs", "Total Sessions", "Moyenne"]
        )
        df["Moyenne"] = pd.to_numeric(df["Moyenne"], errors="coerce").round(1)
        st.dataframe(df, use_container_width=True)

        # Distribution chart
        st.markdown("---")
        st.subheader("Distribution des Sessions")

        cur.execute("""
            SELECT cnt as sessions, COUNT(*) as professeurs
            FROM (
                SELECT prof_id, COUNT(*) as cnt FROM surveillances GROUP BY prof_id
            ) t
            GROUP BY cnt
            ORDER BY cnt
        """)
        dist = cur.fetchall()
        if dist:
            df_dist = pd.DataFrame(dist, columns=["Sessions", "Professeurs"])
            st.bar_chart(df_dist.set_index("Sessions"))

    conn.close()

except Exception as e:
    st.error(f"Erreur: {e}")
    import traceback

    st.code(traceback.format_exc())
