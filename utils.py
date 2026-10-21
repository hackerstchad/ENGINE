"""
Utilitaires divers : loggers, helpers réseau, formatage, etc.
"""
import json
import logging
import hashlib
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from functools import wraps

from config import LOG_FILE, CACHE_DIR


def setup_logger(name: str = "SearchEngine") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


logger = setup_logger()


def safe_json_load(path: Path, default: Any = None) -> Any:
    if default is None:
        default = {}
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error("Erreur lecture JSON %s: %s", path, e)
    return default


def safe_json_save(path: Path, data: Any) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error("Erreur sauvegarde JSON %s: %s", path, e)
        return False


def sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sanitize_query(query: str) -> str:
    query = query.strip()
    query = re.sub(r"\s+", " ", query)
    return query[:200]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:80]


def fetch_url(url: str, timeout: int = 10, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
    if headers is None:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.warning("Échec requête %s: %s", url, e)
        return None


def cache_key(prefix: str, query: str) -> str:
    return f"{prefix}_{sha256_hash(query.lower().strip())}"


def get_cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def read_cache(key: str, ttl: int = 3600) -> Optional[Any]:
    path = get_cache_path(key)
    if not path.exists():
        return None
    try:
        mtime = path.stat().st_mtime
        if time.time() - mtime > ttl:
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Erreur lecture cache %s: %s", key, e)
        return None


def write_cache(key: str, data: Any) -> bool:
    return safe_json_save(get_cache_path(key), data)


def retry(times: int = 3, delay: float = 0.5, exceptions: Tuple = (Exception,)):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < times - 1:
                        time.sleep(delay * (2 ** attempt))
            raise last_exception
        return wrapper
    return decorator


def format_number(value: int) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}G"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def truncate_text(text: str, max_length: int = 120) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def extract_domain(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc or url
    except Exception:
        return url


def get_favicon_url(url: str) -> str:
    domain = extract_domain(url)
    if not domain:
        return ""
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=32"


def clean_html_entities(text: str) -> str:
    import html
    return html.unescape(text)


def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None


def generate_id() -> str:
    import uuid
    return uuid.uuid4().hex[:12]


def ellipsize(text: str, length: int = 50) -> str:
    return text if len(text) <= length else text[:length - 3] + "..."
