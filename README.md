# SHA-256 — Démo pas-à-pas

Application pédagogique pour comprendre le fonctionnement de l'algorithme SHA-256 avec une interface Streamlit moderne.

## Installation

1. Installez les dépendances :
```bash
pip install streamlit plotly pandas numpy
```

## Lancement

Exécutez l'application avec :
```bash
streamlit run app.py
```

L'application s'ouvrira automatiquement dans votre navigateur par défaut à l'adresse http://localhost:8501

## Fonctionnalités

### 📝 Message
- Saisissez ou chargez un fichier texte
- Calculez le hash SHA-256 du message
- Affichez le digest en hexadécimal

### 📊 Padding
- Visualisez les informations de padding
- Affichez le nombre de bits de données, de padding et de longueur
- Consultez le nombre de blocs générés

### 📋 Schedule
- Consultez le schedule W[0..63] pour chaque bloc
- Naviguez entre les blocs et les rounds
- Le round actuel est mis en évidence

### 🔄 Rounds
- Explorez les 64 rounds de compression
- Visualisez les registres a..h et leurs valeurs
- Affichez les variables T1, T2, K, W
- Consultez les opérations Ch, Σ1, Maj
- **Mode lecture automatique** : Cliquez sur "▶ Play" pour voir le défilement automatique des rounds
- **Contrôle de vitesse** : Slider pour ajuster la vitesse (0.1 à 2.0 secondes entre chaque round)
- Barre de progression montrant l'avancement du bloc actuel
- Navigation manuelle avec les boutons ◀◀ et ▶▶

### 🔍 Comparaison
- Comparez deux messages différents
- Visualisez les différences bit à bit entre les hash
- Matrice 8x32 colorée : gris = bits à 0 identiques, vert = bits à 1 identiques, rouge = bits différents
- Statistiques de différence en pourcentage

## Fichiers

- `app.py` : Interface Streamlit
- `sha256.py` : Implémentation de l'algorithme SHA-256 avec traçage
- `utils.py` : Fonctions utilitaires (rotations, décalages, etc.)

## À propos

Cette application a été créée pour démontrer visuellement le fonctionnement de l'algorithme de hachage cryptographique SHA-256 (Secure Hash Algorithm 256-bit), défini dans la norme FIPS 180-4.

