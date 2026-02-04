import time
import os
import logging
import random
import re
import hashlib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from pymongo import MongoClient, UpdateOne
from elasticsearch import Elasticsearch
from faker import Faker

# Log configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ScraperBot")

class MarmitonScraper:
    def __init__(self):
        self.mongo_host = os.getenv("MONGO_HOST", "localhost")
        self.elastic_host = os.getenv("ELASTIC_HOST", "localhost")
        # On scrape plusieurs catégories pour respecter la consigne "Segments à travailler"
        self.categories = ["entree", "plat-principal", "dessert"]
        self.db = None
        self.es = None
        self.driver = None

    def connect(self):
        """Boucle de connexion robuste (30 tentatives)"""
        for i in range(30):
            try:
                if not self.db:
                    self.db = MongoClient(f"mongodb://{self.mongo_host}:27017/")["marmiton_db"]
                
                if not self.es:
                    self.es = Elasticsearch([f"http://{self.elastic_host}:9200"])
                    if not self.es.ping(): raise Exception("Elastic not ready")
                
                logger.info("✅ Connexion BDD & Elastic OK")
                return True
            except Exception as e:
                logger.warning(f"⏳ Attente services ({i}/30)... {e}")
                time.sleep(2)
        return False

    def _get_driver(self):
        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        return webdriver.Chrome(options=opts)

    def _clean_data(self, text, type_data):
        """Nettoyage défensif des données"""
        if not text: return 0
        if type_data == 'duration':
            total = 0
            h = re.search(r'(\d+)h', text)
            m = re.search(r'(\d+)min', text)
            if h: total += int(h.group(1)) * 60
            if m: total += int(m.group(1))
            return total
        if type_data == 'reviews':
            # Extrait seulement les chiffres "45 avis" -> 45
            nums = re.findall(r'\d+', text)
            return int(nums[0]) if nums else 0
        return text

    def scrape(self):
        self.driver = self._get_driver()
        all_recipes = []

        for cat in self.categories:
            url = f"https://www.marmiton.org/recettes/recherche.aspx?aqt={cat}"
            logger.info(f"🔎 Scraping de la catégorie : {cat} ...")
            
            try:
                self.driver.get(url)
                time.sleep(2)
                
                # Cookie banner killer
                try: self.driver.find_element("id", "didomi-notice-agree-button").click()
                except: pass

                # Scroll
                for _ in range(3):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)

                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                cards = soup.find_all('a', class_=lambda x: x and 'recipe-card-link' in x)

                for card in cards:
                    try:
                        link = "https://www.marmiton.org" + card['href']
                        
                        # SPECIFICATION: product_id unique
                        p_id = hashlib.md5(link.encode()).hexdigest()
                        
                        title = card.find('h4').get_text(strip=True)
                        
                        # SPECIFICATION: rating stats
                        rate_tag = card.find(class_=lambda x: x and 'rating__value' in x)
                        rating = float(rate_tag.get_text().strip().replace('/5','').replace(',','.')) if rate_tag else 0.0
                        
                        count_tag = card.find(class_=lambda x: x and 'rating__count' in x)
                        reviews = self._clean_data(count_tag.get_text() if count_tag else "", 'reviews')

                        # SPECIFICATION: Price replacement (Duration) & Segments (Difficulty)
                        info_text = card.get_text(" ", strip=True)
                        duration = self._clean_data(info_text, 'duration')
                        
                        difficulty = "Moyen"
                        if "Facile" in info_text: difficulty = "Facile"
                        elif "Difficile" in info_text: difficulty = "Difficile"

                        img = card.find('img')
                        img_url = img.get('src') or img.get('data-src') if img else ""

                        all_recipes.append({
                            "product_id": p_id,
                            "name": title,
                            "category": cat,
                            "rating": rating,
                            "reviews_count": reviews,
                            "duration_min": duration,
                            "difficulty": difficulty,
                            "url": link,
                            "image_url": img_url,
                            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                    except Exception as e:
                        continue

            except Exception as e:
                logger.error(f"Erreur scraping {cat}: {e}")

        self.driver.quit()
        return all_recipes

    def save(self, data):
        if not data:
            logger.warning("⚠️ Pas de données. Activation du mode SECURE (Mock Data).")
            data = self.generate_mock()
        
        # 1. Mongo (Upsert)
        ops = [UpdateOne({'product_id': d['product_id']}, {'$set': d}, upsert=True) for d in data]
        if ops:
            self.db["recipes"].bulk_write(ops)
            logger.info(f"💾 {len(ops)} recettes sauvegardées dans Mongo.")

        # 2. Elastic
        if not self.es.indices.exists(index="recipes-idx"):
            self.es.indices.create(index="recipes-idx")
        
        for d in data:
            clean_doc = {k:v for k,v in d.items() if k != '_id'}
            self.es.index(index="recipes-idx", id=d['product_id'], document=clean_doc)
        logger.info("🔎 Indexation Elasticsearch terminée.")

    def generate_mock(self):
        """Générateur de secours pour garantir la démo"""
        fake = Faker('fr_FR')
        data = []
        for c in self.categories:
            for _ in range(10):
                data.append({
                    "product_id": fake.md5(),
                    "name": f"Recette {c} {fake.word()}",
                    "category": c,
                    "rating": round(random.uniform(3, 5), 2),
                    "reviews_count": random.randint(10, 1000),
                    "duration_min": random.randint(15, 120),
                    "difficulty": random.choice(["Facile", "Moyen", "Difficile"]),
                    "url": "http://localhost",
                    "image_url": "https://via.placeholder.com/150",
                    "updated_at": time.strftime("%Y-%m-%d")
                })
        return data

if __name__ == "__main__":
    bot = MarmitonScraper()
    if bot.connect():
        data = bot.scrape()
        bot.save(data)