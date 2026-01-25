"""
Plateforme d'Optimisation des Emplois du Temps d'Examens Universitaires
Streamlit Frontend
"""

import streamlit as st

st.set_page_config(
    page_title="EDT Examens Universitaires",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Plateforme d'Optimisation des Emplois du Temps d'Examens")
st.markdown("---")

st.markdown("""
### Bienvenue sur la plateforme de gestion des examens

Utilisez le menu lateral pour naviguer entre les differentes sections:

- **Dashboard** - KPIs et statistiques globales
- **Emplois du Temps** - Consultation et export PDF par formation
- **Professeurs** - Planning de surveillance par professeur
- **Salles** - Occupation des amphis et salles
- **Conflits** - Detection et analyse des conflits
- **Optimisation** - Generation automatique des plannings
""")

# Quick stats in the main page
st.markdown("---")
st.subheader("Apercu Rapide")

try:
    from utils.db import get_connection

    conn = get_connection()
    cur = conn.cursor()

    col1, col2, col3, col4 = st.columns(4)

    cur.execute("SELECT COUNT(*) FROM etudiants")
    with col1:
        st.metric("Etudiants", f"{cur.fetchone()[0]:,}")

    cur.execute("SELECT COUNT(*) FROM modules")
    with col2:
        st.metric("Modules", f"{cur.fetchone()[0]:,}")

    cur.execute("SELECT COUNT(*) FROM professeurs")
    with col3:
        st.metric("Professeurs", f"{cur.fetchone()[0]:,}")

    cur.execute("SELECT COUNT(*) FROM examens")
    with col4:
        st.metric("Examens Planifies", f"{cur.fetchone()[0]:,}")

    conn.close()

except Exception as e:
    st.error(f"Erreur de connexion a la base de donnees: {e}")
