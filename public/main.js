import * as THREE from 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.module.js';
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/jsm/controls/OrbitControls.js';

let scene, camera, renderer, controls;
let sceneContainer;
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

// Groupes pour les étages, pour faciliter l'affichage/masquage
const etageGroups = {
    0: new THREE.Group(),
    1: new THREE.Group(),
    2: new THREE.Group(),
    // Ajoutez plus d'étages si nécessaire
};
let allSallesGroup = new THREE.Group(); // Pour regrouper tous les étages

// Dimensions des salles et espacement
const salleWidth = 4;
const salleHeight = 2.5;
const salleDepth = 6;
const spacing = 2; // Espacement entre les salles
const etageHeight = 5; // Hauteur entre les niveaux d'étage

// Couleurs
const colorLibre = 0x4CAF50; // Vert
const colorOccupee = 0xF44336; // Rouge
const colorIndetermine = 0x9E9E9E; // Gris
const colorSelection = 0xFFEB3B; // Jaune pour la sélection (temporaire)

let INTERSECTED; // Pour garder la trace de l'objet intersecté/cliqué

function init() {
    sceneContainer = document.getElementById('scene-container');

    // Scène
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xeeeeee);

    // Caméra
    camera = new THREE.PerspectiveCamera(75, sceneContainer.clientWidth / sceneContainer.clientHeight, 0.1, 1000);
    camera.position.set(15, 20, 25); // Position initiale de la caméra

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(sceneContainer.clientWidth, sceneContainer.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    sceneContainer.appendChild(renderer.domElement);

    // Contrôles Orbitaux
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true; // Optionnel, pour un mouvement plus doux
    controls.dampingFactor = 0.05;
    controls.screenSpacePanning = false;
    controls.minDistance = 5;
    controls.maxDistance = 100;
    // controls.maxPolarAngle = Math.PI / 2; // Limite l'angle de vue pour ne pas aller sous le "sol"

    // Lumières
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(50, 50, 50);
    scene.add(directionalLight);

    // Ajouter les groupes d'étages à la scène principale (ou à allSallesGroup)
    for (const etageKey in etageGroups) {
        allSallesGroup.add(etageGroups[etageKey]);
    }
    scene.add(allSallesGroup);


    // Grille d'aide au sol (optionnel)
    const gridHelper = new THREE.GridHelper(100, 20);
    scene.add(gridHelper);

    // Gestion du redimensionnement de la fenêtre
    window.addEventListener('resize', onWindowResize, false);
    // Gestion des clics
    sceneContainer.addEventListener('click', onClick, false);

    animate();
    setupEtageControls();
    fetchAndDisplaySalles();
}

function onWindowResize() {
    camera.aspect = sceneContainer.clientWidth / sceneContainer.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(sceneContainer.clientWidth, sceneContainer.clientHeight);
}

function animate() {
    requestAnimationFrame(animate);
    controls.update(); // Seulement si enableDamping ou autoRotate est utilisé
    renderer.render(scene, camera);
}

// ---- LOGIQUE SPÉCIFIQUE À L'APPLICATION ----

async function fetchAndDisplaySalles() {
    try {
        const response = await fetch('http://localhost:5001/api/salles/occupation');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const dataSalles = await response.json();
        console.log("Données reçues:", dataSalles);
        processSallesData(dataSalles);
    } catch (error) {
        console.error("Erreur lors de la récupération des données des salles:", error);
        const infoPanel = document.getElementById('salle-info-content');
        infoPanel.innerHTML = `<p style="color: red;">Erreur de chargement des données des salles. Vérifiez que le backend est démarré et accessible.</p>`;
    }
}

