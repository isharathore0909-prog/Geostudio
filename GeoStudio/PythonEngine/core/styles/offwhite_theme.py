# -*- coding: utf-8 -*-
"""
GeoStudio - Off-White Pro Light Workstation Theme
"""

from .tokens import FONT_FAMILY, MONO_FONT
from .theme_base import get_theme_base
from .theme_controls import get_theme_controls

OFFWHITE_STYLESHEET = f"""
/* ═══════════════════════════════════════════════════════════════
   GeoStudio — Professional Off-White Workstation Light Theme
   ═══════════════════════════════════════════════════════════════ */
{get_theme_base()}
{get_theme_controls()}
"""
