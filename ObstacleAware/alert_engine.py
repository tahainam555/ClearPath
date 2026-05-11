"""Generates user alerts from zone risk analysis for assistive obstacle avoidance.

This module provides the AlertEngine class for translating spatial obstacle
detection results into clear, actionable audio/text alerts for visually
impaired users navigating their environment.
"""

from typing import Dict, Optional


class AlertEngine:
    """
    Generates contextual alerts based on obstacle detection in spatial zones.
    
    Analyzes zone-level danger flags (from ZoneAnalyzer) and produces
    priority-ordered alerts to guide users in obstacle avoidance with
    clear directional guidance.
    """
    
    def __init__(self):
        """Initialize the AlertEngine."""
        print("[AlertEngine] Initialized")
    
    def get_alert(self, zone_result: Dict[str, Dict[str, float | bool]]) -> Optional[str]:
        """
        Generate an alert message based on obstacle detection in zones.
        
        Evaluates which zones have detected obstacles (danger=True) and returns
        an actionable alert string using priority-based logic. The priority
        emphasizes immediate threats (centre) and then provides directional
        guidance for lateral threats (left/right).
        
        Alert Priority Logic:
        1. All 3 zones dangerous      → Imminent threat all directions
        2. Centre + Left dangerous    → Head-on threat with left obstacle
        3. Centre + Right dangerous   → Head-on threat with right obstacle
        4. Left + Right dangerous     → No direct head-on threat, sides blocked
        5. Only Centre                → Direct head-on threat
        6. Only Left                  → Side threat with escape route to right
        7. Only Right                 → Side threat with escape route to left
        8. No zones dangerous         → Clear path (no alert)
        
        Args:
            zone_result (dict): Zone analysis output from ZoneAnalyzer.analyze().
                               Expected structure:
                               {
                                 "left": {"avg": float, "danger": bool},
                                 "centre": {"avg": float, "danger": bool},
                                 "right": {"avg": float, "danger": bool}
                               }
        
        Returns:
            str or None: Alert message string if obstacles detected, None if path is clear.
                        Alert strings are designed for text-to-speech accessibility.
        """
        
        # ============ INPUT VALIDATION ============
        
        # Validate zone_result structure and extract danger flags
        try:
            left_danger = zone_result["left"]["danger"]
            centre_danger = zone_result["centre"]["danger"]
            right_danger = zone_result["right"]["danger"]
        except (KeyError, TypeError) as e:
            print(f"[AlertEngine] Error: Invalid zone_result structure: {e}")
            return None
        
        # ============ PRIORITY-BASED ALERT LOGIC ============
        
        # Priority 1: All 3 zones dangerous — maximum urgency
        if left_danger and centre_danger and right_danger:
            return "Obstacles all around — stop immediately"
        
        # Priority 2: Centre + Left dangerous — head-on with left block
        # User should avoid moving left; right is potentially clear
        if centre_danger and left_danger and not right_danger:
            return "Obstacles ahead and on your left"
        
        # Priority 3: Centre + Right dangerous — head-on with right block
        # User should avoid moving right; left is potentially clear
        if centre_danger and right_danger and not left_danger:
            return "Obstacles ahead and on your right"
        
        # Priority 4: Left + Right dangerous — sides blocked, centre clear
        # This case indicates a narrow passage or corridor
        if left_danger and right_danger and not centre_danger:
            return "Obstacles on both sides"
        
        # Priority 5: Only Centre dangerous — direct head-on threat
        # User must stop; turning may help
        if centre_danger and not left_danger and not right_danger:
            return "Obstacle ahead — stop"
        
        # Priority 6: Only Left dangerous — side threat with clear right
        # Directional guidance: move right to clear obstacle
        if left_danger and not centre_danger and not right_danger:
            return "Obstacle on your left — move right"
        
        # Priority 7: Only Right dangerous — side threat with clear left
        # Directional guidance: move left to clear obstacle
        if right_danger and not centre_danger and not left_danger:
            return "Obstacle on your right — move left"
        
        # No zones dangerous — path is clear
        return None
    
    def get_zone_colors(
        self, zone_result: Dict[str, Dict[str, float | bool]]
    ) -> Dict[str, str]:
        """
        Generate color codes for UI visualization of zone danger levels.
        
        Returns a mapping of zone names to color strings for rendering
        in the web interface. Red indicates danger (potential obstacle),
        green indicates clear (safe passage).
        
        Color convention:
        - "red":   Zone has detected obstacle (danger=True)
        - "green": Zone is clear (danger=False)
        
        Args:
            zone_result (dict): Zone analysis output from ZoneAnalyzer.analyze().
                               Expected structure:
                               {
                                 "left": {"avg": float, "danger": bool},
                                 "centre": {"avg": float, "danger": bool},
                                 "right": {"avg": float, "danger": bool}
                               }
        
        Returns:
            dict: Color mapping with structure:
                  {
                    "left": "red" | "green",
                    "centre": "red" | "green",
                    "right": "red" | "green"
                  }
        """
        
        # ============ INPUT VALIDATION ============
        
        # Validate zone_result structure
        try:
            left_danger = zone_result["left"]["danger"]
            centre_danger = zone_result["centre"]["danger"]
            right_danger = zone_result["right"]["danger"]
        except (KeyError, TypeError) as e:
            print(f"[AlertEngine] Error: Invalid zone_result structure in get_zone_colors: {e}")
            # Return safe defaults (all green) on error
            return {
                "left": "green",
                "centre": "green",
                "right": "green"
            }
        
        # ============ COLOR ASSIGNMENT ============
        
        # Map each zone to its danger level color
        # Red = danger detected, Green = clear
        return {
            "left": "red" if left_danger else "green",
            "centre": "red" if centre_danger else "green",
            "right": "red" if right_danger else "green"
        }
