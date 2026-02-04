import streamlit as st
import pandas as pd
import requests
import os
import matplotlib.pyplot as plt
import seaborn as sns

# --- CONFIG PAGE ---
st.set_page_config(page_title="Marmiton Data Analytics", layout="wide", page_icon="🥘")

# --- CSS CUSTOM ---
st.markdown("""
<style>
    .metric-box {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- CONFIG API ---
API_URL = os.getenv("API_URL", "http://localhost:8000")

# --- FONCTIONS API ---
def get_stats():
    try:
        response = requests.get(f"{API_URL}/stats")
        if response.status_code == 200:
            return response.json()
    except:
        return None
    return None

def get_recipes(page=1, limit=10, category=None):
    params = {"page": page, "limit": limit}
    if category and category != "Toutes":
        params["category"] = category
    try:
        response = requests.get(f"{API_URL}/recipes", params=params)
        if response.status_code == 200:
            return response.json()
    except:
        return None
    return None

def search_recipes(query):
    try:
        response = requests.get(f"{API_URL}/search", params={"q": query})
        if response.status_code == 200:
            return response.json()
    except:
        return None
    return None

# --- SIDEBAR ---
with st.sidebar:
    st.title("👨‍🍳 Navigation")
    page = st.radio("Menu", ["📊 Dashboard & KPIs", "🔎 Moteur de Recherche", "⚙️ Specs & Doc"])
    
    st.markdown("---")
    st.info(f"Connected to API: {API_URL}")

# --- PAGE 1: DASHBOARD ---
if page == "📊 Dashboard & KPIs":
    st.title("📊 Dashboard Analytique")
    
    stats = get_stats()
    
    if stats:
        # KPI Row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Recettes", stats.get("total_recipes", 0))
        with col2:
            nb_categories = len(stats.get("categories_distribution", {}))
            st.metric("Nombre Catégories", nb_categories)
        with col3:
            st.metric("Status API", "En Ligne")

        st.markdown("---")

        # Charts row
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Distribution par Catégorie")
            cat_data = stats.get("categories_distribution", {})
            if cat_data:
                df_cat = pd.DataFrame(list(cat_data.items()), columns=["Catégorie", "Nombre"])
                fig, ax = plt.subplots()
                sns.barplot(data=df_cat, x="Catégorie", y="Nombre", ax=ax, palette="viridis")
                plt.xticks(rotation=45)
                st.pyplot(fig)
            else:
                st.info("Pas de données de catégories.")

        with col_chart2:
            st.subheader("Aperçu des données")
            # On charge un petit échantillon pour montrer un tableau
            sample = get_recipes(limit=5)
            if sample and "data" in sample:
                df_sample = pd.DataFrame(sample["data"])
                if not df_sample.empty and "titre" in df_sample.columns and "note" in df_sample.columns:
                     st.dataframe(df_sample[["titre", "note", "categorie_principale"]])
    else:
        st.error("Impossible de contacter l'API. Vérifiez que le conteneur 'api' tourne bien.")

# --- PAGE 2: RECHERCHE ---
elif page == "🔎 Moteur de Recherche":
    st.title("🔎 Recherche de Recettes")
    
    search_query = st.text_input("Rechercher une recette (ex: 'Chocolat')", "")
    
    if search_query:
        with st.spinner("Recherche via API..."):
            results = search_recipes(search_query)
        
        if results and "data" in results:
            count = results["count"]
            data = results["data"]
            st.success(f"{count} résultats trouvés.")
            
            for recette in data:
                with st.expander(f"{recette.get('titre', 'Sans titre')} - {recette.get('note', 'N/A')}"):
                    st.write(f"**Catégorie:** {recette.get('categorie_principale')}")
                    st.write(f"**Ingrédients:** {recette.get('ingredients', 'Non spécifié')}") # Adapter selon structure JSON
                    if recette.get('url'):
                        st.markdown(f"[Voir sur Marmiton]({recette.get('url')})")
        else:
            st.warning("Aucun résultat ou erreur API.")

    st.markdown("---")
    st.subheader("Catalogue de Recettes")
    
    # Filtres & Pagination
    col_filter, col_page = st.columns([2, 1])
    with col_filter:
        cat_filter = st.selectbox("Filtrer par catégorie", ["Toutes", "Entrées", "Plats principaux", "Desserts"]) # Adapter noms exacts
    with col_page:
        page_num = st.number_input("Page", min_value=1, value=1)
        
    data_page = get_recipes(page=page_num, category=cat_filter if cat_filter != "Toutes" else None)
    
    if data_page and "data" in data_page:
        df_recipes = pd.DataFrame(data_page["data"])
        if not df_recipes.empty:
            st.dataframe(df_recipes)
            st.caption(f"Page {data_page['page']} - Total: {data_page['total']}")
    else:
        st.info("Chargement des recettes...")

# --- PAGE 3: SPECS ---
elif page == "⚙️ Specs & Doc":
    st.title("⚙️ Documentation Technique")
    st.markdown("""
    ### Architecture Micro-services
    
    Cette application est composée de 4 services Docker :
    
    1.  **MongoDB** : Base de données NoSQL stockant les recettes.
    2.  **Loader** : Script d'importation unique (`dataset.json` -> MongoDB).
    3.  **API (FastAPI)** : Backend exposant les données via HTTP REST (`port 8000`).
    4.  **WebApp (Streamlit)** : Ce dashboard frontend (`port 8501`).
    
    ### Flux de Données
    
    1.  L'utilisateur interagit avec ce dashboard.
    2.  Le dashboard envoie une requête HTTP à l'API (`http://api:8000`).
    3.  L'API interroge MongoDB pour récupérer les données.
    4.  Les données remontent la chaîne jusqu'à l'affichage.
    """)