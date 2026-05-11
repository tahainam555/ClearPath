"""Analyzes estimated depth maps to segment and evaluate obstacle risk zones.

This module provides the ZoneAnalyzer class for partitioning depth maps into
left/centre/right zones and computing obstacle risk levels based on average depth
values within each zone relative to a configurable threshold.
"""

import numpy as np
from typing import Dict


class ZoneAnalyzer:
    """
    Analyzes depth maps by dividing them into left, centre, and right zones.
    
    Computes average depth within each zone and compares against a configurable
    depth threshold to determine obstacle danger levels. Lower depth values
    indicate closer objects (higher danger), upper depth values indicate
    farther objects (lower danger).
    """
    
    def __init__(self, threshold: int = 180):
        """
        Initialize the ZoneAnalyzer with a depth danger threshold.
        
        Args:
            threshold (int): Depth value threshold in range [0, 255].
                           Depths <= threshold are flagged as "danger".
                           Defaults to 180 (roughly 71% of maximum depth).
        
        Raises:
            ValueError: If threshold is not in valid range [0, 255].
        """
        if not isinstance(threshold, int) or threshold < 0 or threshold > 255:
            raise ValueError(f"Threshold must be an integer in range [0, 255], got {threshold}.")
        
        self.threshold = threshold
        print(f"[ZoneAnalyzer] Initialized with threshold={self.threshold}")
    
    def set_threshold(self, value: int) -> None:
        """
        Update the depth danger threshold at runtime.
        
        Args:
            value (int): New threshold value in range [0, 255].
        
        Raises:
            ValueError: If value is not in valid range [0, 255].
        """
        if not isinstance(value, int) or value < 0 or value > 255:
            raise ValueError(f"Threshold must be an integer in range [0, 255], got {value}.")
        
        old_threshold = self.threshold
        self.threshold = value
        print(f"[ZoneAnalyzer] Threshold updated: {old_threshold} -> {self.threshold}")
    
    def analyze(self, depth_map: np.ndarray) -> Dict[str, Dict[str, float | bool]]:
        """
        Analyze depth map by computing obstacle danger levels in left, centre, right zones.
        
        Divides the depth map into 3 equal vertical columns (left/centre/right),
        computes the average depth within each zone, and compares against the
        configured threshold to flag danger.
        
        Depth interpretation:
        - Lower values (0-60):   Close objects, high danger
        - Medium values (60-180): Mid-range objects, moderate caution
        - Higher values (180+):   Distant objects, low danger
        
        Args:
            depth_map (np.ndarray): Normalized depth array from DepthEstimator.
                                   Expected shape: (height, width), dtype: uint8,
                                   values in range [0, 255].
        
        Returns:
            dict: Analysis results with structure:
                {
                  "left": {
                    "avg": float,    # Average depth in left zone [0.0, 255.0]
                    "danger": bool   # True if avg <= threshold (obstacle detected)
                  },
                  "centre": {
                    "avg": float,
                    "danger": bool
                  },
                  "right": {
                    "avg": float,
                    "danger": bool
                  }
                }
        
        Raises:
            ValueError: If depth_map format is invalid (not 2D or wrong dtype).
        """
        
        # ============ INPUT VALIDATION ============
        
        # Validate that depth_map is a 2D numpy array
        if not isinstance(depth_map, np.ndarray) or depth_map.ndim != 2:
            raise ValueError(
                f"depth_map must be a 2D numpy array, got shape {depth_map.shape}."
            )
        
        # Validate that values are in expected range (0-255)
        if depth_map.size > 0:  # Only check if array is not empty
            depth_min = depth_map.min()
            depth_max = depth_map.max()
            if depth_min < 0 or depth_max > 255:
                print(f"[ZoneAnalyzer] Warning: depth_map values out of expected range "
                      f"[{depth_min}, {depth_max}]. Expected [0, 255].")
        
        # ============ ZONE DIVISION ============
        
        # Extract map dimensions
        height, width = depth_map.shape
        
        # Compute column boundaries for 3 equal vertical zones
        # Division into thirds ensures balanced left-to-right obstacle detection
        
        # Left zone: columns [0, width//3)
        left_end = width // 3
        
        # Centre zone: columns [width//3, 2*width//3)
        centre_start = width // 3
        centre_end = 2 * width // 3
        
        # Right zone: columns [2*width//3, width)
        # This handles remainder pixels if width is not evenly divisible by 3
        right_start = 2 * width // 3
        
        # Extract zone slices from the depth map
        # NumPy slicing: depth_map[:, start:end] gets all rows, columns [start, end)
        left_zone = depth_map[:, :left_end]
        centre_zone = depth_map[:, centre_start:centre_end]
        right_zone = depth_map[:, right_start:]
        
        # ============ AVERAGE DEPTH COMPUTATION ============
        
        # Compute mean depth value for each zone
        # If a zone is empty (width < 3), numpy.mean returns NaN
        left_avg = float(np.mean(left_zone)) if left_zone.size > 0 else 0.0
        centre_avg = float(np.mean(centre_zone)) if centre_zone.size > 0 else 0.0
        right_avg = float(np.mean(right_zone)) if right_zone.size > 0 else 0.0
        
        # ============ DANGER CLASSIFICATION ============
        
        # Classify each zone as "danger" if average depth <= threshold
        # Logic: Lower depth values = closer objects = higher danger
        # danger=True means an obstacle is detected at potentially unsafe distance
        left_danger = left_avg <= self.threshold
        centre_danger = centre_avg <= self.threshold
        right_danger = right_avg <= self.threshold
        
        # ============ RETURN RESULTS ============
        
        # Return structured analysis results
        return {
            "left": {
                "avg": left_avg,
                "danger": left_danger
            },
            "centre": {
                "avg": centre_avg,
                "danger": centre_danger
            },
            "right": {
                "avg": right_avg,
                "danger": right_danger
            }
        }
