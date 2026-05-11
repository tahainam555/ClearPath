# ClearPath — ObstacleAware (Group G-22)

This repository contains a CPU-first, real-time obstacle awareness demo for
visually impaired pedestrians using a monocular depth estimator (MiDaS small).

Run locally and open the frontend on a mobile browser to test with your device
camera (connect to the same Wi‑Fi network and visit http://<host-ip>:5000/).

## Setup

1. Create a Python 3.9+ virtual environment and activate it:

```bash
python -m venv venv
venv\Scripts\activate    # Windows
source venv/bin/activate # macOS / Linux
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python app.py
```

4. From your phone or another device on the same network, open:

```
http://<machine-local-ip>:5000/
```

Replace `<machine-local-ip>` with your PC's LAN IP (e.g., `192.168.1.42`).

## Notes

- The first run downloads MiDaS weights via `torch.hub` (internet required).
- The project uses CPU-only inference (MiDaS_small) and targets ~5–10 FPS on
	modest CPUs; performance depends on hardware.
- Sensitivity slider adjusts the danger threshold (0–255). Default is 180.
