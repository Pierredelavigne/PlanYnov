from flask import Flask, request, jsonify, render_template_string
import pandas as pd
import re
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Variable globale pour stocker les données d'occupation (simplifié pour l'instant)
occupancy_data = []

# Structure HTML pour l'upload et l'affichage simple
HTML_TEMPLATE = """
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-g">
  <title>Occupation des Salles</title>
  <style>
    body { font-family: sans-serif; margin: 20px; }
    h1, h2 { color: #333; }
    .container { max-width: 800px; margin: auto; background: #f9f9f9; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
    .upload-form { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 4px; }
    .file-input { margin-top: 5px; }
    .submit-btn { background-color: #4CAF50; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }
    .submit-btn:hover { background-color: #45a049; }
    .message { padding: 10px; margin-bottom: 15px; border-radius: 4px; }
    .success { background-color: #e7f3e7; color: #0f5132; border: 1px solid #badbcc; }
    .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }
    th { background-color: #f2f2f2; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Gestion de l'Occupation des Salles</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="message {{ category }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="upload-form">
      <h2>Télécharger un fichier d'occupation (CSV ou XLSX)</h2>
      <form method="post" enctype="multipart/form-data" action="/upload">
        <input type="file" name="file" class="file-input" accept=".csv, .xlsx">
        <input type="submit" value="Télécharger et Traiter" class="submit-btn">
      </form>
    </div>

    <h2>Données d'Occupation Actuelles</h2>
    {% if data %}
      <table>
        <thead>
          <tr>
            <th>Nom Salle</th>
            <th>Étage Déduit</th>
            <th>Date</th>
            <th>Début</th>
            <th>Fin</th>
            <th>Classe</th>
            <th>Intervenant</th>
          </tr>
        </thead>
        <tbody>
          {% for row in data %}
            <tr>
              <td>{{ row.NomSalle }}</td>
              <td>{{ row.EtageDeduit }}</td>
              <td>{{ row.DateOccupation }}</td>
              <td>{{ row.HeureDebut }}</td>
              <td>{{ row.HeureFin }}</td>
              <td>{{ row.NomClasse }}</td>
              <td>{{ row.NomIntervenant }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    {% else %}
      <p>Aucune donnée d'occupation chargée pour le moment.</p>
    {% endif %}
  </div>
</body>
</html>
"""

def parse_nom_salle_to_etage(nom_salle):
    """
    Déduit l'étage à partir du nom de la salle.
    Exemple: S001 -> 0, S101 -> 1, S205 -> 2.
    Recherche un nombre dans le nom, et prend le premier chiffre de ce nombre comme étage
    si ce nombre a une longueur typique (ex: 3 chiffres pour S101, mais aussi S01).
    """
    match = re.search(r'\d+', str(nom_salle))
    if match:
        salle_num_str = match.group(0)
        # Si le numéro est comme "001", "01", "1", etc. pour RDC
        # Si "101", "120", etc. pour 1er
        if salle_num_str.startswith('0') and len(salle_num_str) > 1 : # e.g. 01, 001, 010
            return 0
        elif len(salle_num_str) > 0: # e.g. 1, 10, 100, 200
            # On prend le premier chiffre du nombre trouvé comme indicateur d'étage
            # Ex: "101" -> etage 1, "201" -> etage 2, "01" (interpreté comme 1) -> etage 1
            # Pour "01", "001", etc. cela donnera 0 si le premier chiffre est 0.
            # Pour "S1", "S01", "S001"
            # "S1" -> etage_char = '1' -> 1
            # "S01" -> etage_char = '0' -> 0
            # "S001" -> etage_char = '0' -> 0
            # "S101" -> etage_char = '1' -> 1
            # "S205" -> etage_char = '2' -> 2
            etage_char = salle_num_str[0]
            return int(etage_char)
    return None # Non déterminé


@app.route('/', methods=['GET'])
def index():
    from flask import flash # Import flash here for use in the template context
    # Pour l'affichage simple, on passe les données directement au template.
    # Plus tard, la 3D consommera l'API /api/salles/occupation
    return render_template_string(HTML_TEMPLATE, data=occupancy_data, get_flashed_messages=flash)

