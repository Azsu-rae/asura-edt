"""
Emplois du Temps - Consultation et export PDF par formation
"""

import streamlit as st
import pandas as pd
from io import BytesIO
from fpdf import FPDF
from utils.db import get_connection

st.set_page_config(page_title="Emplois du Temps", page_icon="📅", layout="wide")
st.title("Emplois du Temps par Formation")
st.markdown("---")


def sanitize_text(text):
    """Remove or replace non-ASCII characters for PDF compatibility."""
    if text is None:
        return ""
    replacements = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e', 'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
        'à': 'a', 'â': 'a', 'ä': 'a', 'á': 'a', 'À': 'A', 'Â': 'A', 'Ä': 'A', 'Á': 'A',
        'ù': 'u', 'û': 'u', 'ü': 'u', 'ú': 'u', 'Ù': 'U', 'Û': 'U', 'Ü': 'U', 'Ú': 'U',
        'î': 'i', 'ï': 'i', 'í': 'i', 'ì': 'i', 'Î': 'I', 'Ï': 'I', 'Í': 'I', 'Ì': 'I',
        'ô': 'o', 'ö': 'o', 'ó': 'o', 'ò': 'o', 'Ô': 'O', 'Ö': 'O', 'Ó': 'O', 'Ò': 'O',
        'ç': 'c', 'Ç': 'C',
        'ñ': 'n', 'Ñ': 'N',
        'œ': 'oe', 'Œ': 'OE', 'æ': 'ae', 'Æ': 'AE',
        '\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"',
        ''': "'", ''': "'", '"': '"', '"': '"',
        '–': '-', '—': '-',
        '…': '...', '•': '*',
    }
    result = str(text)
    for old, new in replacements.items():
        result = result.replace(old, new)
    result = result.encode('ascii', 'ignore').decode('ascii')
    return result


class PDFSchedule(FPDF):
    """Custom PDF class for exam schedules."""

    def __init__(self, title):
        super().__init__(orientation='L')  # Landscape for wide tables
        self.title_text = sanitize_text(title)

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, self.title_text, ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def build_schedule_pivot(cur, form_id):
    """Build a pivot table with groups as rows and modules as columns."""
    # Get all exam data for this formation
    cur.execute("""
        SELECT
            m.nom as module,
            ex.groupes as groupe,
            l.nom as salle,
            DATE_FORMAT(ex.date_heure, '%d/%m') as date,
            DATE_FORMAT(ex.date_heure, '%H:%i') as heure
        FROM examens ex
        JOIN modules m ON ex.module_id = m.id
        JOIN lieu_examens l ON ex.lieu_examen_id = l.id
        WHERE m.formation_id = %s
        ORDER BY m.nom, ex.groupes
    """, (form_id,))
    results = cur.fetchall()

    if not results:
        return None, []

    # Get list of modules for this formation
    cur.execute("""
        SELECT DISTINCT m.nom
        FROM modules m
        WHERE m.formation_id = %s
        ORDER BY m.nom
    """, (form_id,))
    modules = [row[0] for row in cur.fetchall()]

    # Get list of groups for this formation
    cur.execute("""
        SELECT DISTINCT groupe
        FROM etudiants
        WHERE formation_id = %s
        ORDER BY groupe
    """, (form_id,))
    groups = [row[0] for row in cur.fetchall()]

    # Build the pivot data structure
    # Each cell will contain: "Salle\nDate Heure"
    pivot_data = {}
    for group in groups:
        pivot_data[group] = {module: "-" for module in modules}

    # Fill in the data from exam results
    for module, groupe_str, salle, date, heure in results:
        if groupe_str:
            # groupe_str can be "1" or "1,2" etc.
            for g in groupe_str.split(","):
                g = int(g.strip())
                if g in pivot_data:
                    pivot_data[g][module] = f"{salle}\n{date} {heure}"

    # Convert to DataFrame
    rows = []
    for group in sorted(pivot_data.keys()):
        row = {"Groupe": f"G{group}"}
        for module in modules:
            row[module] = pivot_data[group][module]
        rows.append(row)

    df = pd.DataFrame(rows)
    return df, modules


