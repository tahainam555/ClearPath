// Frontend JavaScript for ObstacleAware UI interactions and real-time updates.

// ============ GLOBAL STATE ============

// WebSocket connection object (initialized after script loads)
let socket = null;

// Mute state for audio alerts
let isMuted = false;

// Cooldown timer for text-to-speech to avoid rapid repeated alerts
let lastAlertTime = 0;
const ALERT_COOLDOWN_MS = 3000; // 3 seconds between spoken alerts

// Feature detection: check if browser supports Web Speech API
const speechSynthesisAvailable = 'speechSynthesis' in window;

// DOM element references (cached for performance)
const depthFeedElement = document.getElementById('depth-feed');
const alertTextElement = document.getElementById('alert-text');
const connectionStatusElement = document.getElementById('connection-status');
const muteButtonElement = document.getElementById('mute-btn');
const sensitivitySliderElement = document.getElementById('sensitivity');
const sensitivityValueElement = document.getElementById('sensitivity-value');

// Zone card elements (cached references)
const zoneCards = {
    left: document.getElementById('zone-left'),
    centre: document.getElementById('zone-centre'),
    right: document.getElementById('zone-right')
};


// ============ SOCKET.IO INITIALIZATION ============

/**
 * Initialize WebSocket connection to Flask-SocketIO server.
 * Called automatically when page loads.
 */
function initializeSocket() {
    // Connect to the server (uses current host/port by default)
    // io() reads from the socket.io.js client loaded in HTML
    socket = io();
    
    // ============ CONNECTION EVENTS ============
    
    /**
     * Handle successful WebSocket connection.
     * Updates UI to show "Connected ✅" status.
     */
    socket.on('connect', function() {
        console.log('[Socket.IO] Connected to server, sid:', socket.id);
        updateConnectionStatus(true);
    });
    
    /**
     * Handle WebSocket disconnection.
     * Updates UI to show "Disconnected ❌" status.
     */
    socket.on('disconnect', function() {
        console.log('[Socket.IO] Disconnected from server');
        updateConnectionStatus(false);
    });
    
    // ============ DATA EVENTS ============
    
    /**
     * Handle "depth_frame" event: receive and display live depth map.
     * 
     * Event payload: {image: "base64_jpeg_string"}
     */
    socket.on('depth_frame', function(data) {
        try {
            if (data.image) {
                // Convert base64 JPEG to data URL format for <img> tag
                const dataUrl = 'data:image/jpeg;base64,' + data.image;
                depthFeedElement.src = dataUrl;
            }
        } catch (error) {
            console.error('[Socket.IO] Error processing depth frame:', error);
        }
    });
    
    /**
     * Handle "zone_status" event: update zone cards and alert message.
     * 
     * Event payload: {
     *   zones: {left: "red"|"green", centre: "red"|"green", right: "red"|"green"},
     *   alert: "alert message" or null
     * }
     */
    socket.on('zone_status', function(data) {
        try {
            // Update zone cards if zones data is present
            if (data.zones) {
                updateZoneCards(data.zones);
            }
            
            // Update alert text and speak if enabled
            if (data.alert !== undefined) {
                updateAlertText(data.alert);
                
                // Trigger text-to-speech if: not muted, message exists, cooldown passed
                if (!isMuted && data.alert && speechSynthesisAvailable) {
                    const now = Date.now();
                    if (now - lastAlertTime >= ALERT_COOLDOWN_MS) {
                        speakAlert(data.alert);
                        lastAlertTime = now;
                    }
                }
            }
        } catch (error) {
            console.error('[Socket.IO] Error processing zone status:', error);
        }
    });
    
    /**
     * Handle generic connection errors.
     */
    socket.on('connect_error', function(error) {
        console.error('[Socket.IO] Connection error:', error);
        updateConnectionStatus(false);
    });
}


// ============ UI UPDATE FUNCTIONS ============

/**
 * Update connection status indicator.
 * 
 * @param {boolean} isConnected - True if connected, false if disconnected
 */
function updateConnectionStatus(isConnected) {
    if (isConnected) {
        connectionStatusElement.textContent = 'Connected ✅';
        connectionStatusElement.classList.remove('disconnected');
        connectionStatusElement.classList.add('connected');
    } else {
        connectionStatusElement.textContent = 'Disconnected ❌';
        connectionStatusElement.classList.remove('connected');
        connectionStatusElement.classList.add('disconnected');
    }
}

/**
 * Update zone card displays based on danger status.
 * 
 * Changes background color (red for danger, green for clear) and
 * updates status text (DANGER or CLEAR).
 * 
 * @param {Object} zones - {left: "red"|"green", centre: "red"|"green", right: "red"|"green"}
 */
