from fastapi import FastAPI, Query
from pymongo import MongoClient
import os
from typing import List, Optional

app = FastAPI(
    title="Marmiton API",
    description="API pour servir les recettes de cuisine Marmiton",
    version="1.0.0"
)

# --- CONFIGURATION ---
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
client = MongoClient(f"mongodb://{MONGO_HOST}:27017/")
db = client["marmiton_db"]
collection = db["recipes"]

# --- MODELS (Implicit via Dict for simplicity here) ---

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API Marmiton ! Allez sur /docs pour voir la doc."}

@app.get("/recipes", description="Récupère une liste de recettes avec pagination")
def get_recipes(
    page: int = Query(1, ge=1), 
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = None
):
    skip = (page - 1) * limit
    filter_query = {}
    if category:
        filter_query["categorie_principale"] = category
        
    recipes_cursor = collection.find(filter_query, {"_id": 0}).skip(skip).limit(limit)
    recipes = list(recipes_cursor)
    
    total_count = collection.count_documents(filter_query)
    
    return {
        "page": page,
        "limit": limit,
        "total": total_count,
        "data": recipes
    }

@app.get("/stats", description="Récupère des statistiques globales sur les données")
def get_stats():
    total_recipes = collection.count_documents({})
    
    # Agrégation pour compter par catégorie
    pipeline = [
        {"$group": {"_id": "$categorie_principale", "count": {"$sum": 1}}}
    ]
    categories_data = list(collection.aggregate(pipeline))
    categories_stats = {item["_id"]: item["count"] for item in categories_data if item["_id"]}

    return {
        "total_recipes": total_recipes,
        "categories_distribution": categories_stats
    }

@app.get("/search", description="Recherche simple dans les titres")
def search_recipes(q: str):
    # Recherche regex simple (pas aussi puissant qu'ElasticSearch, mais suffisant pour commencer)
    query = {"titre": {"$regex": q, "$options": "i"}}
    results = list(collection.find(query, {"_id": 0}).limit(20))
    return {"count": len(results), "data": results}