@app.route('/upload', methods=['POST'])
def upload_file():
    global occupancy_data # Permet de modifier la variable globale
    from flask import flash, redirect, url_for

    if 'file' not in request.files:
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('index'))

    if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        try:
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)

            if file.filename.endswith('.csv'):
                df = pd.read_csv(filename)
            else:
                df = pd.read_excel(filename)

            # Validation des colonnes (exemple simple)
            expected_columns = ['NomSalle', 'DateOccupation', 'HeureDebut', 'HeureFin', 'NomClasse']
            # NomIntervenant est optionnel

            actual_columns = [col.strip() for col in df.columns]
            df.columns = actual_columns # Normaliser les noms de colonnes (enlever espaces)

            missing_cols = [col for col in expected_columns if col not in df.columns]
            if missing_cols:
                flash(f"Colonnes manquantes dans le fichier : {', '.join(missing_cols)}", 'error')
                return redirect(url_for('index'))

            # Traitement des données
            current_data = []
            for index, row in df.iterrows():
                nom_salle = row['NomSalle']
                etage = parse_nom_salle_to_etage(nom_salle)

                # Si l'étage n'a pas pu être déduit, on pourrait ignorer la ligne ou marquer comme erreur
                if etage is None:
                    app.logger.warning(f"Impossible de déduire l'étage pour la salle : {nom_salle}. Ligne ignorée.")
                    continue

                current_data.append({
                    'NomSalle': nom_salle,
                    'EtageDeduit': etage,
                    'DateOccupation': str(row['DateOccupation']), # Simplifié, idéalement parser en datetime
                    'HeureDebut': str(row['HeureDebut']),       # Simplifié
                    'HeureFin': str(row['HeureFin']),         # Simplifié
                    'NomClasse': row['NomClasse'],
                    'NomIntervenant': row.get('NomIntervenant', '') # Gérer si la colonne est absente ou vide
                })

            occupancy_data = current_data # Remplacer les anciennes données par les nouvelles
            flash('Fichier traité avec succès!', 'success')
            os.remove(filename) # Supprimer le fichier temporaire après traitement

        except Exception as e:
            app.logger.error(f"Erreur lors du traitement du fichier : {e}")
            flash(f'Erreur lors du traitement du fichier : {e}', 'error')
            if 'filename' in locals() and os.path.exists(filename):
                 os.remove(filename) # S'assurer de supprimer le fichier même en cas d'erreur de parsing

        return redirect(url_for('index'))

    else:
        flash('Type de fichier non autorisé. Veuillez utiliser un fichier CSV ou XLSX.', 'error')
        return redirect(url_for('index'))

@app.route('/api/salles/occupation', methods=['GET'])
def get_occupation_data():
    # Pour l'instant, retourne toutes les données.
    # On pourrait ajouter des filtres (date, heure) ici.
    # Exemple: /api/salles/occupation?date=2023-10-27
    # date_filter = request.args.get('date')
    # filtered_data = occupancy_data
    # if date_filter:
    #    filtered_data = [d for d in occupancy_data if d['DateOccupation'] == date_filter]
    # return jsonify(filtered_data)
    return jsonify(occupancy_data)

if __name__ == '__main__':
    app.secret_key = 'supersecretkey' # Nécessaire pour flash messages
    app.run(debug=True)