def generate_pdf(formation_name, schedule_df, modules, groups_info=None):
    """Generate PDF for a formation's schedule with groups as rows."""
    pdf = PDFSchedule(f"Emploi du Temps - {formation_name}")
    pdf.add_page()

    # Show group counts if available
    if groups_info is not None and not groups_info.empty:
        pdf.set_font("Helvetica", size=9)
        group_text = " | ".join([f"G{row['Groupe']}: {row['Effectif']} etud." for _, row in groups_info.iterrows()])
        pdf.cell(0, 6, sanitize_text(group_text), ln=True)
        pdf.ln(3)

    if schedule_df is None or schedule_df.empty:
        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 10, "Aucun examen planifie.", ln=True)
        return pdf.output()

    # Calculate column widths
    num_modules = len(modules)
    available_width = 277 - 20  # A4 landscape width minus margins and Groupe column
    groupe_col_width = 20
    module_col_width = min(45, available_width / max(num_modules, 1))

    # Table header
    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("Helvetica", "B", 8)

    pdf.cell(groupe_col_width, 10, "Groupe", border=1, fill=True, align="C")
    for module in modules:
        module_short = sanitize_text(module)
        if len(module_short) > 20:
            module_short = module_short[:18] + ".."
        pdf.cell(module_col_width, 10, module_short, border=1, fill=True, align="C")
    pdf.ln()

    # Table content
    pdf.set_font("Helvetica", size=7)
    for _, row in schedule_df.iterrows():
        pdf.cell(groupe_col_width, 12, str(row["Groupe"]), border=1, align="C")
        for module in modules:
            cell_text = sanitize_text(str(row[module]))
            # Handle multiline cell content
            if "\n" in cell_text:
                parts = cell_text.split("\n")
                cell_text = f"{parts[0][:15]}\n{parts[1]}" if len(parts) > 1 else parts[0]
            pdf.cell(module_col_width, 12, cell_text.replace("\n", " | "), border=1, align="C")
        pdf.ln()

    return pdf.output()


