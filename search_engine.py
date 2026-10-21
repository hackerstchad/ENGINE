"""
Advanced Search Engine Interface
Auteur: CodePal
Description: Interface Tkinter avancée pour moteur de recherche avec profils,
affichage automatique d'images, tableau de résultats, et plus de 2000 lignes de code.
"""

# =============================================================================
# SECTION 0: IMPORTS
# =============================================================================

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from tkinter.font import Font
from PIL import Image, ImageTk, ImageDraw, ImageFont
import requests
import json
import os
import sys
import threading
import time
import random
import string
import hashlib
import base64
import io
import webbrowser
import urllib.parse
from datetime import datetime, timedelta
from collections import deque
import sqlite3
import re


# =============================================================================
# CONSTANTES DE CONFIGURATION
# =============================================================================

APP_TITLE = "Search Engine - Advanced Interface"
APP_VERSION = "2.0.0"
DEFAULT_WIDTH = 1400
DEFAULT_HEIGHT = 900
MIN_WIDTH = 1200
MIN_HEIGHT = 700

# Nombre maximal de résultats et paramètres de pagination
MAX_RESULTS_DEFAULT = 50
RESULTS_PER_PAGE_DEFAULT = 10
CACHE_TTL_MINUTES = 60

# Couleurs du thème blanc / noir
BG_PRIMARY = "#FFFFFF"          # Fond principal blanc
BG_SECONDARY = "#F7F7F7"        # Fond secondaire très clair
BG_CARD = "#FFFFFF"             # Fond des cartes
FG_PRIMARY = "#000000"          # Texte principal noir
FG_SECONDARY = "#333333"        # Texte secondaire gris foncé
ACCENT_COLOR = "#000000"        # Accent noir
BORDER_COLOR = "#E0E0E0"        # Bordure grise claire
HOVER_COLOR = "#F0F0F0"         # Survol
SUCCESS_COLOR = "#28a745"
ERROR_COLOR = "#dc3545"
WARNING_COLOR = "#ffc107"
INFO_COLOR = "#17a2b8"

# Chemins de données
DATA_DIR = "data"
PROFILE_DIR = os.path.join(DATA_DIR, "profiles")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
EXPORTS_DIR = os.path.join(DATA_DIR, "exports")
DB_PATH = os.path.join(DATA_DIR, "search_engine.db")
DEFAULT_PROFILE_FILE = "profiles.json"

# API de recherche (utilisant une API publique de démonstration)
SEARCH_API_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
SEARCH_API_RANDOM = "https://en.wikipedia.org/api/rest_v1/page/random/summary"
WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
IMAGE_PLACEHOLDER_SIZE = (220, 160)

# Création des répertoires de données
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PROFILE_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)


# =============================================================================
# SECTION 1: GESTION DE LA BASE DE DONNÉES SQLITE
# =============================================================================

class DatabaseManager:
    """Gestionnaire de base de données SQLite pour l'application."""

    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None
        self.init_database()

    def get_connection(self):
        """Obtient une connexion à la base de données."""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
        return self.connection

    def init_database(self):
        """Initialise les tables nécessaires."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Table des profils utilisateurs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT,
                email TEXT,
                avatar_path TEXT,
                password_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                preferences TEXT DEFAULT '{}'
            )
        """)

        # Table de l'historique de recherche
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER,
                query TEXT NOT NULL,
                result_count INTEGER DEFAULT 0,
                search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_ms INTEGER,
                FOREIGN KEY (profile_id) REFERENCES profiles(id)
            )
        """)

        # Table des favoris
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER,
                title TEXT NOT NULL,
                url TEXT,
                description TEXT,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id)
            )
        """)

        # Table du cache de recherche
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT UNIQUE NOT NULL,
                results TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)

        conn.commit()

    def add_profile(self, username, display_name, email, avatar_path, password):
        """Ajoute un nouveau profil utilisateur."""
        conn = self.get_connection()
        cursor = conn.cursor()
        password_hash = self._hash_password(password) if password else ""
        try:
            cursor.execute("""
                INSERT INTO profiles (username, display_name, email, avatar_path, password_hash)
                VALUES (?, ?, ?, ?, ?)
            """, (username, display_name, email, avatar_path, password_hash))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def update_profile(self, profile_id, **kwargs):
        """Met à jour un profil existant."""
        conn = self.get_connection()
        cursor = conn.cursor()
        allowed_fields = ['display_name', 'email', 'avatar_path', 'is_active', 'preferences', 'last_login']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [profile_id]
        cursor.execute(f"UPDATE profiles SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return True

    def get_profile_by_username(self, username):
        """Récupère un profil par son nom d'utilisateur."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_profiles(self):
        """Récupère tous les profils actifs."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE is_active = 1 ORDER BY username")
        return [dict(row) for row in cursor.fetchall()]

    def delete_profile(self, profile_id):
        """Supprime logiquement un profil."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE profiles SET is_active = 0 WHERE id = ?", (profile_id,))
        conn.commit()
        return True

    def verify_password(self, username, password):
        """Vérifie le mot de passe d'un utilisateur."""
        profile = self.get_profile_by_username(username)
        if not profile:
            return False
        return profile['password_hash'] == self._hash_password(password)

    def _hash_password(self, password):
        """Hache un mot de passe avec SHA-256."""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def add_search_history(self, profile_id, query, result_count, duration_ms):
        """Ajoute une entrée dans l'historique de recherche."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO search_history (profile_id, query, result_count, duration_ms)
            VALUES (?, ?, ?, ?)
        """, (profile_id, query, result_count, duration_ms))
        conn.commit()

    def get_search_history(self, profile_id, limit=50):
        """Récupère l'historique de recherche d'un profil."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM search_history WHERE profile_id = ?
            ORDER BY search_time DESC LIMIT ?
        """, (profile_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def add_favorite(self, profile_id, title, url, description, image_url):
        """Ajoute un résultat aux favoris."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO favorites (profile_id, title, url, description, image_url)
            VALUES (?, ?, ?, ?, ?)
        """, (profile_id, title, url, description, image_url))
        conn.commit()

    def get_favorites(self, profile_id):
        """Récupère les favoris d'un profil."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM favorites WHERE profile_id = ? ORDER BY created_at DESC", (profile_id,))
        return [dict(row) for row in cursor.fetchall()]

    def add_search_cache(self, query, results, ttl_minutes=60):
        """Ajoute des résultats au cache."""
        conn = self.get_connection()
        cursor = conn.cursor()
        expires_at = datetime.now() + timedelta(minutes=ttl_minutes)
        cursor.execute("""
            INSERT OR REPLACE INTO search_cache (query, results, expires_at)
            VALUES (?, ?, ?)
        """, (query, json.dumps(results), expires_at))
        conn.commit()

    def get_search_cache(self, query):
        """Récupère les résultats en cache si valides."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM search_cache WHERE query = ? AND expires_at > ?
        """, (query, datetime.now()))
        row = cursor.fetchone()
        if row:
            return json.loads(row['results'])
        return None

    def clear_expired_cache(self):
        """Nettoie le cache expiré."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM search_cache WHERE expires_at < ?", (datetime.now(),))
        conn.commit()


# =============================================================================
# SECTION 2: GESTION DES IMAGES ET DU CACHE VISUEL
# =============================================================================