</tbody>
</table>
{% else %}
<p>Aucune donnée d'occupation chargée pour le moment.</p>
{% endif %}
</div>
</body>
</html>
"""

def parse_nom_salle_to_etage(nom_salle):
    """
    Déduit l'étage à partir du nom de la salle.
    Règle: Le premier chiffre d'un nombre trouvé dans le nom de la salle indique l'étage.
    Ex: S001 -> 0, S101 -> 1, S205 -> 2, Amphi0 -> 0.
    """
    # Convertir en str pour s'assurer que c'est bien une chaîne (si pandas lit un nombre pur)
    nom_salle_str = str(nom_salle)

    # Recherche une séquence de chiffres dans le nom de la salle
    match = re.search(r'\d+', nom_salle_str)

    if match:
        # Extrait la première séquence de chiffres trouvée
        numero_str = match.group(0)

        # Le premier chiffre de cette séquence est l'étage
        # Ex: "001" -> '0' -> 0
        # Ex: "101" -> '1' -> 1
        # Ex: "S20" -> '2' -> 2
        # Ex: "Amphi0" -> '0' -> 0
        if numero_str: # S'assure que la chaîne n'est pas vide
            return int(numero_str[0])

    # Si aucun chiffre n'est trouvé, ou si le nom est mal formé
    app.logger.warning(f"Impossible de déduire l'étage pour : {nom_salle_str}. Aucun format numérique attendu trouvé.")
    return None


@app.route('/', methods=['GET'])
def index():
    from flask import session # Import session pour flash
    # Flash messages are typically handled by render_template if configured correctly
    # For render_template_string, we might need to pass get_flashed_messages manually if not using sessions
    # For simplicity, let's assume flash is available in the template context or use a basic message passing

    # A simple way to pass messages without full flash setup for render_template_string
    message = request.args.get('message', None)
    category = request.args.get('category', None)

    # The 'get_flashed_messages' function needs to be available in the template context.
    # Flask's `flash` stores messages in the session, which `get_flashed_messages` retrieves.
    # To make it work with `render_template_string` without a full app context for requests,
    # it's simpler to pass data directly.

    # We will use Flask's built-in flash mechanism, which requires a secret_key for the session.
    # The `get_flashed_messages` function will be available in the template context
    # when `render_template` or `render_template_string` is called from a request context.
    return render_template_string(HTML_TEMPLATE, data=occupancy_data) # flash messages handled by Flask via session

@app.route('/upload', methods=['POST'])
def upload_file():
    global occupancy_data
    from flask import flash, redirect, url_for

    if 'file' not in request.files:
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('index'))

    if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        temp_filepath = None
        try:
            # Sauvegarde sécurisée du fichier
            _, file_extension = os.path.splitext(file.filename)
            # Crée un nom de fichier temporaire sécurisé pour éviter les conflits et les injections de chemin
            import tempfile
            temp_dir = app.config.get('UPLOAD_FOLDER', 'uploads') # Utilise UPLOAD_FOLDER ou 'uploads' par défaut
            os.makedirs(temp_dir, exist_ok=True) # S'assure que le dossier existe

            # Utilise tempfile pour créer un fichier temporaire de manière sécurisée
            temp_fd, temp_filepath = tempfile.mkstemp(suffix=file_extension, dir=temp_dir)
            with os.fdopen(temp_fd, 'wb') as tmp: # Ouvre le fichier temporaire en binaire pour l'écriture
                file.save(tmp) # Sauvegarde le contenu du fichier uploadé dans le fichier temporaire

            if file.filename.endswith('.csv'):
                df = pd.read_csv(temp_filepath)
            else: # .xlsx
                df = pd.read_excel(temp_filepath)

            expected_columns = ['NomSalle', 'DateOccupation', 'HeureDebut', 'HeureFin', 'NomClasse']
            actual_columns = [col.strip() for col in df.columns]
            df.columns = actual_columns

            missing_cols = [col for col in expected_columns if col not in df.columns]
            if missing_cols:
                flash(f"Colonnes manquantes obligatoires : {', '.join(missing_cols)}. Les colonnes attendues sont: NomSalle, DateOccupation, HeureDebut, HeureFin, NomClasse. 'NomIntervenant' est optionnel.", 'error')
                return redirect(url_for('index'))

            processed_data = []
            for index, row in df.iterrows():
                nom_salle = row.get('NomSalle')
                if pd.isna(nom_salle): # Vérifie si NomSalle est NaN ou vide
                    app.logger.warning(f"Ligne {index+2}: NomSalle manquant. Ligne ignorée.")
                    continue # Ignore les lignes où NomSalle est vide

                etage = parse_nom_salle_to_etage(nom_salle)
                if etage is None:
                    app.logger.warning(f"Ligne {index+2} (Salle: {nom_salle}): Impossible de déduire l'étage. Ligne ignorée.")
                    continue

                # Vérification des autres champs obligatoires
                required_fields_for_row = {
                    'DateOccupation': row.get('DateOccupation'),
                    'HeureDebut': row.get('HeureDebut'),
                    'HeureFin': row.get('HeureFin'),
                    'NomClasse': row.get('NomClasse')
                }

                empty_fields = [k for k, v in required_fields_for_row.items() if pd.isna(v)]
                if empty_fields:
                    app.logger.warning(f"Ligne {index+2} (Salle: {nom_salle}): Champs obligatoires manquants ou vides: {', '.join(empty_fields)}. Ligne ignorée.")
                    continue

                # Conversion en chaîne pour l'affichage (simplifié)
                # Une conversion et validation plus robustes des dates/heures seraient nécessaires pour la logique de "Libre/Occupée"
                processed_data.append({
                    'NomSalle': str(nom_salle),
                    'EtageDeduit': etage,
                    'DateOccupation': str(required_fields_for_row['DateOccupation']).split(' ')[0], # Garde la partie date si datetime
                    'HeureDebut': str(required_fields_for_row['HeureDebut']),
                    'HeureFin': str(required_fields_for_row['HeureFin']),
                    'NomClasse': str(required_fields_for_row['NomClasse']),
                    'NomIntervenant': str(row.get('NomIntervenant', '')) if pd.notna(row.get('NomIntervenant')) else ''
                })

            occupancy_data = processed_data
            flash(f'{len(processed_data)} lignes traitées avec succès!', 'success')

        except Exception as e:
            app.logger.error(f"Erreur lors du traitement du fichier : {e}", exc_info=True)
            flash(f'Erreur technique lors du traitement du fichier : {str(e)}', 'error')
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath) # Nettoie le fichier temporaire

        return redirect(url_for('index'))
    else:
        flash('Type de fichier non autorisé. Veuillez utiliser un fichier CSV ou XLSX.', 'error')
        return redirect(url_for('index'))

@app.route('/api/salles/occupation', methods=['GET'])
def get_occupation_data():
    # Ici, on pourrait ajouter la logique pour déterminer si une salle est "actuellement" occupée
    # basé sur la date et l'heure courante, et les données chargées.
    # Pour l'instant, on retourne toutes les données chargées.
    # Le client (frontend 3D) devra interpréter ces données.

    # Exemple de ce que le frontend pourrait recevoir :
    # Une liste de toutes les salles uniques avec leur état actuel.
    # Ou, une liste de toutes les réservations.
    # Pour l'instant, on renvoie les données brutes traitées.
    return jsonify(occupancy_data)

if __name__ == '__main__':
    app.secret_key = os.urandom(24) # Clé secrète pour les sessions flash
    app.run(debug=True, port=5001) # Utilise un port différent de celui par défaut si nécessaire
</tbody>
</table>
{% else %}
<p>Aucune donnée d'occupation chargée pour le moment.</p>
{% endif %}
</div>
</body>
</html>
"""

