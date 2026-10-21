"""
Gestionnaire de données JSON pour l'application Search Engine.
"""
import json
import os
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from config import (
    USERS_FILE, HISTORY_FILE, FAVORITES_FILE, SETTINGS_FILE, SESSION_FILE
)

logger = logging.getLogger(__name__)


class JSONDataStore:
    """Stockage JSON thread-safe avec cache mémoire et persistance automatique."""

    _instances: Dict[Path, "JSONDataStore"] = {}
    _lock = threading.Lock()

    def __new__(cls, file_path: Path, default: Any = None):
        with cls._lock:
            if file_path not in cls._instances:
                instance = super().__new__(cls)
                instance._file_path = file_path
                instance._default = default if default is not None else {}
                instance._data = None
                instance._mutex = threading.RLock()
                instance._listeners: List[Callable] = []
                cls._instances[file_path] = instance
            return cls._instances[file_path]

    def _ensure_file(self) -> None:
        if not self._file_path.exists():
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_atomic(self._default)

    def _load(self) -> Any:
        try:
            self._ensure_file()
            with open(self._file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erreur chargement {self._file_path}: {e}")
            return self._default

    def _save_atomic(self, data: Any) -> None:
        tmp = self._file_path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self._file_path)
        except Exception as e:
            logger.error(f"Erreur sauvegarde {self._file_path}: {e}")
            if tmp.exists():
                tmp.unlink()

    def get(self) -> Any:
        with self._mutex:
            if self._data is None:
                self._data = self._load()
            return self._data

    def set(self, data: Any) -> None:
        with self._mutex:
            self._data = data
            self._save_atomic(data)
            self._notify()

    def update(self, updater: Callable[[Any], Any]) -> Any:
        with self._mutex:
            data = self.get()
            new_data = updater(data)
            self._data = new_data
            self._save_atomic(new_data)
            self._notify()
            return new_data

    def add_listener(self, callback: Callable) -> None:
        with self._mutex:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable) -> None:
        with self._mutex:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def _notify(self) -> None:
        for listener in self._listeners:
            try:
                listener(self._data)
            except Exception as e:
                logger.error(f"Erreur listener: {e}")


class DataManager:
    """Point d'accès unifié aux données utilisateurs, historique, favoris, paramètres."""

    def __init__(self):
        self.users = JSONDataStore(USERS_FILE, {"users": [], "last_id": 0})
        self.history = JSONDataStore(HISTORY_FILE, {"queries": []})
        self.favorites = JSONDataStore(FAVORITES_FILE, {"items": []})
        self.settings = JSONDataStore(SETTINGS_FILE, {})
        self.session = JSONDataStore(SESSION_FILE, {})

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        data = self.users.get()
        for user in data.get("users", []):
            if user.get("id") == user_id:
                return user
        return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        data = self.users.get()
        for user in data.get("users", []):
            if user.get("username", "").lower() == username.lower():
                return user
        return None

    def add_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        data = self.users.get()
        data["last_id"] = data.get("last_id", 0) + 1
        user["id"] = data["last_id"]
        user["created_at"] = datetime.now().isoformat()
        data["users"].append(user)
        self.users.set(data)
        return user

    def update_user(self, user_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = self.users.get()
        for user in data.get("users", []):
            if user.get("id") == user_id:
                user.update(updates)
                user["updated_at"] = datetime.now().isoformat()
                self.users.set(data)
                return user
        return None

    def delete_user(self, user_id: int) -> bool:
        data = self.users.get()
        initial_len = len(data.get("users", []))
        data["users"] = [u for u in data.get("users", []) if u.get("id") != user_id]
        if len(data["users"]) != initial_len:
            self.users.set(data)
            return True
        return False

    def add_history(self, user_id: Optional[int], query: str, engine: str, results_count: int = 0) -> None:
        if not query or not query.strip():
            return
        entry = {
            "user_id": user_id,
            "query": query.strip(),
            "engine": engine,
            "results_count": results_count,
            "timestamp": datetime.now().isoformat()
        }
        data = self.history.get()
        data.setdefault("queries", []).insert(0, entry)
        data["queries"] = data["queries"][:1000]
        self.history.set(data)

    def get_history(self, user_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        data = self.history.get()
        queries = data.get("queries", [])
        if user_id is not None:
            queries = [q for q in queries if q.get("user_id") == user_id]
        return queries[:limit]

    def clear_history(self, user_id: Optional[int] = None) -> None:
        data = self.history.get()
        if user_id is None:
            data["queries"] = []
        else:
            data["queries"] = [q for q in data.get("queries", []) if q.get("user_id") != user_id]
        self.history.set(data)

    def add_favorite(self, user_id: Optional[int], title: str, url: str, query: str = "") -> Dict[str, Any]:
        item = {
            "user_id": user_id,
            "title": title,
            "url": url,
            "query": query,
            "created_at": datetime.now().isoformat()
        }
        data = self.favorites.get()
        data.setdefault("items", []).insert(0, item)
        self.favorites.set(data)
        return item

    def get_favorites(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        data = self.favorites.get()
        items = data.get("items", [])
        if user_id is not None:
            items = [i for i in items if i.get("user_id") == user_id]
        return items

    def remove_favorite(self, index: int, user_id: Optional[int] = None) -> bool:
        data = self.favorites.get()
        items = data.get("items", [])
        if user_id is not None:
            items = [i for i in items if i.get("user_id") == user_id]
        if 0 <= index < len(items):
            removed = items.pop(index)
            data["items"] = [i for i in data["items"] if i != removed]
            self.favorites.set(data)
            return True
        return False

    def get_settings(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        from config import DEFAULT_SETTINGS
        data = self.settings.get()
        base = DEFAULT_SETTINGS.copy()
        if user_id is None:
            base.update(data.get("global", {}))
        else:
            base.update(data.get("global", {}))
            base.update(data.get("users", {}).get(str(user_id), {}))
        return base

    def set_settings(self, settings: Dict[str, Any], user_id: Optional[int] = None) -> None:
        data = self.settings.get()
        if user_id is None:
            data["global"] = settings
        else:
            data.setdefault("users", {})[str(user_id)] = settings
        self.settings.set(data)

    def set_session(self, key: str, value: Any) -> None:
        data = self.session.get()
        data[key] = value
        self.session.set(data)

    def get_session(self, key: str, default: Any = None) -> Any:
        return self.session.get().get(key, default)

    def clear_session(self) -> None:
        self.session.set({})


data_manager = DataManager()