function processSallesData(dataSalles) {
    // Nettoyer les groupes d'étages avant d'ajouter de nouveaux objets
    for (const key in etageGroups) {
        const group = etageGroups[key];
        while (group.children.length > 0) {
            group.remove(group.children[0]);
        }
    }
     // Vider aussi allSallesGroup si on ne recrée pas etageGroups à chaque fois
    while(allSallesGroup.children.length > 0) {
        const group = allSallesGroup.children[0];
        // Vider les sous-groupes (etageGroups) si nécessaire ou les recréer
        if (group instanceof THREE.Group) {
            while(group.children.length > 0) {
                group.remove(group.children[0]);
            }
        }
        allSallesGroup.remove(group);
    }
    // Ré-ajouter les groupes d'étages (potentiellement vides au début) à allSallesGroup
    for (const etageKey in etageGroups) {
        // Assurer que etageGroups[etageKey] est bien un THREE.Group vide
        etageGroups[etageKey] = new THREE.Group();
        allSallesGroup.add(etageGroups[etageKey]);
    }


    // Agréger les données par salle pour éviter les doublons de géométrie
    // On ne crée qu'un cube par NomSalle unique. L'état (occupé/libre) sera géré par la couleur.
    const sallesUniques = {};
    dataSalles.forEach(occupation => {
        if (!sallesUniques[occupation.NomSalle]) {
            sallesUniques[occupation.NomSalle] = {
                nom: occupation.NomSalle,
                etage: occupation.EtageDeduit,
                occupations: [] // On stockera toutes les occupations pour cette salle
            };
        }
        sallesUniques[occupation.NomSalle].occupations.push(occupation);
    });

    // Disposition simple en grille
    const sallesParRangee = 5;
    let compteurSalleParEtage = {}; // Pour compter les salles par étage: {0: 0, 1: 0, 2: 0}

    Object.values(sallesUniques).forEach(salle => {
        const etage = salle.etage;
        if (etageGroups[etage] === undefined) {
            console.warn(`Étage ${etage} non géré pour la salle ${salle.nom}. Création à la volée (non recommandé pour la prod).`);
            etageGroups[etage] = new THREE.Group();
            allSallesGroup.add(etageGroups[etage]); // S'assurer qu'il est dans la scène
        }

        if (compteurSalleParEtage[etage] === undefined) {
            compteurSalleParEtage[etage] = 0;
        }

        const x = (compteurSalleParEtage[etage] % sallesParRangee) * (salleWidth + spacing);
        const z = Math.floor(compteurSalleParEtage[etage] / sallesParRangee) * (salleDepth + spacing);
        const y = etage * etageHeight + (salleHeight / 2); // Positionner le centre du cube

        const geometry = new THREE.BoxGeometry(salleWidth, salleHeight, salleDepth);

        // Déterminer l'état actuel de la salle
        const etatActuel = getEtatSalle(salle.occupations);
        let materialColor = colorIndetermine;
        if (etatActuel.statut === "Libre") materialColor = colorLibre;
        else if (etatActuel.statut === "Occupée") materialColor = colorOccupee;

        const material = new THREE.MeshStandardMaterial({ color: materialColor });
        const cube = new THREE.Mesh(geometry, material);
        cube.position.set(x, y, z);

        // Stocker les informations de la salle dans l'objet
        cube.userData = {
            id: salle.nom,
            nomSalle: salle.nom,
            etage: salle.etage,
            occupations: salle.occupations, // Toutes les occupations pour cette salle
            etatActuel: etatActuel // Informations sur l'occupation actuelle
        };

        // Ajouter une étiquette de nom de salle (optionnel, peut impacter les perfs)
        const label = createSpriteLabel(salle.nom);
        label.position.set(x, y + salleHeight / 2 + 0.5, z); // Au-dessus du cube

        etageGroups[etage].add(cube);
        etageGroups[etage].add(label); // Ajouter l'étiquette au même groupe que la salle

        compteurSalleParEtage[etage]++;
    });

    // Afficher tous les étages par défaut après le chargement
    showEtage('all');
}

