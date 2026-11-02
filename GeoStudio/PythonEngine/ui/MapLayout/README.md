# GeoStudio — Map Layout & Cartography Module (`app/ui/MapLayout`)

A fully consolidated, modular, professional GIS cartographic composition and publishing workstation module for GeoStudio.

## 1. Directory Structure

```text
app/ui/MapLayout/
├── __init__.py                # Main module entry point and public exports
├── README.md                  # Complete architectural & functional documentation
├── components/                # Core UI composite components
│   ├── __init__.py
│   ├── designer_window.py     # GeoStudioLayoutDesignerWindow (primary workstation)
│   ├── items_dock.py          # LayoutItemsDock (Z-ordering, lock, hierarchy)
│   ├── properties_dock.py     # LayoutPropertiesDock (item properties inspector)
│   ├── settings_tab.py        # LayoutSettingsTab (paper presets, custom size, grids, snaps)
│   ├── guides_tab.py          # GuidesTab (horizontal/vertical guide management)
│   ├── manager_dialog.py      # LayoutManagerDialog (create from template, clone, rename)
│   ├── export_dialog.py       # LayoutExportDialog (multi-format high-res exports)
│   └── print_export_dialog.py # PrintExportDialog (quick canvas & layout export dialog)
├── panels/                    # Dedicated layout inspector and configuration panels
│   ├── __init__.py
│   ├── items_dock.py          # Items tree, Z-order, and lock controls
│   ├── properties_dock.py     # Context-sensitive item inspector
│   ├── settings_tab.py        # Page dimensions, grid resolution, snap tolerance
│   └── guides_tab.py          # Interactive guide positioning and management
├── dialogs/                   # Modal dialog windows
│   ├── __init__.py
│   ├── manager_dialog.py      # Project layout manager and template chooser
│   ├── export_dialog.py       # High-resolution raster & vector exporter
│   └── print_export_dialog.py # Canvas/layout overlay print & export
├── toolbar/                   # Dedicated layout toolbars and palettes
│   ├── __init__.py
│   └── layout_toolbar.py      # Operations bar, navigation & alignment bar, 14-tool palette
├── services/                  # Business logic and rendering engines
│   ├── __init__.py
│   ├── template_service.py    # Cartographic template builder & neatline generator
│   ├── export_service.py      # QgsLayoutExporter execution (PDF, PNG, JPG, TIFF, SVG)
│   ├── overlay_service.py     # Dynamic title, north arrow & scalebar painter routines
│   └── action_service.py      # Geometric alignment (L/R/T/B/C/M) & distribution (H/V)
├── utils/                     # Geometric calculations, conversions & safety guards
│   ├── __init__.py
│   └── layout_utils.py        # Unit conversions (mm/in/px), memory estimation & guards
├── types/                     # Enumerations and typing protocols
│   ├── __init__.py
│   └── layout_types.py        # ExportFormat, AlignmentType, ToolType, PageOrientation
├── constants/                 # Cartographic presets and lookup tables
│   ├── __init__.py
│   └── presets.py             # ISO/ANSI page presets, base sizes, DPI targets
├── styles/                    # Visual styling and design tokens
│   ├── __init__.py
│   └── layout_styles.py       # Off-white palette, dock headers, tab panes, export buttons
├── templates/                 # Resource files and templates
│   └── __init__.py
└── tests/                     # Unit & integration test suite
    ├── __init__.py
    └── test_map_layout.py     # 13 comprehensive unit tests verifying architecture
```

---

## 2. Core Features & Capabilities

### A. Layout Designer Workstation (`GeoStudioLayoutDesignerWindow`)
- **Central Interactive Canvas:** QGIS `QgsLayoutView` with real-time hardware accelerated rendering, pan, zoom, item selection, and drag-to-draw.
- **14 Cartographic Tools:**
  1. Select Item
  2. Move Item Content
  3. Add Map
  4. Add Label / Title
  5. Add Legend
  6. Add Scale Bar
  7. Add North Arrow
  8. Add Image / Logo
  9. Add Table (Attribute table)
  10. Add Shape
  11. Add Line (Polyline)
  12. Add Rectangle
  13. Add Ellipse
  14. Add Arrow
- **Top Menus:** Layout, Edit, View, Items, Add Item, Atlas, Settings, Help.
- **Top Toolbars:** Project/Layout Operations, Navigation & Alignment, Canvas Synchronization.
- **Left Vertical Toolbar:** 14 creation tools with automatic status bar hints.
- **Right Inspector Docks:**
  - Upper: Layout Items tree with Z-order controls + Undo History stack (`QUndoView`).
  - Lower: Layout Settings (page presets, custom mm, grids, snapping) + Item Properties inspector + Guides management.

### B. High-Resolution Multi-Format Exporters
- **LayoutExportDialog:**
  - PDF Document (vector or rasterized for print proofing).
  - High-res PNG, JPEG, TIFF (GeoTIFF), SVG.
  - Resolution presets from 72 DPI up to 1200 DPI.
  - Real-time megapixel calculation and uncompressed memory safety protection (>100 MP warnings).
- **PrintExportDialog:**
  - Instant print preview and export from active layout or live map canvas.
  - Dynamic overlay drawing: title banner, north arrow compass rose, and dynamic scale bar with geodesic/planar distance calculations.

### C. Template Engine (`create_layout_from_template`)
- Ready-to-publish presets: A4/A3/A2/A1/A0 Landscape & Portrait, Map Report, Survey Map, Thematic Map.
- Automated neatline border, primary map frame, title block, scale bar, north arrow, and legend positioning.

### D. Alignment & Geometry Actions (`align_items`, `distribute_items`)
- Align selected items: Left, Right, Top, Bottom, Center, Middle.
- Distribute items evenly: Horizontally and Vertically.

---

## 3. Backward Compatibility

To ensure existing GeoStudio code and legacy modules remain 100% compatible without breakage, lightweight aliases re-export all components:
1. `app.ui.layout.*` -> re-exports from `app.ui.MapLayout`
2. `app.ui.map_layout.*` -> re-exports from `app.ui.MapLayout`
3. `app.MapLayout.*` -> re-exports from `app.ui.MapLayout`
4. `app.ui.print_export_dialog.py` -> re-exports `PrintExportDialog` from `app.ui.MapLayout`
5. `app.ui.print_export_overlays.py` -> re-exports overlay routines from `app.ui.MapLayout`

---

## 4. Verification & Testing

Run the automated test suite:
```bash
python "app/ui/MapLayout/tests/test_map_layout.py"
```

All 13 comprehensive test suites verify:
- Architectural imports & instantiation
- Template generation
- Designer window initialization & dynamic item creation (all 14 tools)
- Layout manager dialog & cloning
- Layout export & print export dialogs
- Alignment & distribution algorithms
- Overlay rendering & geodesic/planar distance calculations
- Properties dock and items dock hierarchy
- Modular subpackages (`services`, `panels`, `dialogs`, `toolbar`, `utils`, `types`, `styles`, `constants`)
- Backward-compatibility aliases
