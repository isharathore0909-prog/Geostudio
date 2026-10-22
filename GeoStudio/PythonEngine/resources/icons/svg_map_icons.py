# -*- coding: utf-8 -*-
"""
GeoStudio - Map & Navigation SVG Icons
"""

MAP_SVGS = {
    # ── Map Tools (Global Mapper Style) ────────────────────────
    "zoom": """
        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <rect x="1" y="1" width="22" height="22" rx="3" fill="#fef08a" stroke="#f59e0b" stroke-width="1.5"/>
            <circle cx="11" cy="11" r="5.5" stroke="#0369a1" stroke-width="2" fill="#e0f2fe"/>
            <line x1="15" y1="15" x2="20" y2="20" stroke="#0369a1" stroke-width="2.5"/>
            <line x1="11" y1="8.5" x2="11" y2="13.5" stroke="#0284c7" stroke-width="1.8"/>
            <line x1="8.5" y1="11" x2="13.5" y2="11" stroke="#0284c7" stroke-width="1.8"/>
            <line x1="4" y1="4" x2="4" y2="8" stroke="#0284c7" stroke-width="1.5"/>
            <line x1="2" y1="6" x2="6" y2="6" stroke="#0284c7" stroke-width="1.5"/>
        </svg>
    """,
    "pan": """
        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 11V6a1.5 1.5 0 0 0-3 0v4M15 10V4a1.5 1.5 0 0 0-3 0v6M12 10.5V5a1.5 1.5 0 0 0-3 0v8M18 8a1.5 1.5 0 1 1 3 0v6a7 7 0 0 1-7 7h-1.5c-2.5 0-4-.8-5.5-2.2l-3-3a1.5 1.5 0 0 1 2.1-2.1L8 14.5" fill="#fef08a" stroke="#b45309" stroke-width="1.6"/>
        </svg>
    """,
    "measure": """
        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 7 7 20l-4-4L16 3l4 4z" fill="#fed7aa" stroke="#c2410c" stroke-width="1.6"/>
            <line x1="8.5" y1="9.5" x2="10.5" y2="11.5" stroke="#c2410c" stroke-width="1.4"/>
            <line x1="12" y1="6" x2="14" y2="8" stroke="#c2410c" stroke-width="1.4"/>
            <line x1="5.5" y1="12.5" x2="7.5" y2="14.5" stroke="#c2410c" stroke-width="1.4"/>
            <circle cx="20.5" cy="5.5" r="2" fill="#0284c7" stroke="#0c4a6e" stroke-width="1"/>
            <circle cx="4.5" cy="20.5" r="2" fill="#0284c7" stroke="#0c4a6e" stroke-width="1"/>
            <line x1="20" y1="6" x2="5" y2="20" stroke="#0284c7" stroke-width="1.4" stroke-dasharray="2 2"/>
        </svg>
    """,
    "identify": """
        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="9.5" fill="#e0f2fe" stroke="#0284c7" stroke-width="2"/>
            <line x1="12" y1="16.5" x2="12" y2="11.5" stroke="#0369a1" stroke-width="2.2"/>
            <circle cx="12" cy="8" r="1.3" fill="#0369a1"/>
        </svg>
    """,
    "profile": """
        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <line x1="2" y1="7" x2="22" y2="7" stroke="#94a3b8" stroke-width="1.2" stroke-dasharray="2 2"/>
            <line x1="2" y1="13" x2="22" y2="13" stroke="#94a3b8" stroke-width="1.2" stroke-dasharray="2 2"/>
            <line x1="2" y1="21" x2="22" y2="21" stroke="#334155" stroke-width="1.8"/>
            <path d="M2 21 8 8l5 6 5-11 4 18H2z" fill="#dcfce7" stroke="#15803d" stroke-width="1.8"/>
        </svg>
    """,
    "viewshed": """
        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="3 14 12 8 21 14 12 12" fill="#f97316" stroke="#c2410c" stroke-width="1.4"/>
            <path d="M2 21 7 13l5 4 6-9 4 13H2z" fill="#dcfce7" stroke="#15803d" stroke-width="1.6"/>
            <line x1="12" y1="3" x2="12" y2="8" stroke="#dc2626" stroke-width="2"/>
        </svg>
    """,
    "digitizer": """
        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 3a2.5 2.5 0 1 1 3.5 3.5L7.5 19.5 2 21l1.5-5.5L17 3z" fill="#fed7aa" stroke="#c2410c" stroke-width="1.6"/>
            <polygon points="2 21 4 15.5 8.5 20" fill="#334155"/>
            <line x1="14.5" y1="5.5" x2="18.5" y2="9.5" stroke="#c2410c" stroke-width="1.5"/>
        </svg>
    """,
    "control_center": """
        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <rect x="1" y="1" width="22" height="22" rx="3" fill="#fef08a" stroke="#f59e0b" stroke-width="1.5"/>
            <rect x="5" y="4" width="14" height="4" rx="1" fill="#f97316" stroke="#c2410c" stroke-width="1.2"/>
            <rect x="5" y="10" width="14" height="4" rx="1" fill="#0284c7" stroke="#0369a1" stroke-width="1.2"/>
            <rect x="5" y="16" width="14" height="4" rx="1" fill="#16a34a" stroke="#15803d" stroke-width="1.2"/>
            <line x1="3" y1="6" x2="5" y2="6" stroke="#475569" stroke-width="1.2"/>
            <line x1="3" y1="12" x2="5" y2="12" stroke="#475569" stroke-width="1.2"/>
            <line x1="3" y1="18" x2="5" y2="18" stroke="#475569" stroke-width="1.2"/>
        </svg>
    """,
    "configure": """
        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" fill="#e0f2fe" stroke="#0369a1" stroke-width="1.8"/>
        </svg>
    """,
    "map_layout": """
        <svg viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" fill="#ffffff" stroke="#0284c7" stroke-width="1.8"/>
            <rect x="6" y="6" width="7" height="7" fill="#dcfce7" stroke="#16a34a" stroke-width="1.2"/>
            <line x1="15" y1="7" x2="19" y2="7" stroke="#64748b" stroke-width="1.4"/>
            <line x1="15" y1="10" x2="19" y2="10" stroke="#64748b" stroke-width="1.4"/>
            <line x1="6" y1="16" x2="19" y2="16" stroke="#64748b" stroke-width="1.4"/>
        </svg>
    """,

    # ── Navigation ─────────────────────────────────────────────
    "zoom_in": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7.5" fill="#e0f2fe"/>
            <line x1="21" y1="21" x2="16.5" y2="16.5" stroke-width="2.5"/>
            <line x1="11" y1="8" x2="11" y2="14" stroke="#16a34a" stroke-width="2"/>
            <line x1="8" y1="11" x2="14" y2="11" stroke="#16a34a" stroke-width="2"/>
        </svg>
    """,
    "zoom_out": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7.5" fill="#e0f2fe"/>
            <line x1="21" y1="21" x2="16.5" y2="16.5" stroke-width="2.5"/>
            <line x1="8" y1="11" x2="14" y2="11" stroke="#dc2626" stroke-width="2"/>
        </svg>
    """,
    "zoom_full": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="9.5" fill="#dcfce7"/>
            <line x1="2.5" y1="12" x2="21.5" y2="12"/>
            <path d="M12 2.5a15 15 0 0 1 4 9.5 15 15 0 0 1-4 9.5 15 15 0 0 1-4-9.5 15 15 0 0 1 4-9.5z"/>
        </svg>
    """,
    "zoom_last": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7.5" fill="#e0f2fe"/>
            <line x1="21" y1="21" x2="16.5" y2="16.5" stroke-width="2.5"/>
            <path d="m12 8-3 3 3 3" stroke="#0369a1" stroke-width="2"/>
            <line x1="9" y1="11" x2="15" y2="11" stroke="#0369a1" stroke-width="2"/>
        </svg>
    """,
    "zoom_next": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7.5" fill="#e0f2fe"/>
            <line x1="21" y1="21" x2="16.5" y2="16.5" stroke-width="2.5"/>
            <path d="m10 8 3 3-3 3" stroke="#0369a1" stroke-width="2"/>
            <line x1="7" y1="11" x2="13" y2="11" stroke="#0369a1" stroke-width="2"/>
        </svg>
    """,
    "undo": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 14 4 9l5-5"/>
            <path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5v1a5.5 5.5 0 0 1-5.5 5.5H11"/>
        </svg>
    """,
    "redo": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m15 14 5-5-5-5"/>
            <path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5v1A5.5 5.5 0 0 0 9.5 21H13"/>
        </svg>
    """,
    "refresh": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3L21.5 8M22 12.5a10 10 0 0 1-18.8 4.2L2.5 16"/>
        </svg>
    """,

    # ── Identify / Selection ───────────────────────────────────
    "select": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m3 3 7 18 3-7 7-3L3 3z" fill="#dbeafe"/>
        </svg>
    """,
    "select_rect": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-dasharray="3 3">
            <rect x="3" y="3" width="18" height="18" rx="2" fill="#eff6ff"/>
        </svg>
    """,
    "select_poly": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-dasharray="3 3">
            <polygon points="12 2 22 8.5 18 20 6 20 2 8.5" fill="#eff6ff"/>
        </svg>
    """,
    "select_radius": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-dasharray="3 3">
            <circle cx="12" cy="12" r="9" fill="#eff6ff"/>
            <line x1="12" y1="12" x2="21" y2="12" stroke-dasharray="none" stroke="#2563eb"/>
        </svg>
    """,
    "clear_selection": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" fill="#fef2f2"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
        </svg>
    """,

    # ── Measurement ────────────────────────────────────────────
    "measure_dist": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21.3 8.7 8.7 21.3a1 1 0 0 1-1.4 0L2.7 16.7a1 1 0 0 1 0-1.4L15.3 2.7a1 1 0 0 1 1.4 0l4.6 4.6a1 1 0 0 1 0 1.4z" fill="#fef3c7"/>
            <line x1="7.5" y1="10.5" x2="9" y2="12"/>
            <line x1="10.5" y1="7.5" x2="12" y2="9"/>
            <line x1="13.5" y1="4.5" x2="15" y2="6"/>
        </svg>
    """,
    "measure_area": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="3 6 14 2 21 10 17 21 6 18" fill="#fef3c7"/>
            <circle cx="3" cy="6" r="2" fill="#d97706"/>
            <circle cx="14" cy="2" r="2" fill="#d97706"/>
            <circle cx="21" cy="10" r="2" fill="#d97706"/>
            <circle cx="17" cy="21" r="2" fill="#d97706"/>
            <circle cx="6" cy="18" r="2" fill="#d97706"/>
        </svg>
    """,
    "measure_angle": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="21 20 4 20 16 4"/>
            <path d="M12 20a8 8 0 0 0-4-7" stroke-dasharray="2 2"/>
        </svg>
    """,
    "coord_capture": """
        <svg viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="9.5" fill="#fef3c7"/>
            <line x1="22" y1="12" x2="18" y2="12"/>
            <line x1="6" y1="12" x2="2" y2="12"/>
            <line x1="12" y1="6" x2="12" y2="2"/>
            <line x1="12" y1="22" x2="12" y2="18"/>
            <circle cx="12" cy="12" r="2" fill="#d97706"/>
        </svg>
    """
}
