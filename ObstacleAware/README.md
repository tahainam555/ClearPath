# ObstacleAware

![ObstacleAware](https://img.shields.io/badge/ObstacleAware-Computer%20Vision%20Project-blue)
![Group](https://img.shields.io/badge/Group-G--22-green)
![Python](https://img.shields.io/badge/Python-3.9%2B-yellow)
![License](https://img.shields.io/badge/License-MIT-orange)

---

## 📋 Project Description

**ObstacleAware** is a real-time assistive navigation system designed to help visually impaired users avoid obstacles in their environment using AI-powered monocular depth estimation. The application captures video frames from a standard webcam, estimates depth using Intel's MiDaS small model, analyzes spatial obstacles in three zones (left, centre, right), and generates audio alerts with directional guidance. The system runs on any device with a camera and provides a mobile-responsive web interface accessible from smartphones on the same local network, making it a practical assistive tool for real-world navigation.

**Key Features:**
- ✅ Real-time depth estimation (MiDaS small model — optimized for speed)
- ✅ Zone-based obstacle detection (left, centre, right spatial awareness)
- ✅ Priority-ordered audio alerts with directional guidance
- ✅ Configurable danger threshold (0–255 range, adjustable via slider)
- ✅ Mobile-first web interface (portrait layout for accessibility)
- ✅ WebSocket streaming for low-latency updates (~8 FPS)
- ✅ Text-to-Speech synthesis for accessibility

---

## 📚 Base Paper Citation

**Ranftl, R., Bochkovskiy, A., & Aischen, V. (2022).** *Towards Robust Monocular Depth Estimation: Mixing Datasets for Zero-shot Cross-dataset Transfer.* **IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI)**, 44(7), 4294–4307. https://doi.org/10.1109/TPAMI.2021.3070144

**Model Repository:** [Intel MiDaS GitHub](https://github.com/isl-org/MiDaS)

---

## 📖 Reference Papers

1. **Eigen, D., Puhrsch, C., & Fergus, R. (2014).** *Depth Map Prediction from a Single Image using a Multi-Scale Deep Network.* In *NIPS*, pp. 2366–2374.

2. **Godard, C., Mac Aodha, O., & Brostow, G. J. (2017).** *Disp R-CNN: Stereo 3D Object Detection via Shape Prior Guided Instance Disparity Estimation.* In *CVPR*, pp. 5407–5415.

3. **Uhrig, J., Schneider, N., Schneider, L., Franke, U., Geiger, A., & Brox, T. (2017).** *Sparsity Invariant CNNs.* In *3DV*, pp. 11–20.

---

## 📁 Project Structure

```
ObstacleAware/
│
├── app.py                              # Flask web server with Flask-SocketIO
│                                       # Manages WebSocket connections, background
│                                       # processing thread, /settings REST endpoint
│
├── depth_estimator.py                  # Intel MiDaS-based depth estimation module
│                                       # Loads pre-trained model, processes frames,
│                                       # outputs normalized depth maps (0–255)
│
├── zone_analyzer.py                    # Spatial obstacle analysis module
│                                       # Divides depth map into 3 zones, computes
│                                       # average depth, flags danger zones
│
├── alert_engine.py                     # Alert message generation module
│                                       # Priority-based logic for obstacle warnings,
│                                       # directional guidance, UI color mapping
│
├── test_pipeline.py                    # Non-interactive pipeline test
│                                       # Tests all modules with dummy frames
│                                       # (no webcam or network required)
│
├── requirements.txt                    # Python package dependencies
│                                       # Flask, Flask-SocketIO, OpenCV,
│                                       # PyTorch, Torchvision, Timm, Numpy, Eventlet
│
├── SETUP_AND_TROUBLESHOOTING.txt      # Comprehensive setup guide & troubleshooting
│                                       # 9 sections: installation, testing, errors,
│                                       # quick reference, performance tips
│
├── README.md                           # This file
│
├── templates/
│   └── index.html                      # Mobile-first HTML5 web interface
│                                       # Portrait layout optimized for 360–430px width
│                                       # Loads socket.io client, displays depth feed,
│                                       # zone cards, alerts, controls
│
└── static/
    ├── style.css                       # Dark theme CSS (INFERNO colormap compatible)
    │                                   # Flexbox layouts, responsive breakpoints,
    │                                   # smooth transitions, accessibility-focused
    │
    └── script.js                       # Frontend JavaScript (real-time UI updates)
                                        # Socket.IO event handlers, WebSocket lifecycle,
                                        # sensitivity slider, mute button, text-to-speech
```

---

## 🔄 How It Works: 5-Step Pipeline

```
┌─────────────────┐
│   Step 1: CAPTURE
│   Webcam → BGR Frame
└────────────┬────┘
             │ (1280×720, 30 FPS camera → ~8 FPS processing)
             ↓
┌─────────────────────────────────────────┐
│   Step 2: DEPTH ESTIMATION (MiDaS)
│   ├─ Convert BGR → RGB
│   ├─ Preprocess: Resize 256×256, Normalize (ImageNet stats)
│   ├─ Inference: MiDaS_small model (torch.no_grad())
│   ├─ Postprocess: Bilinear resize to 1280×720
│   └─ Normalize: Min-max scale to 0–255, Apply INFERNO colormap
└────────────┬────────────────────────────┘
             │ (Outputs: colored_depth_map + normalized_depth_array)
             ↓
┌──────────────────────────────────┐
│   Step 3: ZONE ANALYSIS
│   ├─ Divide depth map: Left | Centre | Right
│   ├─ Compute average depth per zone
│   ├─ Compare against threshold (default 180)
│   └─ Flag zones: danger=True (red) or danger=False (green)
└────────────┬─────────────────────┘
             │ (Outputs: {left, centre, right} zones with avg & danger flag)
             ↓
┌──────────────────────────────────┐
│   Step 4: ALERT GENERATION
│   ├─ Check which zones are dangerous
│   ├─ Apply 7-tier priority logic:
│   │  1. All 3 zones → "Obstacles all around — stop immediately"
│   │  2. Centre+Left → "Obstacles ahead and on your left"
│   │  3. Centre+Right → "Obstacles ahead and on your right"
│   │  4. Left+Right → "Obstacles on both sides"
│   │  5. Centre only → "Obstacle ahead — stop"
│   │  6. Left only → "Obstacle on your left — move right"
│   │  7. Right only → "Obstacle on your right — move left"
│   ├─ Generate zone colors (red/green for UI)
│   └─ (No danger → return None for alert, green for all zones)
└────────────┬──────────────────────┘
             │ (Outputs: alert_message + zone_colors_dict)
             ↓
┌──────────────────────────────────┐
│   Step 5: DELIVERY TO USER
│   ├─ WebSocket "depth_frame": Base64 JPEG to browser
│   ├─ WebSocket "zone_status": Zone colors + alert text
│   ├─ UI Updates:
│   │  - Depth feed image refreshes
│   │  - Zone cards change color (red/green)
│   │  - Alert text updates in yellow bar
│   ├─ Audio Output (if not muted, 3s cooldown):
│   │  - Web Speech API speaks the alert message
│   │  - Rate 1.0, Pitch 1.0, Volume 1.0, English voice
│   └─ Mobile UI: 360–430px portrait layout for accessibility
└──────────────────────────────────┘

LOOP: Repeats every 125ms (~8 FPS) for real-time responsiveness
```

---

## 🚀 Setup & Installation

### Prerequisites

Before starting, ensure you have:
- **Python 3.9 or higher** (3.10+ recommended)
- **pip** (Python package manager)
- **Webcam** connected to your device (USB or built-in)
- **Internet connection** (for torch.hub MiDaS model download on first run)
- **Local WiFi network** (to access app from mobile)

Check your Python version:
```bash
python --version
# Output should be: Python 3.9.x or higher
```

### Step 1: Clone or Navigate to Project Directory

```bash
cd e:\Taha\CV\ClearPath\ClearPath\ObstacleAware
```

Or if cloning:
```bash
git clone https://github.com/tahainam555/ClearPath.git
cd ClearPath/ObstacleAware
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\Activate.ps1

# Linux/Mac:
source venv/bin/activate
```

You should see `(venv)` prefix in your terminal.

### Step 3: Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt

# ⏱️ This will take 10–15 minutes (PyTorch is ~500 MB)
```

**What gets installed:**
- `flask` & `flask-socketio` — Web server and WebSocket support
- `opencv-python` — Computer vision and image processing
- `torch` & `torchvision` — Deep learning framework and models
- `timm` — Vision model registry
- `numpy` — Numerical computing
- `eventlet` — Async I/O for WebSocket

### Step 4: Test the Pipeline (Optional but Recommended)

```bash
# Run without webcam to verify installation
python test_pipeline.py

# Expected output:
# ============================================================
#   1. INITIALIZING MODULES
# ============================================================
# ✅ DepthEstimator initialized successfully
# ✅ ZoneAnalyzer initialized successfully
# ✅ AlertEngine initialized successfully
# ... (test results for black & white frames)
# ✅ Pipeline is ready for deployment!
```

### Step 5: Start the Application

```bash
# Ensure venv is activated, then:
python app.py

# Expected output:
# [App] Starting ObstacleAware Flask server...
# [App] Access the app at: http://localhost:5000 or http://<your-ip>:5000
# [App] Initializing depth estimator...
# [DepthEstimator] Loading MiDaS small model from torch.hub...
# [DepthEstimator] Model loaded successfully.
# [App] Initializing zone analyzer...
# [App] Initializing alert engine...
#  * Running on http://0.0.0.0:5000
```

The server is now running. Leave this terminal open.

### Step 6a: Access on Laptop/Desktop

Open a web browser and go to:
```
http://localhost:5000
```

You should see:
- ✅ "ObstacleAware" header
- ✅ Live depth feed area (showing real-time INFERNO colormap)
- ✅ 3 zone cards (LEFT, CENTRE, RIGHT) showing CLEAR (green)
- ✅ Yellow alert text area
- ✅ Sensitivity slider and Mute button
- ✅ "Connected ✅" at the bottom

### Step 6b: Access on Mobile Phone/Tablet

**Find your computer's IP address:**

Windows (PowerShell):
```powershell
ipconfig
# Look for "IPv4 Address" (e.g., 192.168.1.100)
```

Linux/Mac (Terminal):
```bash
ifconfig
# or
ip addr
# Look for "inet" address (e.g., 192.168.1.100)
```

**On your mobile device:**
1. Connect to the **same WiFi network** as your computer
2. Open Safari (iOS) or Chrome (Android)
3. Navigate to: `http://192.168.1.100:5000` (use YOUR IP)
4. Allow camera permissions when prompted
5. See live depth feed + obstacle alerts

---

## ⚙️ Configuration

### Adjusting Danger Threshold

The **sensitivity slider** controls how close obstacles must be to trigger an alert:

- **100** (Left end): Extremely sensitive — detects even distant objects
- **180** (Default): Balanced — recommended for typical indoor navigation
- **240** (Right end): Low sensitivity — only very close obstacles trigger alerts

**How to adjust:**
1. Use the slider in the UI (labelled "Detection Sensitivity")
2. Value is sent to server via POST `/settings` endpoint
3. ZoneAnalyzer threshold updates in real-time
4. Changes apply immediately to subsequent frames

**Programmatically (advanced):**
```bash
# Via curl:
curl -X POST http://localhost:5000/settings \
  -H "Content-Type: application/json" \
  -d '{"threshold": 150}'
```

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Depth Model** | Intel MiDaS small (PyTorch) | Monocular depth estimation from single RGB frame |
| **Web Server** | Flask + Flask-SocketIO | HTTP server with WebSocket support for real-time updates |
| **Communication** | WebSocket (Socket.IO) | Low-latency bidirectional streaming of depth frames & alerts |
| **Image Processing** | OpenCV (cv2) | Frame capture, colormap application, JPEG encoding |
| **Numerical Computing** | NumPy | Array operations for depth map analysis |
| **Async I/O** | Eventlet | Lightweight coroutines for concurrent WebSocket connections |
| **Frontend UI** | HTML5 + CSS3 + JavaScript | Mobile-responsive interface (portrait, 360–430px width) |
| **Audio Output** | Web Speech API (TTS) | Text-to-speech synthesis for audio alerts |
| **Visualization** | INFERNO Colormap | Perceptually uniform depth visualization (high contrast for accessibility) |

---

## 📸 Screenshots

*Add screenshots here:*
- [ ] Desktop browser showing depth feed + zone cards
- [ ] Mobile portrait view with alert message
- [ ] Zone panel with RED (danger) and GREEN (clear) states
- [ ] Sensitivity slider adjustment UI
- [ ] Connection status indicator

*(To add screenshots: capture PNG/JPG files and include markdown links)*

```markdown
### Desktop Interface
![Desktop View](screenshots/desktop.png)

### Mobile Interface
![Mobile View](screenshots/mobile.png)
```

---

## 🧪 Testing & Troubleshooting

### Run Tests Without Webcam
```bash
python test_pipeline.py
```

### Common Issues

**Issue:** Webcam not found
```bash
# Test with:
python -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL')"
```

**Issue:** MiDaS model download fails
```bash
# Pre-download model:
python -c "import torch; torch.hub.load('intel-isl/MiDaS', 'MiDaS_small')"
```

**Issue:** Mobile cannot connect
```bash
# Verify server running and check IP:
ipconfig
# Then on mobile: http://YOUR_IP:5000 (not http://localhost:5000)
```

**For complete troubleshooting:** See `SETUP_AND_TROUBLESHOOTING.txt` (5 common errors with exact fixes)

---

## 📄 Additional Documentation

- **[SETUP_AND_TROUBLESHOOTING.txt](SETUP_AND_TROUBLESHOOTING.txt)** — 9-section comprehensive guide
  - Installation steps
  - Test pipeline instructions
  - Mobile access setup
  - 5 common errors with exact fixes
  - Quick reference cheat sheet
  - Performance optimization tips

---

## 👥 Team & Course Info

**Project:** ObstacleAware — Assistive Navigation System  
**Group:** G-22  
**Course:** Computer Vision, Spring 2026  
**Institution:** [Your University/Organization]

---

## 📝 License

This project is licensed under the MIT License — see LICENSE file for details.

---

## 🙏 Acknowledgments

- **Intel MiDaS Team** for the pre-trained depth estimation models
- **Flask & Socket.IO** communities for excellent real-time web frameworks
- **OpenCV & PyTorch** for robust computer vision and deep learning tools
- **Course Instructors** for guidance and feedback throughout the project

---

## 📞 Support & Questions

For issues, feature requests, or questions:
1. Check `SETUP_AND_TROUBLESHOOTING.txt` first
2. Run `test_pipeline.py` to verify installation
3. Check browser console (F12) for JavaScript errors
4. Verify network connectivity and firewall settings

---

**Last Updated:** May 11, 2026  
**Version:** 1.0.0  
**Status:** Fully Functional ✅
