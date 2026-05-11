"""
Zone analyzer divides a depth map into three vertical zones and evaluates danger.

Function `analyze_zones(depth_map, threshold=180)` accepts a single-channel
0-255 numpy array and returns a dict of the form:

  {
    "left": {"avg": float, "danger": bool},
    "centre": {"avg": float, "danger": bool},
    "right": {"avg": float, "danger": bool}
  }

Higher average values are treated as closer/denser obstacles (threshold is 0-255).
"""
import numpy as np
from typing import Dict


def analyze_zones(depth_map: np.ndarray, threshold: int = 180) -> Dict[str, Dict]:
    """Divide depth_map into left/centre/right and compute averages.

    Args:
        depth_map: HxW single-channel uint8 numpy array (0-255)
        threshold: danger threshold in same 0-255 scale (default 180)

    Returns:
        dict with keys 'left','centre','right' each mapping to {avg, danger}
    """
    if depth_map.ndim != 2:
        raise ValueError('depth_map must be single-channel 2D array')

    h, w = depth_map.shape
    third = w // 3

    left = depth_map[:, :third]
    centre = depth_map[:, third:2 * third]
    right = depth_map[:, 2 * third:]

    def summarize(zone: np.ndarray):
        avg = float(np.mean(zone)) if zone.size else 0.0
        danger = avg >= threshold
        return {"avg": avg, "danger": bool(danger)}

    return {
        "left": summarize(left),
        "centre": summarize(centre),
        "right": summarize(right),
    }