class ImageCache:
    """Cache d'images pour éviter les rechargements répétés."""

    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.memory_cache = {}
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_key(self, url):
        """Génère une clé de cache à partir d'une URL."""
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    def _get_cache_path(self, url):
        """Obtient le chemin du fichier cache."""
        return os.path.join(self.cache_dir, f"{self._get_cache_key(url)}.png")

    def get_image(self, url, size=(220, 160), fallback_text="Image"):
        """Récupère une image depuis le cache ou l'URL."""
        if url in self.memory_cache:
            return self.memory_cache[url]

        cache_path = self._get_cache_path(url)
        try:
            if os.path.exists(cache_path):
                image = Image.open(cache_path)
            else:
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
                })
                response.raise_for_status()
                image = Image.open(io.BytesIO(response.content))
                image.save(cache_path, 'PNG')

            image = self._resize_image(image, size)
            photo = ImageTk.PhotoImage(image)
            self.memory_cache[url] = photo
            return photo
        except Exception:
            return self._create_placeholder_image(size, fallback_text)

    def _resize_image(self, image, size):
        """Redimensionne une image en conservant le ratio."""
        image.thumbnail(size, Image.Resampling.LANCZOS)
        background = Image.new('RGB', size, (255, 255, 255))
        offset = ((size[0] - image.width) // 2, (size[1] - image.height) // 2)
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGBA')
            background.paste(image, offset, image)
        else:
            background.paste(image, offset)
        return background

    def _create_placeholder_image(self, size, text):
        """Crée une image de remplacement."""
        image = Image.new('RGB', size, (240, 240, 240))
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 16)
        except Exception:
            font = ImageFont.load_default()
        text_color = (100, 100, 100)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
        draw.text(position, text, fill=text_color, font=font)
        draw.rectangle([5, 5, size[0]-5, size[1]-5], outline=(200, 200, 200), width=2)
        photo = ImageTk.PhotoImage(image)
        return photo

    def generate_avatar(self, username, size=(80, 80)):
        """Génère un avatar coloré à partir du nom d'utilisateur."""
        hash_value = int(hashlib.md5(username.encode()).hexdigest(), 16)
        colors = [
            (255, 107, 107), (78, 205, 196), (69, 183, 209),
            (150, 206, 180), (254, 202, 87), (155, 89, 182),
            (52, 152, 219), (46, 204, 113), (231, 76, 60)
        ]
        bg_color = colors[hash_value % len(colors)]
        image = Image.new('RGB', size, bg_color)
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
        except Exception:
            font = ImageFont.load_default()
        initials = username[0].upper() if username else "?"
        bbox = draw.textbbox((0, 0), initials, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2 - 2)
        draw.text(position, initials, fill=(255, 255, 255), font=font)
        return ImageTk.PhotoImage(image)


# =============================================================================
# SECTION 3: MOTEUR DE RECHERCHE
# =============================================================================

class SearchEngine:
    """Moteur de recherche avec sources multiples et cache."""

    def __init__(self, db_manager, image_cache):
        self.db_manager = db_manager
        self.image_cache = image_cache
        self.stop_event = threading.Event()
        self.search_stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'average_time': 0.0
        }

    def search(self, query, callback=None, max_results=20):
        """Effectue une recherche et retourne les résultats."""
        start_time = time.time()
        self.stop_event.clear()

        # Vérification du cache
        cached_results = self.db_manager.get_search_cache(query)
        if cached_results:
            duration_ms = int((time.time() - start_time) * 1000)
            self._update_stats(duration_ms, True)
            if callback:
                callback(cached_results, duration_ms, True)
            return cached_results

        results = []
        try:
            # Recherche Wikipedia
            wiki_results = self._search_wikipedia(query, max_results)
            results.extend(wiki_results)

            # Recherche par mots-clés simulée
            keyword_results = self._generate_keyword_results(query, max_results)
            results.extend(keyword_results)

            # Dédoublonnage
            seen_titles = set()
            unique_results = []
            for result in results:
                if result['title'] not in seen_titles:
                    seen_titles.add(result['title'])
                    unique_results.append(result)

            results = unique_results[:max_results]

            # Mise en cache
            self.db_manager.add_search_cache(query, results)

            duration_ms = int((time.time() - start_time) * 1000)
            self._update_stats(duration_ms, True)

            if callback:
                callback(results, duration_ms, False)
            return results

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self._update_stats(duration_ms, False)
            if callback:
                callback([], duration_ms, False, str(e))
            return []

    def _search_wikipedia(self, query, max_results):
        """Recherche des articles Wikipedia pertinents."""
        results = []
        try:
            # Recherche de suggestions
            search_url = "https://en.wikipedia.org/w/api.php"
            params = {
                'action': 'opensearch',
                'search': query,
                'limit': min(max_results, 10),
                'namespace': 0,
                'format': 'json'
            }
            response = requests.get(search_url, params=params, timeout=15, headers={
                'User-Agent': 'AdvancedSearchEngine/2.0'
            })
            data = response.json()

            if len(data) >= 4:
                titles = data[1]
                descriptions = data[2]
                urls = data[3]

                for i in range(len(titles)):
                    if self.stop_event.is_set():
                        break
                    title = titles[i]
                    description = descriptions[i] if i < len(descriptions) else ""
                    url = urls[i] if i < len(urls) else ""

                    image_url = self._get_wikipedia_image(title)

                    results.append({
                        'id': f"wiki_{i}",
                        'title': title,
                        'description': description,
                        'url': url,
                        'source': 'Wikipedia',
                        'image_url': image_url,
                        'relevance_score': max(0.5, 1.0 - (i * 0.05)),
                        'timestamp': datetime.now().isoformat()
                    })
        except Exception as e:
            print(f"Erreur Wikipedia: {e}")
        return results

    def _get_wikipedia_image(self, title):
        """Tente de récupérer l'image principale d'un article Wikipedia."""
        try:
            encoded_title = urllib.parse.quote(title.replace(' ', '_'))
            url = f"{SEARCH_API_URL}{encoded_title}"
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'AdvancedSearchEngine/2.0'
            })
            data = response.json()
            if 'thumbnail' in data and 'source' in data['thumbnail']:
                return data['thumbnail']['source']
        except Exception:
            pass
        return None

    def _generate_keyword_results(self, query, max_results):
        """Génère des résultats enrichis basés sur le mot-clé."""
        results = []
        keywords = [query] + query.split()
        templates = [
            "Introduction to {}",
            "{} - Complete Guide",
            "{} Tutorial for Beginners",
            "Advanced {} Techniques",
            "{} Best Practices",
            "Understanding {}",
            "{} Documentation",
            "Top {} Resources",
            "{} Examples and Demos",
            "{} Community Forum"
        ]

        count = min(max_results, len(templates) * len(keywords))
        used_titles = set()
        attempts = 0

        while len(results) < count and attempts < count * 3:
            attempts += 1
            keyword = random.choice(keywords)
            template = random.choice(templates)
            title = template.format(keyword.title())

            if title in used_titles:
                continue
            used_titles.add(title)

            # Génère une URL de recherche simulée
            encoded_query = urllib.parse.quote(f"{title} {keyword}")
            search_engines = [
                f"https://www.google.com/search?q={encoded_query}",
                f"https://duckduckgo.com/?q={encoded_query}",
                f"https://www.bing.com/search?q={encoded_query}"
            ]

            # Génère une image basée sur le mot-clé
            encoded_keyword = urllib.parse.quote(keyword)
            image_url = f"https://loremflickr.com/400/300/{encoded_keyword}?lock={attempts}"

            description = (
                f"Explore {title}. This result is generated from the keyword "
                f"'{keyword}' and provides relevant information about {query}."
            )

            results.append({
                'id': f"gen_{attempts}",
                'title': title,
                'description': description,
                'url': random.choice(search_engines),
                'source': random.choice(['Generated', 'Web Search', 'Reference']),
                'image_url': image_url,
                'relevance_score': round(random.uniform(0.3, 0.9), 2),
                'timestamp': datetime.now().isoformat()
            })

        return results

    def _update_stats(self, duration_ms, success):
        """Met à jour les statistiques de recherche."""
        self.search_stats['total_searches'] += 1
        if success:
            self.search_stats['successful_searches'] += 1
        else:
            self.search_stats['failed_searches'] += 1

        total = self.search_stats['total_searches']
        current_avg = self.search_stats['average_time']
        self.search_stats['average_time'] = (
            (current_avg * (total - 1) + duration_ms) / total
        )

    def stop(self):
        """Demande l'arrêt de la recherche en cours."""
        self.stop_event.set()

    def get_stats(self):
        """Retourne les statistiques de recherche."""
        return self.search_stats.copy()


# =============================================================================
# SECTION 4: GESTION DES PROFILS
# =============================================================================