function updateZoneCards(zones) {
    // Map zone names to their DOM elements and status text
    const zoneMapping = [
        { key: 'left', card: zoneCards.left },
        { key: 'centre', card: zoneCards.centre },
        { key: 'right', card: zoneCards.right }
    ];
    
    zoneMapping.forEach(({ key, card }) => {
        if (zones[key] !== undefined) {
            const isDanger = zones[key] === 'red';
            
            // Update background color class
            card.classList.toggle('danger', isDanger);
            
            // Update status text (DANGER or CLEAR)
            const statusElement = card.querySelector('.zone-status');
            if (statusElement) {
                statusElement.textContent = isDanger ? 'DANGER' : 'CLEAR';
            }
        }
    });
}

/**
 * Update the alert message display.
 * 
 * @param {string|null} alertMessage - Alert text or null for no alert
 */
function updateAlertText(alertMessage) {
    if (alertMessage) {
        // Display the alert message
        alertTextElement.textContent = alertMessage;
    } else {
        // Clear alert when no obstacles detected
        alertTextElement.textContent = 'Path clear — continue';
    }
}

/**
 * Speak an alert message using Web Speech API (Text-to-Speech).
 * 
 * Handles graceful fallback if speech synthesis is not available.
 * 
 * @param {string} message - Text to speak
 */
function speakAlert(message) {
    if (!speechSynthesisAvailable) {
        console.warn('[Speech] Web Speech API not available in this browser');
        return;
    }
    
    try {
        // Cancel any ongoing speech to avoid overlapping
        window.speechSynthesis.cancel();
        
        // Create utterance object
        const utterance = new SpeechSynthesisUtterance(message);
        
        // Configure speech parameters for accessibility
        utterance.rate = 1.0;      // Normal speaking speed
        utterance.pitch = 1.0;     // Normal pitch
        utterance.volume = 1.0;    // Full volume
        
        // Optional: select a voice if available
        const voices = window.speechSynthesis.getVoices();
        if (voices.length > 0) {
            // Prefer English voice; fallback to first available
            const englishVoice = voices.find(v => v.lang.startsWith('en')) || voices[0];
            utterance.voice = englishVoice;
        }
        
        // Log speech event for debugging
        utterance.onstart = () => console.log('[Speech] Started:', message);
        utterance.onend = () => console.log('[Speech] Finished');
        utterance.onerror = (event) => console.error('[Speech] Error:', event.error);
        
        // Speak the message
        window.speechSynthesis.speak(utterance);
    } catch (error) {
        console.error('[Speech] Failed to speak alert:', error);
    }
}


// ============ SENSITIVITY SLIDER HANDLER ============

/**
 * Handle sensitivity slider changes.
 * 
 * Sends the new threshold value to the backend /settings endpoint.
 * Updates the displayed value in real-time.
 */
function initializeSensitivitySlider() {
    // Update displayed value when slider moves
    sensitivitySliderElement.addEventListener('input', function(event) {
        const newValue = parseInt(event.target.value, 10);
        sensitivityValueElement.textContent = newValue;
        
        // Send new threshold to backend
        updateThreshold(newValue);
    });
}

/**
 * Send new depth threshold to server via POST /settings.
 * 
 * @param {number} thresholdValue - Depth threshold (0-255)
 */
function updateThreshold(thresholdValue) {
    fetch('/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            threshold: thresholdValue
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('[Settings] Threshold updated to:', thresholdValue);
    })
    .catch(error => {
        console.error('[Settings] Failed to update threshold:', error);
    });
}


// ============ MUTE BUTTON HANDLER ============

/**
 * Handle mute button clicks.
 * 
 * Toggles audio alert state and updates button appearance.
 * When muting, cancels any ongoing speech synthesis.
 */
function initializeMuteButton() {
    muteButtonElement.addEventListener('click', function() {
        // Toggle mute state
        isMuted = !isMuted;
        
        // Update button text and appearance
        if (isMuted) {
            muteButtonElement.textContent = '🔇 Unmuted';
            muteButtonElement.classList.add('muted');
            
            // Cancel any ongoing speech
            if (speechSynthesisAvailable) {
                window.speechSynthesis.cancel();
                console.log('[Mute] Audio alerts disabled, speech cancelled');
            }
        } else {
            muteButtonElement.textContent = '🔊 Mute';
            muteButtonElement.classList.remove('muted');
            console.log('[Mute] Audio alerts enabled');
        }
    });
}


// ============ PAGE INITIALIZATION ============

/**
 * Initialize all event listeners and connections when page loads.
 * Called when DOM content is fully loaded.
 */
function initializeApp() {
    console.log('[App] Initializing ObstacleAware frontend...');
    
    // Initialize WebSocket connection
    initializeSocket();
    
    // Initialize event listeners
    initializeSensitivitySlider();
    initializeMuteButton();
    
    // Log feature support
    if (speechSynthesisAvailable) {
        console.log('[App] Web Speech API available - audio alerts enabled');
    } else {
        console.warn('[App] Web Speech API not available - audio alerts disabled');
    }
    
    console.log('[App] Initialization complete');
}

// Wait for DOM to be fully loaded before initializing
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    // DOM already loaded (e.g., if script is deferred)
    initializeApp();
}
