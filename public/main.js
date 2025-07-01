/**
 * Configuration constants for the 3D scene
 */
const SCENE_CONFIG = {
  CAMERA: {
    FOV: 75,
    NEAR: 0.1,
    FAR: 1000,
    POSITION: { x: 0, y: 30, z: 60 }
  },
  LIGHTING: {
    COLOR: 0xffffff,
    INTENSITY: 1,
    POSITION: { x: 50, y: 50, z: 50 }
  },
  ROOM: {
    GEOMETRY: { width: 4, height: 2, depth: 4 },
    COLORS: {
      OCCUPIED: 0xff4444,
      FREE: 0x44ff44
    },
    SPACING: 6
  },
  BACKGROUND_COLOR: 0x111111,
  API_ENDPOINT: "http://localhost:5001/api/salles/occupation"
};

/**
 * Utility class for time operations
 */
class TimeUtils {
  static getCurrentTime() {
    return new Date().toTimeString().slice(0, 5);
  }

  static getCurrentDate() {
    return new Date().toISOString().split("T")[0];
  }

  static isTimeInRange(currentTime, startTime, endTime) {
    return currentTime >= startTime && currentTime <= endTime;
  }
}

/**
 * Class to handle room data and visualization
 */
class RoomManager {
  constructor(scene, THREE) {
    this.scene = scene;
    this.THREE = THREE;
    this.cubes = [];
  }

  /**
   * Clear all existing room cubes from the scene
   */
  clearRooms() {
    this.cubes.forEach(cube => this.scene.remove(cube));
    this.cubes = [];
  }

  /**
   * Check if a room is currently occupied
   */
  isRoomOccupied(room) {
    const currentTime = TimeUtils.getCurrentTime();
    const currentDate = TimeUtils.getCurrentDate();
    
    return room.DateOccupation === currentDate &&
           TimeUtils.isTimeInRange(currentTime, room.HeureDebut, room.HeureFin);
  }

  /**
   * Create a 3D cube for a room
   */
  createRoomCube(room, index) {
    const isOccupied = this.isRoomOccupied(room);
    const color = isOccupied ? SCENE_CONFIG.ROOM.COLORS.OCCUPIED : SCENE_CONFIG.ROOM.COLORS.FREE;

    const geometry = new this.THREE.BoxGeometry(
      SCENE_CONFIG.ROOM.GEOMETRY.width,
      SCENE_CONFIG.ROOM.GEOMETRY.height,
      SCENE_CONFIG.ROOM.GEOMETRY.depth
    );
    const material = new this.THREE.MeshPhongMaterial({ color });
    const cube = new this.THREE.Mesh(geometry, material);

    // Position the cube based on index and floor
    cube.position.set(
      index * SCENE_CONFIG.ROOM.SPACING,
      room.Etage * SCENE_CONFIG.ROOM.SPACING,
      0
    );

    cube.userData = room;
    cube.callback = () => this.showRoomInfo(room);

    return cube;
  }

  /**
   * Display room information in a better format
   */
  showRoomInfo(room) {
    const infoPanel = document.getElementById('info-panel');
    const roomDetails = document.getElementById('room-details');
    
    if (infoPanel && roomDetails) {
      roomDetails.innerHTML = `
        <div style="margin-bottom: 10px;"><strong>Salle :</strong> ${room.NomSalle}</div>
        <div style="margin-bottom: 10px;"><strong>Étage :</strong> ${room.Etage}</div>
        <div style="margin-bottom: 10px;"><strong>Cours :</strong> ${room.NomClasse}</div>
        <div style="margin-bottom: 10px;"><strong>Intervenant :</strong> ${room.NomIntervenant}</div>
        <div style="margin-bottom: 10px;"><strong>Horaires :</strong> ${room.HeureDebut} - ${room.HeureFin}</div>
        <div><strong>Date :</strong> ${room.DateOccupation}</div>
      `;
      infoPanel.style.display = 'block';
    } else {
      // Fallback vers alert si les éléments DOM ne sont pas disponibles
      const info = [
        `Salle : ${room.NomSalle}`,
        `Cours : ${room.NomClasse}`,
        `Intervenant : ${room.NomIntervenant}`,
        `De ${room.HeureDebut} à ${room.HeureFin}`
      ].join('\n');
      
      alert(info);
    }
  }

  /**
   * Render all rooms in the scene
   */
  renderRooms(roomsData) {
    this.clearRooms();

    roomsData.forEach((room, index) => {
      const cube = this.createRoomCube(room, index);
      this.cubes.push(cube);
      this.scene.add(cube);
    });
  }

