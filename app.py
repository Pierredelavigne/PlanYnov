"""
PlanYnov - Visualisateur 3D de l'occupation des salles
Backend Flask pour la gestion des emplois du temps et données de salles
"""

from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from ics import Calendar
import pandas as pd
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

# Configuration de l'application
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # À changer en production
CORS(app)

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration des fichiers
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'ics'}
DEFAULT_ICAL_FILE = "Edt_DELAVIGNE.ics"

# Créer le dossier d'upload s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Stockage en mémoire des données
current_schedule_data = []


class ScheduleParser:
    """Classe pour parser différents formats de fichiers d'emploi du temps"""
    
    @staticmethod
    def extract_room_code(location_info: str) -> Optional[str]:
        """Extrait le code de salle depuis les informations de localisation"""
        if not location_info:
            return None
            
        location_info = str(location_info)
        
        # Recherche du pattern "Salle XXX"
        if "Salle" in location_info:
            parts = location_info.split("Salle ")
            if len(parts) > 1:
                return parts[1].split(" ")[0]
        
        return None
    
    @staticmethod
    def determine_floor(room_code: str) -> int:
        """Détermine l'étage à partir du code de salle"""
        if not room_code or not room_code[0].isdigit():
            return 0
        return int(room_code[0])
    
    @staticmethod
    def parse_ical_file(filepath: str) -> List[Dict]:
        """Parse un fichier iCal et retourne les données des salles"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                calendar = Calendar(f.read())
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du fichier iCal: {e}")
            return []

        salles = []

        for event in calendar.events:
            room_code = ScheduleParser.extract_room_code(event.location)
            
            if room_code:
                try:
                    nom_salle = f"S{room_code.zfill(3)}"
                    debut = event.begin.datetime.strftime("%H:%M")
                    fin = event.end.datetime.strftime("%H:%M")
                    date = event.begin.datetime.strftime("%Y-%m-%d")
                    etage = ScheduleParser.determine_floor(room_code)

                    salle_data = {
                        "NomSalle": nom_salle,
                        "Etage": etage,
                        "DateOccupation": date,
                        "HeureDebut": debut,
                        "HeureFin": fin,
                        "NomClasse": event.name or "Cours non spécifié",
                        "NomIntervenant": event.description or "Non spécifié"
                    }
                    
                    salles.append(salle_data)
                    
                except Exception as e:
                    logger.warning(f"Erreur lors du traitement de l'événement: {e}")
                    continue

        logger.info(f"Parsé {len(salles)} événements depuis le fichier iCal")
        return salles
    
    @staticmethod
    def parse_csv_file(filepath: str) -> List[Dict]:
        """Parse un fichier CSV et retourne les données des salles"""
        try:
            df = pd.read_csv(filepath)
            
            # Mapping des colonnes possibles
            column_mapping = {
                'salle': ['NomSalle', 'Salle', 'Room', 'salle'],
                'etage': ['Etage', 'Floor', 'etage'],
                'date': ['DateOccupation', 'Date', 'date'],
                'heure_debut': ['HeureDebut', 'Start', 'Début', 'heure_debut'],
                'heure_fin': ['HeureFin', 'End', 'Fin', 'heure_fin'],
                'classe': ['NomClasse', 'Classe', 'Course', 'classe'],
                'intervenant': ['NomIntervenant', 'Intervenant', 'Teacher', 'intervenant']
            }
            
            # Normaliser les noms de colonnes
            normalized_data = []
            for _, row in df.iterrows():
                salle_data = {}
                for key, possible_names in column_mapping.items():
                    for name in possible_names:
                        if name in df.columns:
                            salle_data[column_mapping[key][0]] = row[name]
                            break
                    else:
                        salle_data[column_mapping[key][0]] = ""
                
                # Déduire l'étage si non spécifié
                if not salle_data.get('Etage') and salle_data.get('NomSalle'):
                    room_code = salle_data['NomSalle'].replace('S', '').replace('s', '')
                    salle_data['Etage'] = ScheduleParser.determine_floor(room_code)
                
                normalized_data.append(salle_data)
            
            logger.info(f"Parsé {len(normalized_data)} lignes depuis le fichier CSV")
            return normalized_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du fichier CSV: {e}")
            return []
    
    @staticmethod
    def parse_xlsx_file(filepath: str) -> List[Dict]:
        """Parse un fichier Excel et retourne les données des salles"""
        try:
            df = pd.read_excel(filepath)
            # Utiliser la même logique que pour CSV
            return ScheduleParser.parse_csv_file(filepath.replace('.xlsx', '.csv'))
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du fichier Excel: {e}")
            return []


def allowed_file(filename: str) -> bool:
    """Vérifie si l'extension du fichier est autorisée"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Page d'accueil avec interface de téléversement"""
    return render_template('index.html', data=current_schedule_data)


@app.route('/upload', methods=['POST'])
def upload_file():
    """Endpoint pour téléverser un fichier d'emploi du temps"""
    global current_schedule_data
    
    if 'file' not in request.files:
        flash('Aucun fichier sélectionné')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('Aucun fichier sélectionné')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Parser le fichier selon son extension
        file_extension = filename.rsplit('.', 1)[1].lower()
        
        try:
            if file_extension == 'ics':
                current_schedule_data = ScheduleParser.parse_ical_file(filepath)
            elif file_extension == 'csv':
                current_schedule_data = ScheduleParser.parse_csv_file(filepath)
            elif file_extension in ['xlsx', 'xls']:
                current_schedule_data = ScheduleParser.parse_xlsx_file(filepath)
            
            flash(f'Fichier téléversé avec succès! {len(current_schedule_data)} événements chargés.')
            logger.info(f"Fichier {filename} traité avec succès")
            
        except Exception as e:
            flash(f'Erreur lors du traitement du fichier: {str(e)}')
            logger.error(f"Erreur lors du traitement de {filename}: {e}")
        
        return redirect(url_for('index'))
    
    flash('Type de fichier non autorisé')
    return redirect(request.url)


