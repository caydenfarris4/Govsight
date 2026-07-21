"""
Module Icons - SVG Icons for the Three Main Modules

This module provides SVG icons for the three consolidated modules:
- Navi: Compass icon for navigation and planning
- Mantis: Mantis icon for intelligence and analysis
- Vatica: Cathedral icon for comprehensive analysis
"""

def get_compass_icon():
    """Return SVG for compass icon (Navi module)"""
    return """
    <svg width="120" height="120" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="60" cy="60" r="55" fill="#667eea" stroke="#764ba2" stroke-width="3"/>
        <circle cx="60" cy="60" r="45" fill="none" stroke="white" stroke-width="2"/>
        <path d="M60 15 L65 25 L60 35 L55 25 Z" fill="white"/>
        <path d="M60 85 L65 95 L60 105 L55 95 Z" fill="white"/>
        <path d="M15 60 L25 55 L35 60 L25 65 Z" fill="white"/>
        <path d="M85 60 L95 55 L105 60 L95 65 Z" fill="white"/>
        <path d="M60 30 L75 60 L60 90 L45 60 Z" fill="#f093fb" opacity="0.7"/>
        <circle cx="60" cy="60" r="3" fill="white"/>
    </svg>
    """

def get_mantis_icon():
    """Return SVG for mantis icon (Mantis module)"""
    return """
    <svg width="120" height="120" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
        <ellipse cx="60" cy="70" rx="25" ry="35" fill="#f093fb" stroke="#f5576c" stroke-width="2"/>
        <ellipse cx="60" cy="50" rx="15" ry="20" fill="#f5576c" stroke="#f093fb" stroke-width="2"/>
        <circle cx="55" cy="45" r="3" fill="white"/>
        <circle cx="65" cy="45" r="3" fill="white"/>
        <path d="M35 40 Q30 35 25 40 Q30 45 35 40" fill="#f093fb" stroke="#f5576c" stroke-width="1"/>
        <path d="M85 40 Q90 35 95 40 Q90 45 85 40" fill="#f093fb" stroke="#f5576c" stroke-width="1"/>
        <path d="M30 60 Q20 55 15 65 Q25 70 30 60" fill="#f5576c" stroke="#f093fb" stroke-width="1"/>
        <path d="M90 60 Q100 55 105 65 Q95 70 90 60" fill="#f5576c" stroke="#f093fb" stroke-width="1"/>
        <path d="M45 95 L40 105 L50 105 Z" fill="#f093fb"/>
        <path d="M75 95 L80 105 L70 105 Z" fill="#f093fb"/>
    </svg>
    """

def get_cathedral_icon():
    """Return SVG for cathedral icon (Vatica module)"""
    return """
    <svg width="120" height="120" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="30" y="60" width="60" height="45" fill="#4facfe" stroke="#00f2fe" stroke-width="2"/>
        <path d="M25 60 L60 25 L95 60 Z" fill="#00f2fe" stroke="#4facfe" stroke-width="2"/>
        <rect x="50" y="45" width="20" height="60" fill="#4facfe" stroke="#00f2fe" stroke-width="2"/>
        <path d="M45 45 L60 20 L75 45 Z" fill="#00f2fe" stroke="#4facfe" stroke-width="2"/>
        <rect x="40" y="70" width="8" height="15" fill="#00f2fe"/>
        <rect x="52" y="70" width="8" height="15" fill="#00f2fe"/>
        <rect x="64" y="70" width="8" height="15" fill="#00f2fe"/>
        <rect x="76" y="70" width="8" height="15" fill="#00f2fe"/>
        <rect x="55" y="85" width="10" height="20" fill="white" stroke="#4facfe" stroke-width="1"/>
        <circle cx="60" cy="35" r="3" fill="white"/>
    </svg>
    """