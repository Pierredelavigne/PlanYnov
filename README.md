# � PlanYnov – Visualisateur 3D de l'occupation des salles

Ce projet propose une interface web interactive moderne pour visualiser en 3D l'occupation des salles d'un bâtiment, à partir de fichiers CSV, XLSX ou iCal contenant les emplois du temps. Il combine un backend robuste en Flask (Python) et un frontend 3D immersif en Three.js.🏢 PlanYnov – Visualisateur 3D de l'occupation des salles
This is an experiment by Google's Agent Jules.
Ce projet propose une interface web interactive pour visualiser en 3D l’occupation des salles d’un bâtiment, à partir d’un fichier CSV ou XLSX contenant les emplois du temps. Il combine un backend en Flask (Python) et un frontend 3D en Three.js.

---

## 🚀 Fonctionnalités

### 🔧 Backend (Flask / Python)
- 📂 Téléversement de fichiers CSV ou XLSX.
- 🧠 Analyse des données et déduction de l’étage via le nom de la salle.
- 🗃️ Stockage temporaire des données en mémoire.
- 🔗 API REST :  
  - `GET /api/salles/occupation` – Récupération de l'état d'occupation des salles.
- 📄 Page HTML minimaliste pour charger un fichier et afficher les données dans un tableau.

### 🎮 Frontend (Three.js / JavaScript)
- 🌐 Requêtes vers l’API Flask pour récupérer les données.
- 🧱 Représentation des salles par des **cubes 3D** organisés par étage.
- 🎨 Couleur dynamique des cubes : **rouge** (occupé) / **vert** (libre).
- 🧭 Navigation entre les étages.
- ℹ️ Détail affiché au clic sur une salle.
- 🌀 Caméra libre via OrbitControls.

---

## 🛠️ Installation

### Prérequis

- Python 3.8+
- `pip`

### Étapes

1. **Cloner le projet :**
   ```bash
   git clone https://github.com/<ton-utilisateur>/PlanYnov.git
   cd PlanYnov
   ```

2. **Créer un environnement virtuel (optionnel mais recommandé) :**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Sur Windows : venv\Scripts\activate
   ```

3. **Installer les dépendances :**
   ```bash
   pip install -r requirements.txt
   ```

4. **Lancer l'application Flask :**
   ```bash
   python app.py
   ```

5. **Accéder à l’interface :**  
   Ouvrir un navigateur à l'adresse :  
   👉 [http://localhost:5000](http://localhost:5000)

---

## 📁 Arborescence

```
PlanYnov/
├── app.py                 # Serveur Flask
├── requirements.txt       # Dépendances Python
├── README.md              # Documentation
├── public/                # Frontend statique (HTML, JS, CSS)
│   ├── index.html
│   ├── js/
│   │   └── viewer.js
│   └── css/
│       └── style.css
```

---

## 📦 Technologies utilisées

- **Python** & **Flask**
- **Pandas** (lecture des fichiers CSV/XLSX)
- **JavaScript** / **Three.js** (rendu 3D)
- **HTML/CSS** classiques
- **OrbitControls** pour les mouvements de caméra

---

## 📌 À venir (TODO)

- Sauvegarde persistante des emplois du temps.
- Sélecteur de date/heure dans l’interface.
- Amélioration du design UI.
- Affichage des créneaux horaires disponibles.
- Authentification utilisateur.

---

## 🧑‍💻 Auteurs

Projet développé par [Ton Nom / Ynov Nantes] dans le cadre d’un projet pédagogique.

---

## 📝 Licence

Ce projet est open-source sous licence MIT.