  /**
   * Show only rooms on a specific floor
   */
  showFloor(floor) {
    this.cubes.forEach(cube => {
      cube.visible = cube.userData.Etage === floor;
    });
  }

  /**
   * Show all rooms
   */
  showAll() {
    this.cubes.forEach(cube => {
      cube.visible = true;
    });
  }

  /**
   * Get all room cubes for interaction
   */
  getAllCubes() {
    return this.cubes;
  }
}

/**
 * Class to handle scene setup and management
 */
class SceneManager {
  constructor(THREE, OrbitControls) {
    this.THREE = THREE;
    this.scene = this.createScene();
    this.camera = this.createCamera();
    this.renderer = this.createRenderer();
    this.controls = this.createControls(OrbitControls);
    this.roomManager = new RoomManager(this.scene, THREE);
    
    this.setupLighting();
    this.setupEventListeners();
    this.animate();
  }

  /**
   * Create and configure the 3D scene
   */
  createScene() {
    const scene = new this.THREE.Scene();
    scene.background = new this.THREE.Color(SCENE_CONFIG.BACKGROUND_COLOR);
    return scene;
  }

  /**
   * Create and configure the camera
   */
  createCamera() {
    const camera = new this.THREE.PerspectiveCamera(
      SCENE_CONFIG.CAMERA.FOV,
      window.innerWidth / window.innerHeight,
      SCENE_CONFIG.CAMERA.NEAR,
      SCENE_CONFIG.CAMERA.FAR
    );
    
    camera.position.set(
      SCENE_CONFIG.CAMERA.POSITION.x,
      SCENE_CONFIG.CAMERA.POSITION.y,
      SCENE_CONFIG.CAMERA.POSITION.z
    );
    
    return camera;
  }

  /**
   * Create and configure the renderer
   */
  createRenderer() {
    const renderer = new this.THREE.WebGLRenderer({ 
      canvas: document.getElementById("scene") 
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    return renderer;
  }

  /**
   * Create and configure orbit controls
   */
  createControls(OrbitControls) {
    const controls = new OrbitControls(this.camera, this.renderer.domElement);
    controls.enableDamping = true;
    return controls;
  }

  /**
   * Setup scene lighting
   */
  setupLighting() {
    const light = new this.THREE.PointLight(
      SCENE_CONFIG.LIGHTING.COLOR,
      SCENE_CONFIG.LIGHTING.INTENSITY
    );
    
    light.position.set(
      SCENE_CONFIG.LIGHTING.POSITION.x,
      SCENE_CONFIG.LIGHTING.POSITION.y,
      SCENE_CONFIG.LIGHTING.POSITION.z
    );
    
    this.scene.add(light);
  }

  /**
   * Setup event listeners for user interaction
   */
  setupEventListeners() {
    window.addEventListener("click", (event) => {
      this.handleClick(event);
    });

    window.addEventListener("resize", () => {
      this.handleResize();
    });
  }

  /**
   * Handle click events on the scene
   */
  handleClick(event) {
    const mouse = new this.THREE.Vector2(
      (event.clientX / window.innerWidth) * 2 - 1,
      -(event.clientY / window.innerHeight) * 2 + 1
    );

    const raycaster = new this.THREE.Raycaster();
    raycaster.setFromCamera(mouse, this.camera);
    
    const intersects = raycaster.intersectObjects(this.roomManager.getAllCubes());
    
    if (intersects.length > 0 && intersects[0].object.callback) {
      intersects[0].object.callback();
    }
  }

  /**
   * Handle window resize events
   */
  handleResize() {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight);
  }

  /**
   * Animation loop
   */
  animate() {
    requestAnimationFrame(() => this.animate());
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  /**
   * Load room data from API
   */
  async loadData() {
    try {
      const response = await fetch(SCENE_CONFIG.API_ENDPOINT);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      this.roomManager.renderRooms(data);
    } catch (error) {
      console.error("Erreur de chargement des données :", error);
      // You could add a user-friendly error message here
    }
  }

  /**
   * Show rooms on a specific floor
   */
  showFloor(floor) {
    this.roomManager.showFloor(floor);
  }

  /**
   * Show all rooms
   */
  showAll() {
    this.roomManager.showAll();
  }
}

/**
 * Initialize the 3D scene
 */
function initScene(THREE, OrbitControls) {
  const sceneManager = new SceneManager(THREE, OrbitControls);
  
  // Load initial data
  sceneManager.loadData();
  
  // Return the scene manager instance for external control
  return sceneManager;
}

// Export pour compatibilité module
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { initScene };
}

// Export pour import ES6
if (typeof window !== 'undefined') {
  window.initScene = initScene;
}