@app.route("/api/salles/occupation")
def api_salles_occupation():
    """API REST - Récupération de l'état d'occupation des salles"""
    global current_schedule_data
    
    try:
        # Si pas de données chargées, essayer de charger le fichier par défaut
        if not current_schedule_data and os.path.exists(DEFAULT_ICAL_FILE):
            current_schedule_data = ScheduleParser.parse_ical_file(DEFAULT_ICAL_FILE)
        
        return jsonify(current_schedule_data)
    
    except Exception as e:
        logger.error(f"Erreur dans l'API salles/occupation: {e}")
        return jsonify({"error": "Erreur lors de la récupération des données"}), 500


@app.route("/api/stats")
def api_stats():
    """API REST - Statistiques sur les données chargées"""
    global current_schedule_data
    
    if not current_schedule_data:
        return jsonify({"message": "Aucune donnée chargée"})
    
    # Calculer quelques statistiques
    total_events = len(current_schedule_data)
    unique_rooms = len(set(item['NomSalle'] for item in current_schedule_data))
    floors = list(set(item['Etage'] for item in current_schedule_data))
    
    return jsonify({
        "total_events": total_events,
        "unique_rooms": unique_rooms,
        "floors": sorted(floors),
        "last_updated": datetime.now().isoformat()
    })


@app.route('/public/<path:filename>')
def serve_static(filename):
    """Servir les fichiers statiques du dossier public"""
    return send_from_directory('public', filename)


@app.errorhandler(404)
def not_found(error):
    """Gestionnaire d'erreur 404"""
    return jsonify({"error": "Endpoint non trouvé"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Gestionnaire d'erreur 500"""
    logger.error(f"Erreur interne: {error}")
    return jsonify({"error": "Erreur interne du serveur"}), 500


if __name__ == "__main__":
    logger.info("Démarrage de l'application PlanYnov...")
    app.run(debug=True, host='0.0.0.0', port=5001)
