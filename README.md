# Advanced Search Engine - Interface Tkinter

## Description

Application de bureau Python développée avec Tkinter offrant une interface avancée de moteur de recherche. Elle permet d'effectuer des recherches web, d'afficher les résultats dans un tableau interactif, de charger automatiquement des images correspondant aux mots-clés, de gérer des profils utilisateurs avec choix depuis un fichier, et bien plus encore.

## Fonctionnalités principales

- **Moteur de recherche multi-sources** : Google, Bing, DuckDuckGo, Yahoo, Wikipedia, YouTube, GitHub, StackOverflow
- **Affichage avancé des résultats** : tableau avec tri, filtrage, sélection, statistiques
- **Chargement automatique d'images** associées au mot-clé recherché
- **Gestion des profils utilisateurs** avec connexion depuis un fichier JSON
- **Thèmes clair/sombre** personnalisables
- **Historique des recherches** et favoris
- **Export des résultats** en CSV, JSON, TXT
- **Tableau de bord analytique** avec graphiques simplifiés
- **Interface moderne** sur une seule page avec barre de recherche, titre et design noir/blanc
- **Code de plus de 2000 lignes** réparti dans plusieurs modules modulaires

## Architecture

| Fichier | Description |
|---------|-------------|
| `search_engine.py` | Interface principale Tkinter (fenêtre unique) |
| `auth_manager.py` | Gestion de l'authentification et des profils |
| `data_manager.py` | Persistance des données (JSON) |
| `config.py` | Configuration centralisée |
| `utils.py` | Fonctions utilitaires |
| `requirements.txt` | Dépendances Python |
| `README.md` | Documentation |

## Installation

1. Cloner ou copier le projet dans un dossier
2. Créer un environnement virtuel (recommandé) :
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

## Utilisation

Lancer l'application :

```bash
python search_engine.py
```

### Créer un fichier d'utilisateurs

Un fichier exemple est généré automatiquement dans `data/users_sample.json`. Vous pouvez l'utiliser comme modèle pour créer votre propre fichier `users.json` dans le dossier `data/`.

Format attendu :

```json
[
  {
    "username": "admin",
    "password": "admin123",
    "role": "admin",
    "display_name": "Administrateur",
    "email": "admin@example.com",
    "avatar": "assets/default_avatar.png"
  },
  {
    "username": "user1",
    "password": "password1",
    "role": "user",
    "display_name": "Utilisateur 1",
    "email": "user1@example.com"
  }
]
```

### Connexion

1. Cliquez sur le bouton **Profil** en haut à droite
2. Choisissez un fichier JSON contenant vos utilisateurs
3. Sélectionnez un utilisateur dans la liste
4. Connectez-vous

### Recherche

1. Saisissez un mot-clé dans la barre de recherche
2. Appuyez sur Entrée ou cliquez sur le bouton de recherche
3. Les résultats s'affichent dans le tableau central
4. Les images correspondantes apparaissent dans la galerie à droite

## Raccourcis clavier

- `Ctrl+Q` : Quitter
- `Ctrl+F` : Focus sur la barre de recherche
- `Ctrl+R` : Lancer la recherche
- `Ctrl+E` : Exporter les résultats
- `Ctrl+H` : Afficher l'historique
- `F5` : Rafraîchir
- `F1` : Aide

## Personnalisation

Modifiez `config.py` pour ajuster :
- Les moteurs de recherche disponibles
- Les fournisseurs d'images
- Les couleurs des thèmes
- Les dimensions de la fenêtre
- Les paramètres par défaut

## Dépendances

- Python 3.8+
- Pillow
- requests
- python-dateutil