function getEtatSalle(occupations) {
    // Logique pour déterminer si la salle est actuellement occupée.
    // Pour l'instant, c'est simplifié. Il faudrait comparer avec la date et l'heure actuelle.
    const maintenant = new Date();
    // TODO: Améliorer la gestion des fuseaux horaires si nécessaire

    for (const occ of occupations) {
        // Supposition: occ.DateOccupation est YYYY-MM-DD, HeureDebut/Fin est HH:MM
        // Conversion basique, peut nécessiter une bibliothèque de dates pour la robustesse
        try {
            const [year, month, day] = occ.DateOccupation.split('-').map(Number);
            const [startHour, startMinute] = occ.HeureDebut.split(':').map(Number);
            const [endHour, endMinute] = occ.HeureFin.split(':').map(Number);

            const dateDebut = new Date(year, month - 1, day, startHour, startMinute);
            const dateFin = new Date(year, month - 1, day, endHour, endMinute);

            if (maintenant >= dateDebut && maintenant < dateFin) {
                return { statut: "Occupée", details: occ };
            }
        } catch (e) {
            console.error("Erreur de parsing date/heure pour l'occupation:", occ, e);
            // Peut retourner un état "erreur de données" si nécessaire
        }
    }
    return { statut: "Libre" };
}


function createSpriteLabel(text) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    const fontSize = 20; // Ajustez la taille de la police
    context.font = `Bold ${fontSize}px Arial`;

    // Mesurer le texte pour dimensionner le canvas
    const metrics = context.measureText(text);
    const textWidth = metrics.width;

    // Redimensionner le canvas pour s'adapter au texte
    // Il est souvent utile d'ajouter un peu de padding
    canvas.width = textWidth + 8; // padding horizontal
    canvas.height = fontSize + 8; // padding vertical + ajustement pour la ligne de base

    // Réappliquer la police après redimensionnement (certains navigateurs le nécessitent)
    context.font = `Bold ${fontSize}px Arial`;
    context.fillStyle = 'rgba(0, 0, 0, 0.7)'; // Couleur du fond du label (semi-transparent)
    context.fillRect(0, 0, canvas.width, canvas.height);

    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillStyle = 'white'; // Couleur du texte
    context.fillText(text, canvas.width / 2, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter; // Qualité de la texture
    texture.wrapS = THREE.ClampToEdgeWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;

    const spriteMaterial = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMaterial);

    // Dimensionner le sprite dans la scène 3D
    // La taille ici dépend de la taille de votre police et des dimensions du canvas
    // Vous devrez peut-être ajuster ces valeurs
    const labelScaleFactor = 0.1; // Facteur d'échelle global pour le sprite
    sprite.scale.set(canvas.width * labelScaleFactor * 0.05, canvas.height * labelScaleFactor * 0.05, 1.0);


    return sprite;
}


function setupEtageControls() {
    const buttons = document.querySelectorAll('#etage-controls button');
    buttons.forEach(button => {
        button.addEventListener('click', (event) => {
            const etageKey = event.target.dataset.etage;
            showEtage(etageKey);
            // Gérer la classe 'active' pour le style
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
        });
    });
    // Activer le bouton "Tous" par défaut
    document.querySelector('#etage-controls button[data-etage="all"]').classList.add('active');
}

function showEtage(etageKey) {
    if (etageKey === 'all') {
        for (const key in etageGroups) {
            etageGroups[key].visible = true;
        }
    } else {
        const etageNum = parseInt(etageKey, 10);
        for (const key in etageGroups) {
            etageGroups[key].visible = (parseInt(key, 10) === etageNum);
        }
    }
}

