#!/usr/bin/env python3
"""
Calendar Styling Module
Handles all theme colors and CSS styling for the calendar widget
"""

import subprocess
import json
import re
from pathlib import Path

def hex_to_rgba(hex_color, alpha=1.0):
    """Convert hex color to rgba string"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"
    return hex_color

def get_hyprland_colors():
    """
    Extract colors dynamically from multiple sources:
    1. Hyprland border colors
    2. Pywal color scheme
    3. Fallback to Catppuccin theme
    """
    colors = {
        'bg': '#1e1e2e',
        'fg': '#cdd6f4',
        'accent': '#89b4fa',
        'border': '#89b4fa',
        'hover': '#313244',
        'today': '#89b4fa',
        'today_fg': '#1e1e2e',
        'event': '#f9e2af',
        'weekday': '#f9e2af',
        'inactive': '#6c7086',
        'delete': '#f38ba8',
        'delete_hover': '#eba0ac'
    }
    
    # Try to get colors from Hyprland
    try:
        result = subprocess.run(
            ['hyprctl', 'getoption', 'general:col.active_border'], 
            capture_output=True, 
            text=True, 
            timeout=1
        )
        if result.returncode == 0:
            match = re.search(r'0x([0-9a-fA-F]{6})', result.stdout)
            if match:
                hex_color = '#' + match.group(1)
                colors['accent'] = hex_color
                colors['border'] = hex_color
                colors['today'] = hex_color
    except:
        pass
    
    # Try to read from pywal cache (overrides Hyprland colors if available)
    pywal_colors = Path.home() / '.cache' / 'wal' / 'colors.json'
    if pywal_colors.exists():
        try:
            with open(pywal_colors, 'r') as f:
                wal = json.load(f)
                colors['bg'] = wal['special']['background']
                colors['fg'] = wal['special']['foreground']
                colors['accent'] = wal['colors']['color4']
                colors['border'] = wal['colors']['color4']
                colors['hover'] = wal['colors']['color8']
                colors['today'] = wal['colors']['color6']
                colors['event'] = wal['colors']['color3']
                colors['weekday'] = wal['colors']['color3']
                colors['inactive'] = wal['colors']['color8']
                colors['today_fg'] = wal['special']['background']
        except:
            pass
    
    return colors


def generate_css(colors):
    """
    Generate CSS stylesheet based on provided colors
    """
    bg_rgba = hex_to_rgba(colors['bg'], 0.85)
    hover_rgba = hex_to_rgba(colors['hover'], 0.6)
    
    css = f"""
        /* Global Font & Window */
        * {{
            font-family: "JetBrainsMono Nerd Font", "JetBrains Mono", "Fira Code", "Roboto", sans-serif;
        }}

        window {{
            background-color: transparent;
            border: none;
        }}

        .popup-window {{
            background-color: {bg_rgba};
            border: 2px solid {colors['border']};
            border-radius: 16px;
        }}
        
        .arrow-up {{
            background-color: transparent;
            border-left: 10px solid transparent;
            border-right: 10px solid transparent;
            border-bottom: 10px solid {colors['border']};
            margin-bottom: -2px; /* Overlap slightly with the border */
        }}
        
        /* Main Container */
        .main-container {{
            padding: 0;
        }}
        
        /* Left Pane (Events) */
        .events-pane {{
            background-color: rgba(0, 0, 0, 0.3);
            border-right: 1px solid {hex_to_rgba(colors['fg'], 0.1)};
            padding: 24px;
            min-width: 280px;
            border-top-left-radius: 14px;
            border-bottom-left-radius: 14px;
        }}
        
        /* Right Pane (Calendar) */
        .calendar-pane {{
            padding: 24px;
            background-color: transparent;
        }}
        
        /* Headers */
        .header-label {{
            font-size: 14px;
            font-weight: 800;
            color: {colors['accent']};
            margin-bottom: 20px;
            letter-spacing: 1px;
        }}
        
        .month-label {{
            font-size: 24px;
            font-weight: 800;
            color: {colors['fg']};
            letter-spacing: -0.5px;
        }}
        
        /* Calendar Day Buttons */
        .calendar-day {{
            min-width: 42px;
            min-height: 42px;
            border-radius: 12px;
            margin: 2px;
            background-color: transparent;
            color: {colors['fg']};
            border: 1px solid transparent;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s ease;
        }}
        
        .calendar-day:hover {{
            background-color: {hex_to_rgba(colors['accent'], 0.2)};
            color: {colors['accent']};
            border-color: {colors['accent']};
        }}
        
        .calendar-day.today {{
            background-color: {colors['accent']};
            color: {colors['bg']};
            font-weight: 800;
            box-shadow: 0 0 10px {hex_to_rgba(colors['accent'], 0.5)};
        }}
        
        .calendar-day.selected {{
            border: 2px solid {colors['accent']};
            background-color: transparent;
            color: {colors['accent']};
        }}
        
        .calendar-day.has-event {{
            font-weight: 800;
            color: {colors['event']};
        }}
        
        /* Weekday Labels */
        .weekday-label {{
            color: {hex_to_rgba(colors['fg'], 0.6)};
            font-weight: 700;
            font-size: 12px;
            padding-bottom: 12px;
        }}
        
        /* Navigation Buttons */
        .nav-button {{
            min-width: 32px;
            min-height: 32px;
            border-radius: 8px;
            background-color: {hex_to_rgba(colors['fg'], 0.1)};
            color: {colors['fg']};
            border: none;
            font-size: 14px;
            margin-left: 8px;
            padding: 0;
            transition: all 0.2s;
        }}
        
        .nav-button:hover {{
            background-color: {colors['accent']};
            color: {colors['bg']};
        }}
        
        /* Toggle Buttons (AD/BS) */
        .toggle-button {{
            padding: 6px 16px;
            border-radius: 8px;
            background-color: transparent;
            color: {hex_to_rgba(colors['fg'], 0.5)};
            border: 1px solid {hex_to_rgba(colors['fg'], 0.2)};
            font-weight: 700;
            font-size: 12px;
            margin-right: 8px;
            transition: all 0.2s;
        }}
        
        .toggle-button:checked {{
            background-color: {colors['accent']};
            color: {colors['bg']};
            border-color: {colors['accent']};
        }}
        
        /* Event Items */
        .event-item {{
            padding: 16px;
            margin-bottom: 12px;
            border-radius: 12px;
            background-color: {hex_to_rgba(colors['fg'], 0.05)};
            border: 1px solid {hex_to_rgba(colors['fg'], 0.1)};
            transition: all 0.2s;
        }}
        
        .event-item:hover {{
            border-color: {colors['accent']};
            background-color: {hex_to_rgba(colors['fg'], 0.08)};
        }}
        
        .event-title {{
            font-weight: 700;
            font-size: 14px;
            color: {colors['fg']};
            margin-bottom: 4px;
        }}
        
        .event-meta {{
            font-size: 12px;
            color: {hex_to_rgba(colors['fg'], 0.6)};
        }}
        
        /* Add Event Button */
        .add-event-btn {{
            background-color: {colors['accent']};
            color: {colors['bg']};
            border-radius: 8px;
            padding: 8px 12px;
            font-weight: 700;
            border: none;
            margin-left: 8px;
        }}
        
        .add-event-btn:hover {{
            background-color: {colors['hover']};
        }}
        
        /* Inputs */
        entry {{
            background-color: {hex_to_rgba(colors['fg'], 0.05)};
            color: {colors['fg']};
            border: 1px solid {hex_to_rgba(colors['fg'], 0.1)};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 13px;
        }}
        
        entry:focus {{
            border-color: {colors['accent']};
            box-shadow: 0 0 0 1px {colors['accent']};
        }}
        
        /* Scrollbar */
        scrollbar slider {{
            min-width: 4px;
            border-radius: 2px;
            background-color: {hex_to_rgba(colors['fg'], 0.2)};
        }}
        
        /* Delete Button */
        .delete-btn {{
            color: {hex_to_rgba(colors['fg'], 0.4)};
            background-color: transparent;
            border-radius: 4px;
            min-width: 20px;
            min-height: 20px;
            padding: 0;
        }}
        
        .delete-btn:hover {{
            color: {colors['delete']};
            background-color: {hex_to_rgba(colors['delete'], 0.1)};
        }}
    """
    
    return css.encode('utf-8')


def get_styled_css():
    colors = get_hyprland_colors()
    return generate_css(colors)