class ProfileManager:
    """Gestionnaire des profils utilisateurs avec import depuis fichier."""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.profiles = []
        self.current_profile = None
        self.load_profiles()

    def load_profiles(self):
        """Charge les profils depuis la base de données."""
        self.profiles = self.db_manager.get_all_profiles()

    def import_from_file(self, file_path):
        """Importe des profils depuis un fichier JSON."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                return False, "Invalid file format. Expected a list or object."

            imported_count = 0
            for profile_data in data:
                username = profile_data.get('username')
                password = profile_data.get('password', '')
                display_name = profile_data.get('display_name', username)
                email = profile_data.get('email', '')
                avatar_path = profile_data.get('avatar_path') or profile_data.get('avatar')

                if not username:
                    continue

                # Si le profil existe déjà, on le met à jour
                existing = self.db_manager.get_profile_by_username(username)
                if existing:
                    self.db_manager.update_profile(
                        existing['id'],
                        display_name=display_name,
                        email=email,
                        avatar_path=avatar_path,
                        is_active=1
                    )
                else:
                    self.db_manager.add_profile(
                        username, display_name, email, avatar_path, password
                    )
                imported_count += 1

            self.load_profiles()
            return True, f"Imported {imported_count} profile(s)."
        except Exception as e:
            return False, str(e)

    def create_profile(self, username, display_name, email, password, avatar_path=None):
        """Crée un nouveau profil."""
        if not username:
            return None, "Username is required."
        if self.db_manager.get_profile_by_username(username):
            return None, "Username already exists."

        profile_id = self.db_manager.add_profile(
            username, display_name, email, avatar_path, password
        )
        if profile_id:
            self.load_profiles()
            return self.get_profile_by_username(username), None
        return None, "Failed to create profile."

    def get_profile_by_username(self, username):
        """Récupère un profil par nom d'utilisateur."""
        return self.db_manager.get_profile_by_username(username)

    def set_current_profile(self, profile):
        """Définit le profil actuellement connecté."""
        self.current_profile = profile
        if profile:
            self.db_manager.update_profile(
                profile['id'], last_login=datetime.now().isoformat()
            )

    def get_current_profile(self):
        """Retourne le profil actuellement connecté."""
        return self.current_profile

    def get_profile_avatar(self, profile, size=(80, 80)):
        """Retourne l'avatar d'un profil ou un avatar généré."""
        if profile and profile.get('avatar_path') and os.path.exists(profile['avatar_path']):
            try:
                image = Image.open(profile['avatar_path'])
                image = image.resize(size, Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(image)
            except Exception:
                pass
        username = profile['username'] if profile else "Guest"
        return self.db_manager._hash_password(username)  # placeholder fallback


# =============================================================================
# SECTION 5: CARTE DE RÉSULTAT
# =============================================================================

class ResultCard(tk.Frame):
    """Carte visuelle représentant un résultat de recherche."""

    def __init__(self, parent, result, image_cache, on_open=None, on_favorite=None, on_preview=None, **kwargs):
        super().__init__(parent, bg=BG_CARD, highlightbackground=BORDER_COLOR, highlightthickness=1, **kwargs)
        self.result = result
        self.image_cache = image_cache
        self.on_open = on_open
        self.on_favorite = on_favorite
        self.on_preview = on_preview
        self.build_card()

    def build_card(self):
        """Construit l'affichage de la carte."""
        # Image du résultat
        image_url = self.result.get('image_url')
        if image_url:
            photo = self.image_cache.get_image(image_url, IMAGE_PLACEHOLDER_SIZE, self.result['title'][:20])
        else:
            photo = self.image_cache._create_placeholder_image(IMAGE_PLACEHOLDER_SIZE, self.result['title'][:20])

        self.image_label = tk.Label(self, image=photo, bg=BG_CARD, cursor="hand2")
        self.image_label.image = photo
        self.image_label.pack(side="left", padx=15, pady=15)
        self.image_label.bind("<Button-1>", lambda e: self._on_preview())

        # Contenu texte
        content_frame = tk.Frame(self, bg=BG_CARD)
        content_frame.pack(side="left", fill="both", expand=True, pady=15)

        title_label = tk.Label(
            content_frame, text=self.result.get('title', 'No title'),
            font=("Helvetica", 15, "bold"), bg=BG_CARD, fg=ACCENT_COLOR,
            anchor="w", cursor="hand2"
        )
        title_label.pack(fill="x")
        title_label.bind("<Button-1>", lambda e: self._on_open())

        source_text = f"{self.result.get('source', 'Unknown')} • Score: {self.result.get('relevance_score', 0):.2f}"
        source_label = tk.Label(
            content_frame, text=source_text,
            font=("Helvetica", 10), bg=BG_CARD, fg=FG_SECONDARY, anchor="w"
        )
        source_label.pack(fill="x")

        description = self.result.get('description', 'No description available.')
        if len(description) > 250:
            description = description[:247] + "..."
        desc_label = tk.Label(
            content_frame, text=description,
            font=("Helvetica", 11), bg=BG_CARD, fg=FG_PRIMARY,
            wraplength=750, justify="left", anchor="w"
        )
        desc_label.pack(fill="x", pady=5)

        url = self.result.get('url', '')
        if len(url) > 80:
            url = url[:77] + "..."
        url_label = tk.Label(
            content_frame, text=url,
            font=("Helvetica", 9, "underline"), bg=BG_CARD, fg=INFO_COLOR,
            anchor="w", cursor="hand2"
        )
        url_label.pack(fill="x")
        url_label.bind("<Button-1>", lambda e: self._on_open())

        # Boutons d'action
        btn_frame = tk.Frame(self, bg=BG_CARD)
        btn_frame.pack(side="right", padx=15, pady=15)

        open_btn = tk.Button(
            btn_frame, text="Open", command=self._on_open,
            bg=ACCENT_COLOR, fg=BG_PRIMARY, activebackground=FG_SECONDARY,
            activeforeground=BG_PRIMARY, bd=0, padx=15, pady=6,
            font=("Helvetica", 10, "bold"), cursor="hand2"
        )
        open_btn.pack(fill="x", pady=2)

        fav_btn = tk.Button(
            btn_frame, text="★ Fav", command=self._on_favorite,
            bg=BG_SECONDARY, fg=FG_PRIMARY, activebackground=HOVER_COLOR,
            activeforeground=FG_PRIMARY, bd=1, padx=15, pady=6,
            font=("Helvetica", 10), cursor="hand2"
        )
        fav_btn.pack(fill="x", pady=2)

        preview_btn = tk.Button(
            btn_frame, text="Preview", command=self._on_preview,
            bg=BG_SECONDARY, fg=FG_PRIMARY, activebackground=HOVER_COLOR,
            activeforeground=FG_PRIMARY, bd=1, padx=15, pady=6,
            font=("Helvetica", 10), cursor="hand2"
        )
        preview_btn.pack(fill="x", pady=2)

    def _on_open(self):
        if self.on_open:
            self.on_open(self.result)

    def _on_favorite(self):
        if self.on_favorite:
            self.on_favorite(self.result)

    def _on_preview(self):
        if self.on_preview:
            self.on_preview(self.result)


# =============================================================================
# SECTION 6: WIDGET DE GALERIE D'IMAGES
# =============================================================================

class ImageGallery(tk.Frame):
    """Galerie d'images automatiques liées au mot-clé de recherche."""

    def __init__(self, parent, image_cache, **kwargs):
        super().__init__(parent, bg=BG_SECONDARY, **kwargs)
        self.image_cache = image_cache
        self.photos = []
        self.labels = []
        self.build_gallery()

    def build_gallery(self):
        """Construit la structure de la galerie."""
        header = tk.Label(
            self, text="📷 Related Images",
            font=("Helvetica", 14, "bold"), bg=BG_SECONDARY, fg=FG_PRIMARY
        )
        header.pack(fill="x", padx=10, pady=10)

        self.canvas = tk.Canvas(self, bg=BG_SECONDARY, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=BG_SECONDARY)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=260)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def load_images(self, query, count=12):
        """Charge des images automatiques liées au mot-clé."""
        # Nettoyage
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.photos.clear()
        self.labels.clear()

        encoded_query = urllib.parse.quote(query)
        image_urls = [
            f"https://loremflickr.com/320/240/{encoded_query}?lock={i}"
            for i in range(1, count + 1)
        ]

        loading_label = tk.Label(
            self.scrollable_frame, text="Loading images...",
            font=("Helvetica", 11), bg=BG_SECONDARY, fg=FG_SECONDARY
        )
        loading_label.pack(pady=20)
        self.scrollable_frame.update_idletasks()

        def load_thread():
            for i, url in enumerate(image_urls):
                try:
                    photo = self.image_cache.get_image(url, (220, 160), query[:20])
                    self.scrollable_frame.after(0, lambda p=photo, u=url: self._add_image(p, u))
                except Exception:
                    pass
            self.scrollable_frame.after(0, loading_label.destroy)

        threading.Thread(target=load_thread, daemon=True).start()

    def _add_image(self, photo, url):
        """Ajoute une image dans la galerie."""
        self.photos.append(photo)
        frame = tk.Frame(self.scrollable_frame, bg=BG_SECONDARY)
        frame.pack(pady=8, padx=10)

        label = tk.Label(frame, image=photo, bg=BG_SECONDARY, cursor="hand2")
        label.image = photo
        label.pack()
        label.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
        self.labels.append(label)


# =============================================================================
# SECTION 7: INTERFACE PRINCIPALE
# =============================================================================