function onClick(event) {
    // Calculer la position de la souris en coordonnées normalisées (-1 à +1)
    mouse.x = (event.clientX / sceneContainer.clientWidth) * 2 - 1;
    // Attention: l'origine Y pour le raycaster est en bas, alors que pour clientX/Y c'est en haut
    mouse.y = -((event.clientY - sceneContainer.offsetTop) / sceneContainer.clientHeight) * 2 + 1;


    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(allSallesGroup.children, true); // true pour vérifier les descendants

    if (intersects.length > 0) {
        // Filtrer pour ne garder que les Mesh (cubes des salles), pas les Sprite (labels)
        const firstIntersectedObject = intersects.find(intersect => intersect.object instanceof THREE.Mesh);

        if (firstIntersectedObject) {
            if (INTERSECTED && INTERSECTED !== firstIntersectedObject.object) {
                // Rétablir la couleur d'origine de l'ancien objet sélectionné
                const previousUserData = INTERSECTED.userData;
                if (previousUserData && previousUserData.etatActuel) {
                     if (previousUserData.etatActuel.statut === "Libre") INTERSECTED.material.color.setHex(colorLibre);
                     else if (previousUserData.etatActuel.statut === "Occupée") INTERSECTED.material.color.setHex(colorOccupee);
                     else INTERSECTED.material.color.setHex(colorIndetermine);
                } else {
                    INTERSECTED.material.color.setHex(colorIndetermine); // Fallback
                }
            }

            INTERSECTED = firstIntersectedObject.object;
            INTERSECTED.material.color.setHex(colorSelection); // Couleur de sélection
            displaySalleInfo(INTERSECTED.userData);

        } else { // Clic dans le vide ou sur un label
            if (INTERSECTED) {
                // Rétablir la couleur d'origine
                const previousUserData = INTERSECTED.userData;
                if (previousUserData && previousUserData.etatActuel) {
                     if (previousUserData.etatActuel.statut === "Libre") INTERSECTED.material.color.setHex(colorLibre);
                     else if (previousUserData.etatActuel.statut === "Occupée") INTERSECTED.material.color.setHex(colorOccupee);
                     else INTERSECTED.material.color.setHex(colorIndetermine);
                } else {
                    INTERSECTED.material.color.setHex(colorIndetermine); // Fallback
                }
                INTERSECTED = null;
            }
            clearSalleInfo();
        }
    } else { // Clic dans le vide
        if (INTERSECTED) {
            // Rétablir la couleur d'origine
            const previousUserData = INTERSECTED.userData;
            if (previousUserData && previousUserData.etatActuel) {
                 if (previousUserData.etatActuel.statut === "Libre") INTERSECTED.material.color.setHex(colorLibre);
                 else if (previousUserData.etatActuel.statut === "Occupée") INTERSECTED.material.color.setHex(colorOccupee);
                 else INTERSECTED.material.color.setHex(colorIndetermine);
            } else {
                INTERSECTED.material.color.setHex(colorIndetermine); // Fallback
            }
            INTERSECTED = null;
        }
        clearSalleInfo();
    }
}

function displaySalleInfo(salleData) {
    const infoPanel = document.getElementById('salle-info-content');
    if (!salleData || !salleData.nomSalle) {
        infoPanel.innerHTML = "<p>Aucune information disponible pour cette salle.</p>";
        return;
    }

    let html = `<p><strong>Salle :</strong> ${salleData.nomSalle}</p>`;
    html += `<p><strong>Étage :</strong> ${salleData.etage}</p>`;

    const etat = getEtatSalle(salleData.occupations); // Ré-évaluer l'état au moment du clic si besoin
                                                      // ou utiliser salleData.etatActuel si mis à jour régulièrement

    html += `<p><strong>État actuel :</strong> <span class="${etat.statut.toLowerCase()}">${etat.statut}</span></p>`;

    if (etat.statut === "Occupée" && etat.details) {
        html += `<p><strong>Classe :</strong> ${etat.details.NomClasse || 'N/A'}</p>`;
        html += `<p><strong>Intervenant :</strong> ${etat.details.NomIntervenant || 'N/A'}</p>`;
        html += `<p><strong>Horaires :</strong> ${etat.details.HeureDebut} - ${etat.details.HeureFin} (le ${etat.details.DateOccupation})</p>`;
    }

    if (salleData.occupations && salleData.occupations.length > 0) {
        html += "<h3>Toutes les réservations pour cette salle :</h3><ul>";
        salleData.occupations.forEach(occ => {
            html += `<li>${occ.DateOccupation} (${occ.HeureDebut}-${occ.HeureFin}): ${occ.NomClasse} <i>(${occ.NomIntervenant || 'N/A'})</i></li>`;
        });
        html += "</ul>";
    } else {
        html += "<p>Aucune réservation enregistrée pour cette salle dans les données chargées.</p>";
    }

    infoPanel.innerHTML = html;
}

function clearSalleInfo() {
    const infoPanel = document.getElementById('salle-info-content');
    infoPanel.innerHTML = "<p>Cliquez sur une salle pour voir ses détails.</p>";
}


// Lancement de l'initialisation
init();