def parse_nom_salle_to_etage(nom_salle):
    """
    Déduit l'étage à partir du nom de la salle.
    Règle: Le premier chiffre d'un nombre trouvé dans le nom de la salle indique l'étage.
    Ex: S001 -> 0, S101 -> 1, S205 -> 2, Amphi0 -> 0.
    """
    nom_salle_str = str(nom_salle)
    match = re.search(r'\d+', nom_salle_str)
    if match:
        numero_str = match.group(0)
        if numero_str:
            return int(numero_str[0])
    app.logger.warning(f"Impossible de déduire l'étage pour : {nom_salle_str}.")
    return None


@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE, data=occupancy_data)

@app.route('/upload', methods=['POST'])
def upload_file():
    global occupancy_data
    from flask import flash, redirect, url_for

    if 'file' not in request.files:
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('Aucun fichier sélectionné', 'error')
        return redirect(url_for('index'))

    if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        temp_filepath = None
        try:
            _, file_extension = os.path.splitext(file.filename)
            temp_dir = app.config.get('UPLOAD_FOLDER', 'uploads')
            os.makedirs(temp_dir, exist_ok=True)
            temp_fd, temp_filepath = tempfile.mkstemp(suffix=file_extension, dir=temp_dir)

            with os.fdopen(temp_fd, 'wb') as tmp:
                file.save(tmp)

            if file.filename.endswith('.csv'):
                df = pd.read_csv(temp_filepath, dtype=str) # Lire toutes les colonnes comme str au début
            else:
                df = pd.read_excel(temp_filepath, dtype=str) # Lire toutes les colonnes comme str

            df.columns = [col.strip() for col in df.columns] # Normaliser les noms de colonnes

            expected_columns = ['NomSalle', 'DateOccupation', 'HeureDebut', 'HeureFin', 'NomClasse']
            missing_cols = [col for col in expected_columns if col not in df.columns]
            if missing_cols:
                flash(f"Colonnes manquantes obligatoires : {', '.join(missing_cols)}. Les colonnes attendues sont: NomSalle, DateOccupation, HeureDebut, HeureFin, NomClasse. 'NomIntervenant' est optionnel.", 'error')
                return redirect(url_for('index'))

            processed_data = []
            for index, row in df.iterrows():
                nom_salle = row.get('NomSalle')
                if pd.isna(nom_salle) or str(nom_salle).strip() == "":
                    app.logger.warning(f"Ligne {index+2}: NomSalle manquant ou vide. Ligne ignorée.")
                    continue

                etage = parse_nom_salle_to_etage(nom_salle)
                if etage is None:
                    app.logger.warning(f"Ligne {index+2} (Salle: {nom_salle}): Impossible de déduire l'étage. Ligne ignorée.")
                    continue

                required_fields_for_row = {
                    'DateOccupation': row.get('DateOccupation'),
                    'HeureDebut': row.get('HeureDebut'),
                    'HeureFin': row.get('HeureFin'),
                    'NomClasse': row.get('NomClasse')
                }

                empty_or_nan_fields = {k: v for k, v in required_fields_for_row.items() if pd.isna(v) or str(v).strip() == ""}
                if empty_or_nan_fields:
                    app.logger.warning(f"Ligne {index+2} (Salle: {nom_salle}): Champs obligatoires manquants ou vides: {', '.join(empty_or_nan_fields.keys())}. Ligne ignorée.")
                    continue

                processed_data.append({
                    'NomSalle': str(nom_salle),
                    'EtageDeduit': etage,
                    'DateOccupation': str(required_fields_for_row['DateOccupation']).split(' ')[0],
                    'HeureDebut': str(required_fields_for_row['HeureDebut']),
                    'HeureFin': str(required_fields_for_row['HeureFin']),
                    'NomClasse': str(required_fields_for_row['NomClasse']),
                    'NomIntervenant': str(row.get('NomIntervenant', '')) if pd.notna(row.get('NomIntervenant')) else ''
                })

            occupancy_data = processed_data
            flash(f'{len(processed_data)} lignes traitées avec succès! {len(df) - len(processed_data)} lignes ignorées.', 'success')

        except Exception as e:
            app.logger.error(f"Erreur lors du traitement du fichier : {e}", exc_info=True)
            flash(f'Erreur technique lors du traitement du fichier : {str(e)}', 'error')
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except OSError as e_rm:
                    app.logger.error(f"Erreur lors de la suppression du fichier temporaire {temp_filepath}: {e_rm}")

        return redirect(url_for('index'))
    else:
        flash('Type de fichier non autorisé. Veuillez utiliser un fichier CSV ou XLSX.', 'error')
        return redirect(url_for('index'))

@app.route('/api/salles/occupation', methods=['GET'])
def get_occupation_data():
    return jsonify(occupancy_data)

if __name__ == '__main__':
    app.secret_key = os.urandom(24)
    app.run(debug=True, port=5001)