try:
    conn = get_connection()
    cur = conn.cursor()

    # === Filters ===
    st.subheader("Filtres")

    col1, col2, col3 = st.columns(3)

    # Get departments
    cur.execute("SELECT id, nom FROM departements ORDER BY nom")
    departments = cur.fetchall()

    with col1:
        dept_options = ["Tous"] + [d[1] for d in departments]
        selected_dept = st.selectbox("Departement", dept_options)

    # Get specialties based on department
    if selected_dept == "Tous":
        cur.execute("SELECT id, nom, cycle FROM specialites ORDER BY nom")
    else:
        dept_id = next(d[0] for d in departments if d[1] == selected_dept)
        cur.execute("SELECT id, nom, cycle FROM specialites WHERE dept_id = %s ORDER BY nom", (dept_id,))
    specialties = cur.fetchall()

    with col2:
        spec_options = ["Toutes"] + [f"{s[1]} ({s[2]})" for s in specialties]
        selected_spec = st.selectbox("Specialite", spec_options)

    # Get formations based on specialty
    if selected_spec == "Toutes":
        if selected_dept == "Tous":
            cur.execute("""
                SELECT f.id, CONCAT(s.nom, ' ', f.cycle, ' S', f.semestre) as name
                FROM formations f
                JOIN specialites s ON f.specialite_id = s.id
                ORDER BY s.nom, f.cycle, f.semestre
            """)
        else:
            cur.execute("""
                SELECT f.id, CONCAT(s.nom, ' ', f.cycle, ' S', f.semestre) as name
                FROM formations f
                JOIN specialites s ON f.specialite_id = s.id
                WHERE s.dept_id = %s
                ORDER BY s.nom, f.cycle, f.semestre
            """, (dept_id,))
    else:
        spec_id = next(s[0] for s in specialties if f"{s[1]} ({s[2]})" == selected_spec)
        cur.execute("""
            SELECT f.id, CONCAT(s.nom, ' ', f.cycle, ' S', f.semestre) as name
            FROM formations f
            JOIN specialites s ON f.specialite_id = s.id
            WHERE f.specialite_id = %s
            ORDER BY f.semestre
        """, (spec_id,))

    formations = cur.fetchall()

    with col3:
        form_options = ["Toutes"] + [f[1] for f in formations]
        selected_form = st.selectbox("Formation", form_options)

    st.markdown("---")

    # === Schedule Display ===
    if selected_form != "Toutes":
        form_id = next(f[0] for f in formations if f[1] == selected_form)
        form_name = selected_form

        # Build pivot table
        schedule_df, modules = build_schedule_pivot(cur, form_id)

        # Get group information
        cur.execute("""
            SELECT groupe, COUNT(*) as effectif
            FROM etudiants
            WHERE formation_id = %s
            GROUP BY groupe
            ORDER BY groupe
        """, (form_id,))
        groups = cur.fetchall()
        df_groups = pd.DataFrame(groups, columns=["Groupe", "Effectif"]) if groups else None

        st.subheader(f"Emploi du Temps: {form_name}")

        if schedule_df is not None and not schedule_df.empty:
            # Show group counts
            if df_groups is not None and not df_groups.empty:
                total_students = df_groups["Effectif"].sum()
                group_info = " | ".join([f"**G{row['Groupe']}**: {row['Effectif']}" for _, row in df_groups.iterrows()])
                st.markdown(f"{group_info} | **Total**: {total_students} etudiants")

            st.markdown("---")

            # Display the pivot table
            st.dataframe(schedule_df, use_container_width=True, height=400)

            # PDF Export button
            st.markdown("---")
            col1, col2 = st.columns([1, 4])
            with col1:
                pdf_bytes = generate_pdf(form_name, schedule_df, modules, df_groups)
                st.download_button(
                    label="Telecharger PDF",
                    data=pdf_bytes,
                    file_name=f"EDT_{form_name.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("Aucun examen planifie pour cette formation.")

    else:
        # Show all formations summary
        st.subheader("Resume des Formations")

        cur.execute("""
            SELECT
                d.nom as departement,
                CONCAT(s.nom, ' ', f.cycle, ' S', f.semestre) as formation,
                COUNT(DISTINCT m.id) as modules,
                COUNT(DISTINCT ex.id) as examens,
                COUNT(DISTINCT e.id) as etudiants
            FROM departements d
            JOIN specialites s ON s.dept_id = d.id
            JOIN formations f ON f.specialite_id = s.id
            LEFT JOIN modules m ON m.formation_id = f.id
            LEFT JOIN examens ex ON ex.module_id = m.id
            LEFT JOIN etudiants e ON e.formation_id = f.id
            GROUP BY d.id, d.nom, f.id, s.nom, f.cycle, f.semestre
            ORDER BY d.nom, s.nom, f.cycle, f.semestre
        """)

        results = cur.fetchall()
        df = pd.DataFrame(results,
                          columns=["Departement", "Formation", "Modules", "Examens", "Etudiants"])
        st.dataframe(df, use_container_width=True, height=500)

        # Bulk PDF export
        st.markdown("---")
        if st.button("Generer tous les PDFs"):
            with st.spinner("Generation des PDFs..."):
                from zipfile import ZipFile

                zip_buffer = BytesIO()
                with ZipFile(zip_buffer, 'w') as zip_file:
                    for form_id, form_name in formations:
                        schedule_df, modules = build_schedule_pivot(cur, form_id)
                        if schedule_df is not None and not schedule_df.empty:
                            # Get groups for this formation
                            cur.execute("""
                                SELECT groupe, COUNT(*) as effectif
                                FROM etudiants WHERE formation_id = %s
                                GROUP BY groupe ORDER BY groupe
                            """, (form_id,))
                            groups = cur.fetchall()
                            df_groups = pd.DataFrame(groups, columns=["Groupe", "Effectif"]) if groups else None
                            pdf_bytes = generate_pdf(form_name, schedule_df, modules, df_groups)
                            zip_file.writestr(f"EDT_{form_name.replace(' ', '_')}.pdf", pdf_bytes)

                zip_buffer.seek(0)
                st.download_button(
                    label="Telecharger tous les PDFs (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="EDT_Toutes_Formations.zip",
                    mime="application/zip"
                )

    conn.close()

except Exception as e:
    st.error(f"Erreur: {e}")
    import traceback
    st.code(traceback.format_exc())
