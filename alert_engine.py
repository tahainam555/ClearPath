"""
Convert zone analysis into human-friendly alert messages.

Public API:
  generate_alert(zones: dict) -> Optional[str]

The function intelligently combines multi-zone danger information into a
concise English phrase, or returns None when no danger is detected.
"""
from typing import Optional, Dict


def generate_alert(zones: Dict[str, Dict]) -> Optional[str]:
    """Generate alert message from zone analysis.

    Examples:
      - {left: True} -> "Obstacle on your left"
      - {centre: True, right: True} -> "Obstacles ahead and on your right"
      - none -> None
    """
    dangerous = [name for name, info in zones.items() if info.get('danger')]

    if not dangerous:
        return None

    # Map names to readable phrases
    mapping = {
        'left': 'on your left',
        'centre': 'ahead',
        'right': 'on your right'
    }

    # Create human-friendly description
    if len(dangerous) == 1:
        zone = dangerous[0]
        if zone == 'centre':
            return 'Obstacle ahead'
        return f'Obstacle {mapping[zone]}'

    # Multiple zones -> join intelligently
    parts = [mapping[z] for z in dangerous]
    if 'ahead' in parts:
        # Place 'ahead' first
        parts.remove('ahead')
        parts.insert(0, 'ahead')

    # Build sentence
    if len(parts) == 2:
        # e.g., 'ahead and on your right'
        msg = 'Obstacles ' + parts[0] + ' and ' + parts[1]
    else:
        # three zones
        msg = 'Obstacles ' + ', '.join(parts[:-1]) + ', and ' + parts[-1]

    # Fix small grammatical issues
    msg = msg.replace('Obstacles ahead', 'Obstacles ahead')
    return msg
