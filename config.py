"""
Configuration centralisée de l'application Search Engine.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
CACHE_DIR = BASE_DIR / "cache"
LOGS_DIR = BASE_DIR / "logs"
EXPORTS_DIR = BASE_DIR / "exports"

for directory in (DATA_DIR, ASSETS_DIR, CACHE_DIR, LOGS_DIR, EXPORTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

APP_NAME = "Advanced Search Engine"
APP_VERSION = "1.0.0"
APP_AUTHOR = "CodePal"
APP_ICON = ASSETS_DIR / "app_icon.png"

USERS_FILE = DATA_DIR / "users.json"
HISTORY_FILE = DATA_DIR / "history.json"
FAVORITES_FILE = DATA_DIR / "favorites.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
SESSION_FILE = DATA_DIR / "session.json"
LOG_FILE = LOGS_DIR / "app.log"

WINDOW_MIN_WIDTH = 1280
WINDOW_MIN_HEIGHT = 800
WINDOW_DEFAULT_WIDTH = 1600
WINDOW_DEFAULT_HEIGHT = 950

THEMES = {
    "light": {
        "bg": "#ffffff",
        "fg": "#000000",
        "accent": "#2563eb",
        "accent_hover": "#1d4ed8",
        "secondary": "#f3f4f6",
        "border": "#e5e7eb",
        "card": "#ffffff",
        "success": "#16a34a",
        "warning": "#f59e0b",
        "error": "#dc2626",
        "text_muted": "#6b7280"
    },
    "dark": {
        "bg": "#0f172a",
        "fg": "#f8fafc",
        "accent": "#3b82f6",
        "accent_hover": "#2563eb",
        "secondary": "#1e293b",
        "border": "#334155",
        "card": "#1e293b",
        "success": "#22c55e",
        "warning": "#fbbf24",
        "error": "#ef4444",
        "text_muted": "#94a3b8"
    }
}

SEARCH_ENGINES = {
    "Google": "https://www.google.com/search?q={}",
    "Bing": "https://www.bing.com/search?q={}",
    "DuckDuckGo": "https://duckduckgo.com/?q={}",
    "Yahoo": "https://search.yahoo.com/search?p={}",
    "Wikipedia": "https://en.wikipedia.org/wiki/Special:Search?search={}",
    "YouTube": "https://www.youtube.com/results?search_query={}",
    "GitHub": "https://github.com/search?q={}",
    "StackOverflow": "https://stackoverflow.com/search?q={}"
}

IMAGE_PROVIDERS = {
    "Unsplash": "https://source.unsplash.com/featured/400x300/?{}",
    "LoremFlickr": "https://loremflickr.com/400/300/{}",
    "Picsum": "https://picsum.photos/400/300"
}

DEFAULT_SETTINGS = {
    "theme": "light",
    "search_engine": "Google",
    "image_provider": "LoremFlickr",
    "results_per_page": 20,
    "auto_refresh": True,
    "save_history": True,
    "notifications": True,
    "language": "fr"
}

SAMPLE_USER_FILE = DATA_DIR / "users_sample.json"
