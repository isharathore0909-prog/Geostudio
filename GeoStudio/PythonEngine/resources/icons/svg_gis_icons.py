# -*- coding: utf-8 -*-
"""
GeoStudio - GIS & Earthwork SVG Icons
"""

GIS_SVGS = {
    # ── Project / File ─────────────────────────────────────────
    "new_project": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="#eff6ff"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="12" y1="18" x2="12" y2="12" stroke="#16a34a"/>
            <line x1="9" y1="15" x2="15" y2="15" stroke="#16a34a"/>
        </svg>
    """,
    "open_project": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" fill="#fef3c7"/>
            <polygon points="12 11 12 17 16 14" fill="#d97706"/>
        </svg>
    """,
    "save_project": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" fill="#eff6ff"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
        </svg>
    """,
    "save_project_as": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" fill="#eff6ff"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <circle cx="18" cy="18" r="3.5" fill="#16a34a" stroke="#ffffff" stroke-width="1.2"/>
            <line x1="18" y1="16" x2="18" y2="20" stroke="#ffffff"/>
            <line x1="16" y1="18" x2="20" y2="18" stroke="#ffffff"/>
        </svg>
    """,
    "print_map": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 6 2 18 2 18 9"/>
            <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" fill="#f8fafc"/>
            <rect x="6" y="14" width="12" height="8" fill="#ffffff"/>
        </svg>
    """,

    # ── Data Sources ───────────────────────────────────────────
    "add_vector": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="12 2 2 7 12 12 22 7 12 2" fill="#dcfce7"/>
            <polyline points="2 17 12 22 22 17"/>
            <polyline points="2 12 12 17 22 12"/>
            <circle cx="19" cy="19" r="4.5" fill="#16a34a"/>
            <line x1="19" y1="16.5" x2="19" y2="21.5" stroke="#ffffff" stroke-width="1.8"/>
            <line x1="16.5" y1="19" x2="21.5" y2="19" stroke="#ffffff" stroke-width="1.8"/>
        </svg>
    """,
    "add_raster": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#ea580c" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" fill="#ffedd5"/>
            <line x1="3" y1="9" x2="21" y2="9"/>
            <line x1="3" y1="15" x2="21" y2="15"/>
            <line x1="9" y1="3" x2="9" y2="21"/>
            <line x1="15" y1="3" x2="15" y2="21"/>
            <circle cx="19" cy="19" r="4.5" fill="#ea580c"/>
            <line x1="19" y1="16.5" x2="19" y2="21.5" stroke="#ffffff" stroke-width="1.8"/>
            <line x1="16.5" y1="19" x2="21.5" y2="19" stroke="#ffffff" stroke-width="1.8"/>
        </svg>
    """,
    "add_csv": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#0891b2" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="#ecfeff"/>
            <polyline points="14 2 14 8 20 8"/>
            <circle cx="8" cy="13" r="1.5" fill="#0891b2"/>
            <circle cx="14" cy="13" r="1.5" fill="#0891b2"/>
            <circle cx="10" cy="17" r="1.5" fill="#0891b2"/>
        </svg>
    """,
    "add_wms": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="9.5" fill="#e0f2fe"/>
            <line x1="2.5" y1="12" x2="21.5" y2="12"/>
            <path d="M12 2.5a15 15 0 0 1 4 9.5 15 15 0 0 1-4 9.5 15 15 0 0 1-4-9.5 15 15 0 0 1 4-9.5z"/>
        </svg>
    """,
    "add_xyz": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" fill="#eef2ff"/>
            <line x1="8" y1="2" x2="8" y2="18"/>
            <line x1="16" y1="6" x2="16" y2="22"/>
        </svg>
    """,
    "browser_panel": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" fill="#f8fafc"/>
            <line x1="9" y1="3" x2="9" y2="21"/>
        </svg>
    """,

    # ── Terrain & Elevation ────────────────────────────────────
    "shader": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="3" width="20" height="18" rx="2" fill="#ede9fe"/>
            <path d="M2 15l5-5 5 5 5-5 5 5" stroke="#8b5cf6" stroke-width="2.5"/>
            <circle cx="18" cy="8" r="2" fill="#f59e0b"/>
        </svg>
    """,
    "elevation": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2 20h20"/>
            <path d="m5 20 6-12 4 6 4-9 3 15" fill="#d1fae5"/>
        </svg>
    """,
    "slope": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#ea580c" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="3 20 21 20 21 4 3 20" fill="#ffedd5"/>
            <line x1="7" y1="16" x2="17" y2="8" stroke="#ea580c" stroke-width="2.5"/>
        </svg>
    """,
    "aspect": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="9.5" fill="#f8fafc"/>
            <polygon points="12 4 15 12 12 10 9 12 12 4" fill="#dc2626" stroke="#dc2626"/>
            <polygon points="12 20 15 12 12 14 9 12 12 20" fill="#64748b" stroke="#64748b"/>
        </svg>
    """,
    "hillshade": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="6" cy="6" r="3" fill="#fef08a"/>
            <path d="m2 20 8-10 6 7 3-4 3 7H2z" fill="#475569" stroke="#334155"/>
        </svg>
    """,
    "view_3d": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="12 2 2 7 12 12 22 7 12 2" fill="#e0e7ff"/>
            <polyline points="2 17 12 22 22 17"/>
            <polyline points="2 12 12 17 22 12"/>
        </svg>
    """,
    "cut_fill": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 14h18"/>
            <path d="m4 14 4-6 6 6" fill="#fecaca"/>
            <path d="m14 14 3 5 4-5" fill="#bbf7d0"/>
        </svg>
    """,
    "watershed": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2a5 5 0 0 0-5 5c0 4 5 11 5 11s5-7 5-11a5 5 0 0 0-5-5Z" fill="#bae6fd"/>
            <path d="M2 19c2 0 2-2 4-2s2 2 4 2 2-2 4-2 2 2 4 2 2-2 4-2"/>
        </svg>
    """,

    # ── LiDAR / Point Cloud ────────────────────────────────────
    "load_las": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#9333ea" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" fill="#f3e8ff"/>
            <circle cx="8" cy="15" r="1" fill="#9333ea"/>
            <circle cx="12" cy="13" r="1" fill="#9333ea"/>
            <circle cx="15" cy="16" r="1" fill="#9333ea"/>
            <circle cx="11" cy="17" r="1" fill="#9333ea"/>
        </svg>
    """,
    "classify_ground": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2 18h20" stroke-width="3"/>
            <circle cx="5" cy="14" r="1.5" fill="#16a34a"/>
            <circle cx="10" cy="14" r="1.5" fill="#16a34a"/>
            <circle cx="15" cy="14" r="1.5" fill="#16a34a"/>
            <circle cx="19" cy="14" r="1.5" fill="#16a34a"/>
        </svg>
    """,
    "classify_buildings": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="4" y="4" width="16" height="16" rx="2" fill="#fee2e2"/>
            <line x1="8" y1="8" x2="8" y2="10"/>
            <line x1="16" y1="8" x2="16" y2="10"/>
            <line x1="8" y1="14" x2="8" y2="16"/>
            <line x1="16" y1="14" x2="16" y2="16"/>
        </svg>
    """,
    "classify_veg": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2a7 7 0 0 0-7 7c0 3 2 5 4 6.5V20h6v-4.5c2-1.5 4-3.5 4-6.5a7 7 0 0 0-7-7Z" fill="#d1fae5"/>
            <line x1="12" y1="11" x2="12" y2="20"/>
        </svg>
    """,
    "thin": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="6" cy="6" r="1.5" fill="#64748b"/>
            <circle cx="18" cy="6" r="1.5" fill="#64748b"/>
            <circle cx="12" cy="12" r="1.5" fill="#64748b"/>
            <circle cx="6" cy="18" r="1.5" fill="#64748b"/>
            <circle cx="18" cy="18" r="1.5" fill="#64748b"/>
            <line x1="3" y1="21" x2="21" y2="3" stroke="#dc2626" stroke-width="1.8"/>
        </svg>
    """,
    "clip": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#e11d48" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="6" cy="6" r="3"/>
            <circle cx="6" cy="18" r="3"/>
            <line x1="20" y1="4" x2="8.12" y2="15.88"/>
            <line x1="14.47" y1="14.48" x2="20" y2="20"/>
            <line x1="8.12" y1="8.12" x2="12" y2="12"/>
        </svg>
    """,
    "color_by": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#9333ea" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="13.5" cy="6.5" r="2.5" fill="#ef4444"/>
            <circle cx="17.5" cy="10.5" r="2.5" fill="#10b981"/>
            <circle cx="8.5" cy="7.5" r="2.5" fill="#3b82f6"/>
            <circle cx="6.5" cy="12.5" r="2.5" fill="#f59e0b"/>
            <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.9 0 1.6-.7 1.6-1.6 0-.4-.2-.8-.4-1.1-.3-.3-.4-.7-.4-1.1 0-.9.7-1.6 1.6-1.6H16c3.3 0 6-2.7 6-6 0-5.5-4.5-9.6-10-9.6Z"/>
        </svg>
    """,

    # ── Digitizing ─────────────────────────────────────────────
    "toggle_edit": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#ea580c" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" fill="#ffedd5"/>
        </svg>
    """,
    "add_point": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#e11d48" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="4" fill="#e11d48"/>
            <line x1="12" y1="2" x2="12" y2="6"/>
            <line x1="12" y1="18" x2="12" y2="22"/>
            <line x1="2" y1="12" x2="6" y2="12"/>
            <line x1="18" y1="12" x2="22" y2="12"/>
        </svg>
    """,
    "add_line": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="4" cy="19" r="2.5" fill="#2563eb"/>
            <circle cx="11" cy="6" r="2.5" fill="#2563eb"/>
            <circle cx="20" cy="14" r="2.5" fill="#2563eb"/>
            <line x1="6" y1="17.5" x2="9.5" y2="8"/>
            <line x1="13" y1="7.5" x2="18" y2="12.5"/>
        </svg>
    """,
    "add_poly": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="12 3 21 9 18 20 6 20 3 9" fill="#dcfce7"/>
            <circle cx="12" cy="3" r="2" fill="#16a34a"/>
            <circle cx="21" cy="9" r="2" fill="#16a34a"/>
            <circle cx="18" cy="20" r="2" fill="#16a34a"/>
            <circle cx="6" cy="20" r="2" fill="#16a34a"/>
            <circle cx="3" cy="9" r="2" fill="#16a34a"/>
        </svg>
    """,
    "vertex_tool": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 20 10 4l6 10 4-4"/>
            <rect x="2" y="18" width="4" height="4" fill="#2563eb"/>
            <rect x="8" y="2" width="4" height="4" fill="#2563eb"/>
            <rect x="14" y="12" width="4" height="4" fill="#2563eb"/>
            <rect x="18" y="8" width="4" height="4" fill="#2563eb"/>
        </svg>
    """,
    "split": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#e11d48" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" fill="#f8fafc"/>
            <line x1="3" y1="3" x2="21" y2="21" stroke="#dc2626" stroke-width="2.5" stroke-dasharray="2 2"/>
        </svg>
    """,
    "merge": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="5" width="10" height="14" rx="1" fill="#dcfce7"/>
            <rect x="12" y="5" width="10" height="14" rx="1" fill="#dcfce7"/>
            <line x1="8" y1="12" x2="16" y2="12" stroke="#16a34a" stroke-width="2"/>
        </svg>
    """,
    "delete": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 6h18"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
        </svg>
    """,
    "move": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="5 9 2 12 5 15"/>
            <polyline points="9 5 12 2 15 5"/>
            <polyline points="15 19 12 22 9 19"/>
            <polyline points="19 9 22 12 19 15"/>
            <line x1="2" y1="12" x2="22" y2="12"/>
            <line x1="12" y1="2" x2="12" y2="22"/>
        </svg>
    """,
    "rotate": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.85.99 6.57 2.57L21 8"/>
            <polyline points="21 3 21 8 16 8"/>
        </svg>
    """,
    "snapping": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m6 15-4-4 6.75-6.77a7.79 7.79 0 0 1 11 11L13 22l-4-4 6.36-6.36a2.14 2.14 0 0 0-3-3L6 15Z" fill="#fee2e2"/>
        </svg>
    """,

    # ── Compare / Visualization Tools ──────────────────────────
    "swipe": """
        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <!-- Left map panel (Layer A - blue) -->
            <path d="M3 4h8v16H3a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z" fill="#dbeafe" stroke="#2563eb" stroke-width="1.5"/>
            <!-- Right map panel (Layer B - green) -->
            <path d="M13 4h8a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-8V4z" fill="#dcfce7" stroke="#16a34a" stroke-width="1.5"/>
            <!-- Central swipe bar -->
            <line x1="12" y1="2" x2="12" y2="22" stroke="#1e293b" stroke-width="2"/>
            <!-- Center handle knob -->
            <circle cx="12" cy="12" r="3.2" fill="#1e293b" stroke="#ffffff" stroke-width="1.2"/>
            <!-- Opposing interactive swipe arrows (white) -->
            <polygon points="9.5,12 11.2,10.2 11.2,13.8" fill="#ffffff"/>
            <polygon points="14.5,12 12.8,10.2 12.8,13.8" fill="#ffffff"/>
        </svg>
    """,

    "blend_mode": """
        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <!-- Left circle (cyan/blue) -->
            <circle cx="9" cy="12" r="6.2" fill="#60a5fa" fill-opacity="0.75" stroke="#2563eb" stroke-width="1.5"/>
            <!-- Right circle (amber/yellow) -->
            <circle cx="15" cy="12" r="6.2" fill="#fbbf24" fill-opacity="0.75" stroke="#d97706" stroke-width="1.5"/>
            <!-- Blended overlapping lens (emerald) -->
            <path d="M12 7.2 A 6.2 6.2 0 0 1 12 16.8 A 6.2 6.2 0 0 1 12 7.2 Z" fill="#10b981" stroke="#059669" stroke-width="1.2"/>
        </svg>
    """,

    "transpose": """
        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <!-- Table grid border -->
            <rect x="3" y="3" width="18" height="18" rx="2" fill="#f8fafc" stroke="#475569" stroke-width="1.5"/>
            <line x1="3" y1="9" x2="21" y2="9" stroke="#475569" stroke-width="1.2"/>
            <line x1="9" y1="3" x2="9" y2="21" stroke="#475569" stroke-width="1.2"/>
            <!-- Transpose curved swap arrow -->
            <path d="M13 15h5v-5" stroke="#2563eb" stroke-width="1.8"/>
            <path d="M18 15l-5-5" stroke="#2563eb" stroke-width="1.8"/>
            <path d="M11 9H6v5" stroke="#16a34a" stroke-width="1.8"/>
            <path d="M6 9l5 5" stroke="#16a34a" stroke-width="1.8"/>
        </svg>
    """
}