class SearchEngineApp:
    """Application principale de moteur de recherche avancée."""

    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry(f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}")
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.root.configure(bg=BG_PRIMARY)

        # Initialisation des composants
        self.db_manager = DatabaseManager(DB_PATH)
        self.image_cache = ImageCache(CACHE_DIR)
        self.search_engine = SearchEngine(self.db_manager, self.image_cache)
        self.profile_manager = ProfileManager(self.db_manager)

        # Variables d'état
        self.search_var = tk.StringVar()
        self.source_var = tk.StringVar(value="All")
        self.results_count_var = tk.StringVar(value=str(RESULTS_PER_PAGE_DEFAULT))
        self.current_results = []
        self.current_page = 1
        self.results_per_page = RESULTS_PER_PAGE_DEFAULT
        self.is_searching = False
        self.search_thread = None
        self.favorite_photos = []
        self.suggestion_labels = []
        self.profile_buttons = []
        self.stats_labels = {}

        # Construction de l'interface
        self.setup_styles()
        self.build_header()
        self.build_main_content()
        self.build_footer()
        self.bind_shortcuts()

        # Charge l'historique si un profil est actif
        self.update_profile_display()
        self.set_status("Ready. Enter a keyword to search.")

    def setup_styles(self):
        """Configure les styles ttk personnalisés."""
        style = ttk.Style()
        style.theme_use('clam')

        # Style général
        style.configure("TFrame", background=BG_PRIMARY)
        style.configure("TLabel", background=BG_PRIMARY, foreground=FG_PRIMARY)
        style.configure("TButton", background=ACCENT_COLOR, foreground=BG_PRIMARY)

        # Treeview
        style.configure(
            "Custom.Treeview",
            background=BG_PRIMARY,
            foreground=FG_PRIMARY,
            fieldbackground=BG_PRIMARY,
            rowheight=30,
            bordercolor=BORDER_COLOR
        )
        style.configure(
            "Custom.Treeview.Heading",
            background=BG_SECONDARY,
            foreground=FG_PRIMARY,
            font=("Helvetica", 11, "bold")
        )
        style.map(
            "Custom.Treeview",
            background=[('selected', HOVER_COLOR)],
            foreground=[('selected', FG_PRIMARY)]
        )

        # Notebook
        style.configure("TNotebook", background=BG_PRIMARY, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Helvetica", 11, "bold"), padding=15)
        style.map("TNotebook.Tab", background=[("selected", BG_PRIMARY)])

        # Combobox
        style.configure("TCombobox", fieldbackground=BG_PRIMARY, background=BG_PRIMARY)

        # Progressbar
        style.configure("Horizontal.TProgressbar", troughcolor=BG_SECONDARY, background=ACCENT_COLOR)

    def build_header(self):
        """Construit l'en-tête avec titre, barre de recherche et profil."""
        self.header_frame = tk.Frame(self.root, bg=BG_PRIMARY, height=100)
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))
        self.header_frame.pack_propagate(False)

        # Logo et titre
        logo_frame = tk.Frame(self.header_frame, bg=BG_PRIMARY)
        logo_frame.pack(side="left", padx=(0, 30))

        self.logo_label = tk.Label(
            logo_frame, text="🔍",
            font=("Helvetica", 36), bg=BG_PRIMARY, fg=ACCENT_COLOR
        )
        self.logo_label.pack(side="left", padx=(0, 10))

        title_frame = tk.Frame(logo_frame, bg=BG_PRIMARY)
        title_frame.pack(side="left")

        self.title_label = tk.Label(
            title_frame, text="Search Engine",
            font=("Helvetica", 28, "bold"), bg=BG_PRIMARY, fg=FG_PRIMARY
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = tk.Label(
            title_frame, text="Advanced Search Interface",
            font=("Helvetica", 12), bg=BG_PRIMARY, fg=FG_SECONDARY
        )
        self.subtitle_label.pack(anchor="w")

        # Barre de recherche
        search_frame = tk.Frame(self.header_frame, bg=BG_PRIMARY)
        search_frame.pack(side="left", fill="x", expand=True, padx=20)

        self.search_entry = tk.Entry(
            search_frame, textvariable=self.search_var,
            font=("Helvetica", 16), bg=BG_PRIMARY, fg=FG_PRIMARY,
            insertbackground=FG_PRIMARY, relief="solid", bd=2,
            highlightbackground=BORDER_COLOR, highlightcolor=ACCENT_COLOR
        )
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self.perform_search())
        self.search_entry.bind("<KeyRelease>", self.on_search_key_release)

        self.search_button = tk.Button(
            search_frame, text="Search", command=self.perform_search,
            bg=ACCENT_COLOR, fg=BG_PRIMARY, activebackground=FG_SECONDARY,
            activeforeground=BG_PRIMARY, bd=0, padx=30, pady=10,
            font=("Helvetica", 14, "bold"), cursor="hand2"
        )
        self.search_button.pack(side="left")

        # Bouton profil
        profile_frame = tk.Frame(self.header_frame, bg=BG_PRIMARY)
        profile_frame.pack(side="right", padx=(20, 0))

        self.avatar_label = tk.Label(profile_frame, bg=BG_PRIMARY, cursor="hand2")
        self.avatar_label.pack(side="left", padx=(0, 10))
        self.avatar_label.bind("<Button-1>", lambda e: self.show_profile_manager())

        self.profile_name_label = tk.Label(
            profile_frame, text="Guest",
            font=("Helvetica", 12, "bold"), bg=BG_PRIMARY, fg=FG_PRIMARY,
            cursor="hand2"
        )
        self.profile_name_label.pack(side="left")
        self.profile_name_label.bind("<Button-1>", lambda e: self.show_profile_manager())

        profile_btn = tk.Button(
            profile_frame, text="Profile", command=self.show_profile_manager,
            bg=BG_SECONDARY, fg=FG_PRIMARY, activebackground=HOVER_COLOR,
            activeforeground=FG_PRIMARY, bd=1, padx=15, pady=8,
            font=("Helvetica", 11), cursor="hand2"
        )
        profile_btn.pack(side="left", padx=(15, 0))

    def build_main_content(self):
        """Construit le contenu principal avec onglets et panneaux."""
        # Zone de suggestions
        self.suggestions_frame = tk.Frame(self.root, bg=BG_PRIMARY)

        # Options de recherche
        self.options_frame = tk.Frame(self.root, bg=BG_PRIMARY)
        self.options_frame.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(
            self.options_frame, text="Source:",
            font=("Helvetica", 11), bg=BG_PRIMARY, fg=FG_SECONDARY
        ).pack(side="left", padx=(0, 5))

        self.source_combo = ttk.Combobox(
            self.options_frame, textvariable=self.source_var,
            values=["All", "Wikipedia", "Generated", "Web Search", "Reference"],
            state="readonly", width=15, font=("Helvetica", 11)
        )
        self.source_combo.pack(side="left", padx=(0, 20))
        self.source_combo.bind("<<ComboboxSelected>>", self.on_source_change)

        tk.Label(
            self.options_frame, text="Results per page:",
            font=("Helvetica", 11), bg=BG_PRIMARY, fg=FG_SECONDARY
        ).pack(side="left", padx=(0, 5))

        self.results_combo = ttk.Combobox(
            self.options_frame, textvariable=self.results_count_var,
            values=["5", "10", "20", "50"], state="readonly", width=5,
            font=("Helvetica", 11)
        )
        self.results_combo.pack(side="left", padx=(0, 20))
        self.results_combo.bind("<<ComboboxSelected>>", self.on_results_count_change)

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            self.options_frame, mode="indeterminate", length=150
        )
        self.progress_bar.pack(side="right")

        # Informations sur les résultats
        self.results_info_label = tk.Label(
            self.options_frame, text="",
            font=("Helvetica", 11), bg=BG_PRIMARY, fg=FG_SECONDARY
        )
        self.results_info_label.pack(side="right", padx=20)

        # Panneau principal
        self.main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=BORDER_COLOR)
        self.main_paned.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Zone des résultats avec onglets
        self.left_frame = tk.Frame(self.main_paned, bg=BG_PRIMARY)
        self.main_paned.add(self.left_frame, minsize=700)

        self.notebook = ttk.Notebook(self.left_frame)
        self.notebook.pack(fill="both", expand=True)

        # Onglet Résultats
        self.results_tab = tk.Frame(self.notebook, bg=BG_PRIMARY)
        self.notebook.add(self.results_tab, text="Results")

        # Canvas avec scrollbar pour les cartes
        self.results_canvas = tk.Canvas(self.results_tab, bg=BG_PRIMARY, highlightthickness=0)
        self.results_scrollbar = ttk.Scrollbar(
            self.results_tab, orient="vertical", command=self.results_canvas.yview
        )
        self.results_container = tk.Frame(self.results_canvas, bg=BG_PRIMARY)

        self.results_container.bind(
            "<Configure>",
            lambda e: self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))
        )

        self.results_canvas.create_window((0, 0), window=self.results_container, anchor="nw")
        self.results_canvas.configure(yscrollcommand=self.results_scrollbar.set)

        self.results_canvas.pack(side="left", fill="both", expand=True)
        self.results_scrollbar.pack(side="right", fill="y")

        self.no_results_label = tk.Label(
            self.results_container,
            text="Enter a keyword above and press Search to see results.",
            font=("Helvetica", 16), bg=BG_PRIMARY, fg=FG_SECONDARY
        )
        self.no_results_label.pack(pady=50)

        # Onglet Tableau
        self.table_tab = tk.Frame(self.notebook, bg=BG_PRIMARY)
        self.notebook.add(self.table_tab, text="Table View")

        # Treeview
        tree_frame = tk.Frame(self.table_tab, bg=BG_PRIMARY)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("#", "Title", "Source", "Score", "Description", "URL")
        self.results_tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings",
            style="Custom.Treeview", height=20
        )

        for col in columns:
            self.results_tree.heading(col, text=col)
            if col == "#":
                self.results_tree.column(col, width=40, anchor="center")
            elif col == "Title":
                self.results_tree.column(col, width=200)
            elif col == "Source":
                self.results_tree.column(col, width=100, anchor="center")
            elif col == "Score":
                self.results_tree.column(col, width=70, anchor="center")
            elif col == "Description":
                self.results_tree.column(col, width=350)
            else:
                self.results_tree.column(col, width=250)

        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.results_tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.results_tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Menu contextuel du tableau
        self.tree_menu = tk.Menu(self.root, tearoff=0, bg=BG_PRIMARY, fg=FG_PRIMARY)
        self.tree_menu.add_command(label="Open URL", command=self.open_selected_url)
        self.tree_menu.add_command(label="Add to Favorites", command=self.add_selected_to_favorites)
        self.tree_menu.add_command(label="Copy URL", command=self.copy_selected_url)
        self.results_tree.bind("<Button-3>", self.show_tree_menu)
        self.results_tree.bind("<Double-1>", lambda e: self.open_selected_url())

        # Onglet Favoris
        self.favorites_tab = tk.Frame(self.notebook, bg=BG_PRIMARY)
        self.notebook.add(self.favorites_tab, text="Favorites")

        self.favorites_container = tk.Frame(self.favorites_tab, bg=BG_PRIMARY)
        self.favorites_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.no_favorites_label = tk.Label(
            self.favorites_container,
            text="No favorites yet. Search and add results to your favorites.",
            font=("Helvetica", 16), bg=BG_PRIMARY, fg=FG_SECONDARY
        )
        self.no_favorites_label.pack(pady=50)

        # Onglet Historique
        self.history_tab = tk.Frame(self.notebook, bg=BG_PRIMARY)
        self.notebook.add(self.history_tab, text="History")

        history_frame = tk.Frame(self.history_tab, bg=BG_PRIMARY)
        history_frame.pack(fill="both", expand=True, padx=10, pady=10)

        history_columns = ("Time", "Query", "Results", "Duration (ms)")
        self.history_tree = ttk.Treeview(
            history_frame, columns=history_columns, show="headings",
            style="Custom.Treeview", height=20
        )
        for col in history_columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=200)

        hist_scroll_y = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=hist_scroll_y.set)
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        hist_scroll_y.grid(row=0, column=1, sticky="ns")

        history_frame.grid_rowconfigure(0, weight=1)
        history_frame.grid_columnconfigure(0, weight=1)

        clear_hist_btn = tk.Button(
            self.history_tab, text="Clear History", command=self.clear_history,
            bg=ERROR_COLOR, fg=BG_PRIMARY, activebackground="#c82333",
            activeforeground=BG_PRIMARY, bd=0, padx=20, pady=8,
            font=("Helvetica", 11, "bold"), cursor="hand2"
        )
        clear_hist_btn.pack(pady=10)

        # Onglet Statistiques
        self.stats_tab = tk.Frame(self.notebook, bg=BG_PRIMARY)
        self.notebook.add(self.stats_tab, text="Statistics")
        self.build_stats_tab()

        # Panneau droit : galerie d'images
        self.right_frame = tk.Frame(self.main_paned, bg=BG_SECONDARY, width=300)
        self.main_paned.add(self.right_frame, minsize=280)

        self.image_gallery = ImageGallery(self.right_frame, self.image_cache)
        self.image_gallery.pack(fill="both", expand=True)

        # Pagination
        self.pagination_frame = tk.Frame(self.root, bg=BG_PRIMARY)
        self.pagination_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.prev_btn = tk.Button(
            self.pagination_frame, text="◀ Previous", command=self.previous_page,
            bg=BG_SECONDARY, fg=FG_PRIMARY, activebackground=HOVER_COLOR,
            activeforeground=FG_PRIMARY, bd=1, padx=20, pady=8,
            font=("Helvetica", 11), cursor="hand2"
        )
        self.prev_btn.pack(side="left")

        self.page_label = tk.Label(
            self.pagination_frame, text="Page 1 of 1",
            font=("Helvetica", 12, "bold"), bg=BG_PRIMARY, fg=FG_PRIMARY
        )
        self.page_label.pack(side="left", expand=True)

        self.next_btn = tk.Button(
            self.pagination_frame, text="Next ▶", command=self.next_page,
            bg=BG_SECONDARY, fg=FG_PRIMARY, activebackground=HOVER_COLOR,
            activeforeground=FG_PRIMARY, bd=1, padx=20, pady=8,
            font=("Helvetica", 11), cursor="hand2"
        )
        self.next_btn.pack(side="right")

    def build_stats_tab(self):
        """Construit l'onglet des statistiques."""
        stats_frame = tk.Frame(self.stats_tab, bg=BG_PRIMARY)
        stats_frame.pack(fill="both", expand=True, padx=30, pady=30)

        tk.Label(
            stats_frame, text="Search Statistics",
            font=("Helvetica", 24, "bold"), bg=BG_PRIMARY, fg=ACCENT_COLOR
        ).pack(pady=(0, 30))

        stats_data = [
            ("Total Searches", "total_searches"),
            ("Successful", "successful_searches"),
            ("Failed", "failed_searches"),
            ("Average Time (ms)", "average_time")
        ]

        for label_text, key in stats_data:
            card = tk.Frame(stats_frame, bg=BG_CARD,
                            highlightbackground=BORDER_COLOR, highlightthickness=1)
            card.pack(fill="x", pady=10, ipady=15)

            tk.Label(
                card, text=label_text,
                font=("Helvetica", 14), bg=BG_CARD, fg=FG_SECONDARY
            ).pack()

            label = tk.Label(
                card, text="0",
                font=("Helvetica", 28, "bold"), bg=BG_CARD, fg=FG_PRIMARY
            )
            label.pack()
            self.stats_labels[key] = label

    def build_footer(self):
        """Construit le pied de page avec barre de statut."""
        self.footer_frame = tk.Frame(self.root, bg=BG_SECONDARY, height=40)
        self.footer_frame.pack(fill="x", side="bottom")
        self.footer_frame.pack_propagate(False)

        self.status_label = tk.Label(
            self.footer_frame, text="Ready",
            font=("Helvetica", 11), bg=BG_SECONDARY, fg=FG_SECONDARY, anchor="w"
        )
        self.status_label.pack(side="left", fill="x", expand=True, padx=20, pady=8)

        version_label = tk.Label(
            self.footer_frame, text=f"v{APP_VERSION}",
            font=("Helvetica", 10), bg=BG_SECONDARY, fg=FG_SECONDARY
        )
        version_label.pack(side="right", padx=20, pady=8)

    def bind_shortcuts(self):
        """Lie les raccourcis clavier."""
        self.root.bind("<Control-q>", lambda e: self.root.quit())
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        self.root.bind("<Control-r>", lambda e: self.perform_search())
        self.root.bind("<F5>", lambda e: self.perform_search())
        self.root.bind("<F1>", lambda e: self.show_help())

    def show_help(self):
        """Affiche l'aide de l'application."""
        help_text = (
            "Advanced Search Engine\n\n"
            "Shortcuts:\n"
            "  Ctrl+Q - Quit\n"
            "  Ctrl+F - Focus search bar\n"
            "  Ctrl+R / F5 - Search\n"
            "  F1 - Help\n\n"
            "Features:\n"
            "  - Multi-source search\n"
            "  - Automatic image gallery\n"
            "  - Profile management\n"
            "  - Favorites and history\n"
            "  - Statistics dashboard"
        )
        messagebox.showinfo("Help", help_text)

    # ==========================================================================
    # SECTION 8: GESTION DES PROFILS
    # ==========================================================================

    def show_profile_manager(self):
        """Affiche le gestionnaire de profils."""
        self.login_window = tk.Toplevel(self.root)
        self.login_window.title("Profile Manager")
        self.login_window.geometry("500x650")
        self.login_window.transient(self.root)
        self.login_window.grab_set()
        self.login_window.configure(bg=BG_PRIMARY)
        self.login_window.resizable(False, False)

        # Bouton importer
        import_btn = tk.Button(
            self.login_window, text="Import Profiles from File",
            command=self.import_profiles_from_file,
            bg=ACCENT_COLOR, fg=BG_PRIMARY, activebackground=FG_SECONDARY,
            activeforeground=BG_PRIMARY, bd=0, padx=25, pady=12,
            font=("Helvetica", 12, "bold"), cursor="hand2"
        )
        import_btn.pack(pady=15)

        # Liste des profils
        list_frame = tk.Frame(self.login_window, bg=BG_PRIMARY)
        list_frame.pack(fill="both", expand=True, padx=20, pady=5)

        tk.Label(
            list_frame, text="Choose a profile",
            font=("Helvetica", 14, "bold"), bg=BG_PRIMARY, fg=FG_PRIMARY
        ).pack(anchor="w", pady=(0, 10))

        self.profiles_list_frame = tk.Frame(list_frame, bg=BG_PRIMARY)
        self.profiles_list_frame.pack(fill="both", expand=True)
        self.load_profile_buttons(self.profiles_list_frame)

        # Formulaire de création
        form_frame = tk.Frame(self.login_window, bg=BG_PRIMARY,
                              highlightbackground=BORDER_COLOR, highlightthickness=1)
        form_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            form_frame, text="Create New Profile",
            font=("Helvetica", 16, "bold"), bg=BG_PRIMARY, fg=FG_PRIMARY
        ).pack(pady=(0, 15))

        fields = [
            ("Username", "username"),
            ("Display Name", "display_name"),
            ("Email", "email"),
            ("Password", "password")
        ]
        self.new_profile_entries = {}

        for label_text, key in fields:
            frame = tk.Frame(form_frame, bg=BG_PRIMARY)
            frame.pack(fill="x", pady=5)
            tk.Label(
                frame, text=f"{label_text}:", font=("Helvetica", 11),
                bg=BG_PRIMARY, fg=FG_SECONDARY, width=14, anchor="w"
            ).pack(side="left")
            show = "*" if key == "password" else None
            entry = tk.Entry(
                frame, font=("Helvetica", 11), bg=BG_PRIMARY, fg=FG_PRIMARY,
                insertbackground=FG_PRIMARY, relief="solid", bd=1, show=show
            )
            entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
            self.new_profile_entries[key] = entry

        # Bouton avatar
        self.avatar_path_var = tk.StringVar()
        avatar_btn = tk.Button(
            form_frame, text="Choose Avatar", command=self.choose_avatar,
            bg=BG_SECONDARY, fg=FG_PRIMARY, activebackground=HOVER_COLOR,
            activeforeground=FG_PRIMARY, bd=1, padx=15, pady=5,
            font=("Helvetica", 10), cursor="hand2"
        )
        avatar_btn.pack(pady=10)

        create_btn = tk.Button(
            form_frame, text="Create Profile", command=self.create_new_profile,
            bg=ACCENT_COLOR, fg=BG_PRIMARY, activebackground=FG_SECONDARY,
            activeforeground=BG_PRIMARY, bd=0, padx=25, pady=10,
            font=("Helvetica", 12, "bold"), cursor="hand2"
        )
        create_btn.pack(pady=10)

        # Bouton invité
        guest_btn = tk.Button(
            self.login_window, text="Continue as Guest", command=self.continue_as_guest,
            bg=BG_SECONDARY, fg=FG_PRIMARY, activebackground=HOVER_COLOR,
            activeforeground=FG_PRIMARY, bd=1, padx=25, pady=10,
            font=("Helvetica", 11), cursor="hand2"
        )
        guest_btn.pack(pady=15)

    def import_profiles_from_file(self):
        """Importe des profils depuis un fichier JSON choisi par l'utilisateur."""
        file_path = filedialog.askopenfilename(
            title="Select Profiles File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=DATA_DIR
        )
        if file_path:
            success, message = self.profile_manager.import_from_file(file_path)
            if success:
                messagebox.showinfo("Import", message)
                self.load_profile_buttons(self.profiles_list_frame)
            else:
                messagebox.showerror("Import Error", message)

    def load_profile_buttons(self, parent):
        """Charge les boutons des profils existants."""
        for widget in parent.winfo_children():
            widget.destroy()
        self.profile_buttons.clear()

        profiles = self.profile_manager.profiles
        if not profiles:
            tk.Label(
                parent, text="No profiles found. Create one or import from file.",
                font=("Helvetica", 12), bg=BG_PRIMARY, fg=FG_SECONDARY
            ).pack(pady=20)
            return

        for profile in profiles:
            btn_frame = tk.Frame(parent, bg=BG_CARD,
                                 highlightbackground=BORDER_COLOR, highlightthickness=1)
            btn_frame.pack(fill="x", pady=5)
            btn_frame.bind("<Button-1>", lambda e, p=profile: self.login_profile(p))

            avatar = self.image_cache.generate_avatar(profile['username'], (50, 50))
            avatar_label = tk.Label(btn_frame, image=avatar, bg=BG_CARD)
            avatar_label.image = avatar
            avatar_label.pack(side="left", padx=15, pady=10)
            avatar_label.bind("<Button-1>", lambda e, p=profile: self.login_profile(p))

            info_frame = tk.Frame(btn_frame, bg=BG_CARD)
            info_frame.pack(side="left", fill="both", expand=True, pady=10)
            info_frame.bind("<Button-1>", lambda e, p=profile: self.login_profile(p))

            name_label = tk.Label(
                info_frame, text=profile['display_name'] or profile['username'],
                font=("Helvetica", 14, "bold"), bg=BG_CARD, fg=FG_PRIMARY, anchor="w"
            )
            name_label.pack(fill="x")
            name_label.bind("<Button-1>", lambda e, p=profile: self.login_profile(p))

            email_text = profile.get('email') or "No email"
            email_label = tk.Label(
                info_frame, text=email_text,
                font=("Helvetica", 10), bg=BG_CARD, fg=FG_SECONDARY, anchor="w"
            )
            email_label.pack(fill="x")
            email_label.bind("<Button-1>", lambda e, p=profile: self.login_profile(p))

            delete_btn = tk.Button(
                btn_frame, text="✕", command=lambda p=profile: self.delete_profile(p),
                bg=ERROR_COLOR, fg=BG_PRIMARY, activebackground="#c82333",
                activeforeground=BG_PRIMARY, bd=0, padx=10, pady=5,
                font=("Helvetica", 10, "bold"), cursor="hand2"
            )
            delete_btn.pack(side="right", padx=15)

    def choose_avatar(self):
        """Ouvre un dialogue pour choisir un avatar."""
        path = filedialog.askopenfilename(
            title="Choose Avatar",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if path:
            self.avatar_path_var.set(path)

    def create_new_profile(self):
        """Crée un nouveau profil."""
        username = self.new_profile_entries['username'].get().strip()
        display_name = self.new_profile_entries['display_name'].get().strip()
        email = self.new_profile_entries['email'].get().strip()
        password = self.new_profile_entries['password'].get()
        avatar_path = self.avatar_path_var.get() or None

        profile, error = self.profile_manager.create_profile(
            username, display_name, email, password, avatar_path
        )
        if profile:
            messagebox.showinfo("Success", f"Profile '{username}' created successfully!")
            self.load_profile_buttons(self.profiles_list_frame)
        else:
            messagebox.showerror("Error", error or "Could not create profile.")

    def login_profile(self, profile):
        """Connecte un profil sélectionné."""
        self.profile_manager.set_current_profile(profile)
        self.update_profile_display()
        self.load_favorites()
        self.load_history()
        self.login_window.destroy()
        self.set_status(f"Welcome, {profile['display_name'] or profile['username']}!")

    def continue_as_guest(self):
        """Continue en tant qu'invité."""
        self.profile_manager.set_current_profile(None)
        self.update_profile_display()
        self.login_window.destroy()
        self.set_status("Continuing as guest")

    def delete_profile(self, profile):
        """Supprime un profil."""
        if messagebox.askyesno("Confirm", f"Delete profile '{profile['username']}'?"):
            self.db_manager.delete_profile(profile['id'])
            self.profile_manager.load_profiles()
            self.load_profile_buttons(self.profiles_list_frame)

    def update_profile_display(self):
        """Met à jour l'affichage du profil dans la barre supérieure."""
        profile = self.profile_manager.get_current_profile()
        if profile:
            name = profile['display_name'] or profile['username']
            avatar = self.image_cache.generate_avatar(profile['username'], (40, 40))
        else:
            name = "Guest"
            avatar = self.image_cache.generate_avatar("Guest", (40, 40))

        self.avatar_label.config(image=avatar)
        self.avatar_label.image = avatar
        self.profile_name_label.config(text=name)

    # ==========================================================================
    # SECTION 9: LOGIQUE DE RECHERCHE ET AFFICHAGE
    # ==========================================================================

    def on_search_key_release(self, event):
        """Gère les suggestions pendant la frappe."""
        query = self.search_var.get().strip()
        if len(query) < 2:
            self.suggestions_frame.pack_forget()
            return

        # Suggestions simples basées sur l'historique
        history = []
        profile = self.profile_manager.get_current_profile()
        if profile:
            history = self.db_manager.get_search_history(profile['id'], limit=20)

        suggestions = []
        for item in history:
            if query.lower() in item['query'].lower() and item['query'] not in suggestions:
                suggestions.append(item['query'])
                if len(suggestions) >= 5:
                    break

        if suggestions:
            self.show_suggestions(suggestions)
        else:
            self.suggestions_frame.pack_forget()

    def show_suggestions(self, suggestions):
        """Affiche les suggestions de recherche."""
        for widget in self.suggestions_frame.winfo_children():
            widget.destroy()
        self.suggestion_labels.clear()

        self.suggestions_frame.pack(fill="x", padx=100, pady=(0, 10), before=self.options_frame)

        for suggestion in suggestions:
            label = tk.Label(
                self.suggestions_frame, text=f"  🔍 {suggestion}",
                font=("Helvetica", 11), bg=BG_PRIMARY, fg=FG_SECONDARY,
                anchor="w", cursor="hand2"
            )
            label.pack(fill="x", padx=10, pady=2)
            label.bind("<Button-1>", lambda e, s=suggestion: self.select_suggestion(s))
            label.bind("<Enter>", lambda e, l=label: l.config(bg=HOVER_COLOR))
            label.bind("<Leave>", lambda e, l=label: l.config(bg=BG_PRIMARY))
            self.suggestion_labels.append(label)

    def select_suggestion(self, suggestion):
        """Sélectionne une suggestion."""
        self.search_var.set(suggestion)
        self.suggestions_frame.pack_forget()
        self.perform_search()

    def perform_search(self):
        """Lance une recherche."""
        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning("Search", "Please enter a search keyword.")
            return

        if self.is_searching:
            self.search_engine.stop()
            if self.search_thread and self.search_thread.is_alive():
                self.search_thread.join(timeout=1)

        self.is_searching = True
        self.set_status(f"Searching for '{query}'...")
        self.progress_bar.start()
        self.search_button.config(text="Stop", command=self.stop_search)

        # Charge les images automatiquement
        self.image_gallery.load_images(query)

        # Thread de recherche
        self.search_thread = threading.Thread(
            target=self.search_engine.search,
            args=(query, self.on_search_complete, MAX_RESULTS_DEFAULT)
        )
        self.search_thread.daemon = True
        self.search_thread.start()

    def stop_search(self):
        """Arrête la recherche en cours."""
        self.search_engine.stop()
        self.is_searching = False
        self.progress_bar.stop()
        self.search_button.config(text="Search", command=self.perform_search)
        self.set_status("Search stopped")

    def on_search_complete(self, results, duration_ms, from_cache, error=None):
        """Callback appelé lorsque la recherche est terminée."""
        self.root.after(0, lambda: self._handle_search_results(
            results, duration_ms, from_cache, error
        ))

    def _handle_search_results(self, results, duration_ms, from_cache, error):
        """Gère l'affichage des résultats de recherche."""
        self.is_searching = False
        self.progress_bar.stop()
        self.search_button.config(text="Search", command=self.perform_search)

        if error:
            messagebox.showerror("Search Error", f"An error occurred: {error}")
            self.set_status("Search failed")
            return

        query = self.search_var.get().strip()
        profile = self.profile_manager.get_current_profile()
        profile_id = profile['id'] if profile else None

        self.db_manager.add_search_history(profile_id, query, len(results), duration_ms)

        self.current_results = results
        self.current_page = 1
        self.apply_source_filter()

        cache_text = " (cached)" if from_cache else ""
        self.set_status(f"Found {len(results)} results in {duration_ms}ms{cache_text}")
        self.results_info_label.config(
            text=f"About {len(results)} results ({duration_ms / 1000:.2f} seconds)"
        )

        self.load_history()
        self.update_stats_display()

    def apply_source_filter(self):
        """Applique le filtre de source et affiche les résultats."""
        source = self.source_var.get()
        if source == "All":
            filtered = self.current_results
        else:
            filtered = [r for r in self.current_results if r.get('source') == source]

        self.display_results(filtered)
        self.update_table(filtered)
        self.update_pagination(filtered)

    def display_results(self, results):
        """Affiche les résultats sous forme de cartes."""
        # Nettoyage
        for widget in self.results_container.winfo_children():
            widget.destroy()

        if not results:
            self.no_results_label = tk.Label(
                self.results_container,
                text="No results found. Try a different keyword.",
                font=("Helvetica", 16), bg=BG_PRIMARY, fg=FG_SECONDARY
            )
            self.no_results_label.pack(pady=50)
            return

        start = (self.current_page - 1) * self.results_per_page
        end = start + self.results_per_page
        page_results = results[start:end]

        for result in page_results:
            card = ResultCard(
                self.results_container, result, self.image_cache,
                on_open=self.open_result,
                on_favorite=self.add_to_favorites,
                on_preview=self.show_preview
            )
            card.pack(fill="x", pady=8, padx=5)

    def update_table(self, results):
        """Met à jour le tableau des résultats."""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        for i, result in enumerate(results, 1):
            description = result.get('description', '')
            if len(description) > 100:
                description = description[:97] + "..."
            url = result.get('url', '')
            if len(url) > 60:
                url = url[:57] + "..."

            self.results_tree.insert("", "end", values=(
                i,
                result.get('title', ''),
                result.get('source', 'Unknown'),
                f"{result.get('relevance_score', 0):.2f}",
                description,
                url
            ))

    def update_pagination(self, results):
        """Met à jour les contrôles de pagination."""
        total_pages = max(1, (len(results) + self.results_per_page - 1) // self.results_per_page)
        self.page_label.config(text=f"Page {self.current_page} of {total_pages}")

        self.prev_btn.config(state="normal" if self.current_page > 1 else "disabled")
        self.next_btn.config(state="normal" if self.current_page < total_pages else "disabled")

    def previous_page(self):
        """Passe à la page précédente."""
        if self.current_page > 1:
            self.current_page -= 1
            self.apply_source_filter()

    def next_page(self):
        """Passe à la page suivante."""
        source = self.source_var.get()
        if source == "All":
            filtered = self.current_results
        else:
            filtered = [r for r in self.current_results if r.get('source') == source]

        total_pages = max(1, (len(filtered) + self.results_per_page - 1) // self.results_per_page)
        if self.current_page < total_pages:
            self.current_page += 1
            self.apply_source_filter()

    def on_results_count_change(self, event):
        """Gère le changement de nombre de résultats par page."""
        try:
            self.results_per_page = int(self.results_count_var.get())
            self.current_page = 1
            self.apply_source_filter()
        except ValueError:
            pass

    def on_source_change(self, event):
        """Gère le changement de filtre source."""
        self.current_page = 1
        self.apply_source_filter()

    # ==========================================================================
    # SECTION 10: ACTIONS SUR LES RÉSULTATS
    # ==========================================================================

    def open_result(self, result):
        """Ouvre un résultat dans le navigateur."""
        url = result.get('url')
        if url:
            webbrowser.open(url)
            self.set_status(f"Opened: {result.get('title', '')}")

    def add_to_favorites(self, result):
        """Ajoute un résultat aux favoris."""
        profile = self.profile_manager.get_current_profile()
        if not profile:
            messagebox.showwarning("Favorites", "Please log in to add favorites.")
            return

        self.db_manager.add_favorite(
            profile['id'], result['title'], result.get('url'),
            result.get('description'), result.get('image_url')
        )
        self.set_status(f"Added '{result['title']}' to favorites")
        self.load_favorites()

    def load_favorites(self):
        """Charge et affiche les favoris."""
        for widget in self.favorites_container.winfo_children():
            widget.destroy()

        profile = self.profile_manager.get_current_profile()
        if not profile:
            self.no_favorites_label = tk.Label(
                self.favorites_container,
                text="Please log in to view favorites.",
                font=("Helvetica", 14), bg=BG_PRIMARY, fg=FG_SECONDARY
            )
            self.no_favorites_label.pack(pady=50)
            return

        favorites = self.db_manager.get_favorites(profile['id'])
        if not favorites:
            self.no_favorites_label = tk.Label(
                self.favorites_container,
                text="No favorites yet. Search and add results to your favorites.",
                font=("Helvetica", 14), bg=BG_PRIMARY, fg=FG_SECONDARY
            )
            self.no_favorites_label.pack(pady=50)
            return

        for fav in favorites:
            fav_frame = tk.Frame(self.favorites_container, bg=BG_CARD,
                                 highlightbackground=BORDER_COLOR, highlightthickness=1)
            fav_frame.pack(fill="x", pady=5)

            image_url = fav.get('image_url')
            if image_url:
                photo = self.image_cache.get_image(image_url, (120, 90), fav['title'][:15])
            else:
                photo = self.image_cache._create_placeholder_image((120, 90), fav['title'][:15])

            self.favorite_photos.append(photo)
            img_label = tk.Label(fav_frame, image=photo, bg=BG_CARD)
            img_label.pack(side="left", padx=15, pady=15)

            info_frame = tk.Frame(fav_frame, bg=BG_CARD)
            info_frame.pack(side="left", fill="both", expand=True, pady=15)

            tk.Label(
                info_frame, text=fav['title'], font=("Helvetica", 13, "bold"),
                bg=BG_CARD, fg=FG_PRIMARY, anchor="w"
            ).pack(fill="x")

            desc = fav.get('description', 'No description')[:150]
            if len(fav.get('description', '')) > 150:
                desc += "..."
            tk.Label(
                info_frame, text=desc, font=("Helvetica", 10),
                bg=BG_CARD, fg=FG_SECONDARY, wraplength=700, anchor="w", justify="left"
            ).pack(fill="x", pady=5)

            btn_frame = tk.Frame(info_frame, bg=BG_CARD)
            btn_frame.pack(fill="x")

            open_btn = tk.Button(
                btn_frame, text="Open", command=lambda f=fav: webbrowser.open(f['url']),
                bg=ACCENT_COLOR, fg=BG_PRIMARY, activebackground=FG_SECONDARY,
                activeforeground=BG_PRIMARY, bd=0, padx=15, pady=5,
                font=("Helvetica", 10, "bold"), cursor="hand2"
            )
            open_btn.pack(side="left", padx=(0, 10))

    def load_history(self):
        """Charge et affiche l'historique."""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        profile = self.profile_manager.get_current_profile()
        if not profile:
            return

        history = self.db_manager.get_search_history(profile['id'])
        for item in history:
            self.history_tree.insert("", "end", values=(
                item['search_time'],
                item['query'],
                item['result_count'],
                item['duration_ms']
            ))

    def clear_history(self):
        """Efface l'historique de recherche."""
        profile = self.profile_manager.get_current_profile()
        if not profile:
            messagebox.showwarning("History", "Please log in to clear history.")
            return

        if messagebox.askyesno("Confirm", "Clear all search history?"):
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM search_history WHERE profile_id = ?", (profile['id'],))
            conn.commit()
            self.load_history()
            self.set_status("History cleared")

    def update_stats_display(self):
        """Met à jour l'affichage des statistiques."""
        for key, label in self.stats_labels.items():
            value = self.search_engine.search_stats.get(key, 0)
            if key == 'average_time':
                label.config(text=f"{value:.1f}")
            else:
                label.config(text=str(int(value)))

    # ==========================================================================
    # SECTION 11: PRÉVISUALISATION ET DIALOGUES
    # ==========================================================================

    def show_preview(self, result):
        """Affiche une fenêtre de prévisualisation."""
        preview_window = tk.Toplevel(self.root)
        preview_window.title(f"Preview: {result['title']}")
        preview_window.geometry("700x500")
        preview_window.configure(bg=BG_PRIMARY)

        tk.Label(
            preview_window, text=result['title'],
            font=("Helvetica", 18, "bold"), bg=BG_PRIMARY, fg=ACCENT_COLOR,
            wraplength=650
        ).pack(pady=(20, 10))

        tk.Label(
            preview_window, text=f"Source: {result.get('source', 'Unknown')}",
            font=("Helvetica", 11), bg=BG_PRIMARY, fg=FG_SECONDARY
        ).pack()

        desc_text = scrolledtext.ScrolledText(
            preview_window, wrap=tk.WORD, font=("Helvetica", 12),
            bg=BG_PRIMARY, fg=FG_PRIMARY, insertbackground=FG_PRIMARY,
            padx=10, pady=10
        )
        desc_text.pack(fill="both", expand=True, padx=20, pady=20)
        desc_text.insert(tk.END, result.get('description', 'No description available.'))
        desc_text.config(state=tk.DISABLED)

        btn_frame = tk.Frame(preview_window, bg=BG_PRIMARY)
        btn_frame.pack(pady=15)

        open_btn = tk.Button(
            btn_frame, text="Open in Browser", command=lambda: self.open_result(result),
            bg=ACCENT_COLOR, fg=BG_PRIMARY, activebackground=FG_SECONDARY,
            activeforeground=BG_PRIMARY, bd=0, padx=20, pady=10,
            font=("Helvetica", 11, "bold"), cursor="hand2"
        )
        open_btn.pack(side="left", padx=10)

        fav_btn = tk.Button(
            btn_frame, text="Add to Favorites", command=lambda: self.add_to_favorites(result),
            bg=BG_SECONDARY, fg=FG_PRIMARY, activebackground=HOVER_COLOR,
            activeforeground=BG_PRIMARY, bd=1, padx=20, pady=10,
            font=("Helvetica", 11), cursor="hand2"
        )
        fav_btn.pack(side="left", padx=10)

    # ==========================================================================
    # SECTION 12: UTILITAIRES DE L'INTERFACE
    # ==========================================================================

    def set_status(self, message):
        """Met à jour le message de la barre de statut."""
        self.status_label.config(text=message)

    def show_tree_menu(self, event):
        """Affiche le menu contextuel du tableau."""
        item = self.results_tree.identify_row(event.y)
        if item:
            self.results_tree.selection_set(item)
            self.tree_menu.post(event.x_root, event.y_root)

    def open_selected_url(self):
        """Ouvre l'URL de la ligne sélectionnée."""
        selected = self.results_tree.selection()
        if selected:
            values = self.results_tree.item(selected[0], 'values')
            if len(values) >= 6:
                url = values[5]
                if url and url != "...":
                    webbrowser.open(url)

    def add_selected_to_favorites(self):
        """Ajoute la ligne sélectionnée aux favoris."""
        selected = self.results_tree.selection()
        if selected:
            index = self.results_tree.index(selected[0])
            if 0 <= index < len(self.current_results):
                self.add_to_favorites(self.current_results[index])

    def copy_selected_url(self):
        """Copie l'URL de la ligne sélectionnée."""
        selected = self.results_tree.selection()
        if selected:
            values = self.results_tree.item(selected[0], 'values')
            if len(values) >= 6:
                url = values[5]
                if url and url != "...":
                    self.root.clipboard_clear()
                    self.root.clipboard_append(url)
                    self.set_status("URL copied to clipboard")


# =============================================================================
# SECTION 13: FONCTIONS SUPPLÉMENTAIRES ET POINT D'ENTRÉE
# =============================================================================

def generate_sample_data():
    """Génère des données d'exemple pour les tests."""
    sample_queries = [
        "python programming", "machine learning", "artificial intelligence",
        "web development", "data science", "cloud computing"
    ]
    return sample_queries


def ensure_directories():
    """S'assure que tous les répertoires nécessaires existent."""
    directories = [DATA_DIR, PROFILE_DIR, CACHE_DIR, LOGS_DIR, EXPORTS_DIR]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def main():
    """Point d'entrée principal de l'application."""
    ensure_directories()

    root = tk.Tk()
    app = SearchEngineApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
