# GeoStudio v1.0.0 — Standalone High-Performance GIS

[![Platform: Windows x64](https://img.shields.io/badge/Platform-Windows%20x64-blue.svg)](#)
[![Runtime: .NET 8 WPF](https://img.shields.io/badge/Runtime-.NET%208%20WPF-purple.svg)](#)
[![Map Engine: WebGL / OpenLayers](https://img.shields.io/badge/Engine-WebGL%20%2F%20OpenLayers-green.svg)](#)
[![Spatial DB: DuckDB Columnar](https://img.shields.io/badge/Spatial%20DB-DuckDB%201.5.6-yellow.svg)](#)
[![Raster Engine: GDAL 3.13](https://img.shields.io/badge/Raster%20Engine-GDAL%203.13-orange.svg)](#)

**GeoStudio** is a high-performance, standalone GIS desktop application developed in **C# / .NET 8 (WPF)** with an integrated **GPU-accelerated WebGL / OpenLayers map engine**. It is engineered to load, process, stream, and visualize massive geospatial datasets with sub-second viewport responsiveness—handling **100 GB+ BigTIFF / GeoTIFF rasters**, **multi-million point ASPRS LiDAR clouds (LAS/LAZ)**, and **interactive vector layers** completely offline or with hybrid online basemaps.

---

## 📑 Table of Contents

1. [Architectural Overview](#-architectural-overview)
2. [Component Architecture & Technology Stack](#-component-architecture--technology-stack)
3. [User Interface & Ribbon Design](#-user-interface--ribbon-design)
4. [Raster Processing Engine (100 GB+ BigTIFF)](#-raster-processing-engine-100-gb-bigtiff)
5. [LiDAR & Point Cloud Engine (DuckDB Columnar)](#-lidar--point-cloud-engine-duckdb-columnar)
6. [Vector Digitizing, Snapping & Measurement](#-vector-digitizing-snapping--measurement)
7. [Inter-Process Communication (IPC) Protocol](#-inter-process-communication-ipc-protocol)
8. [Data, Cache & Memory Lifecycle Management](#-data-cache--memory-lifecycle-management)
9. [Scientific, Hydrological & Rule-Based Formulas](#-scientific-hydrological--rule-based-formulas)
10. [Project Structure](#-project-structure)
11. [Prerequisites & Build Instructions](#-prerequisites--build-instructions)
12. [Performance Benchmarks & Optimizations](#-performance-benchmarks--optimizations)
13. [Troubleshooting Guide](#-troubleshooting-guide)

---

## 🏛️ Architectural Overview

GeoStudio separates UI layout, native spatial data processing, and GPU rendering into decoupled, cooperative subsystems:

```mermaid
graph TB
    subgraph "Desktop Host (.NET 8 WPF)"
        UI[WPF Ribbon & Layer Panel]
        Bridge[WebView2 Core Controller]
        GDAL[GdalRasterService<br/>MaxRev GDAL 3.13 Native Core]
        DuckDB[DuckDbPointCloudService<br/>DuckDB Embedded Columnar DB]
        SurfRast[LasSurfaceRasterizerService<br/>IDW / Grid Interpolation]
        CacheMgr[Cache Lifecycle & Pruning Engine]
    end

    subgraph "Hardware & Disk Subsystem"
        DiskRast[(100GB+ BigTIFF / GeoTIFF Files)]
        DiskLas[(ASPRS LAS 1.0 - 1.4 Files)]
        AppData[(%LOCALAPPDATA%/GeoStudio/Cache)]
    end

    subgraph "Client Map Engine (WebView2 / Chromium)"
        OL[OpenLayers 8+ WebGL Canvas]
        PCShader[Custom WebGL Point Cloud Overlay]
        Digitizer[Interactive Vector & Snapping Engine]
        Telemetry[Hardware Telemetry & Frame Profiler]
    end

    UI --> Bridge
    Bridge <==>|JSON IPC via postMessage / WebMessageReceived| OL
    
    DiskRast -->|Memory-Mapped Windows / VSI Cache| GDAL
    DiskLas -->|Direct Binary Ingestion| DuckDB
    DuckDB --> SurfRast
    SurfRast --> GDAL
    
    GDAL -->|Low-Res Pyramids & Dynamic Viewport Tiles| AppData
    AppData -->|file:/// or Data URIs| OL
    DuckDB -->|LOD Sampled Batches (X, Y, Z, R, G, B, Class, Intensity)| PCShader
    Telemetry -->|FPS / Redraw Time / Zoom Telemetry| UI
    CacheMgr -->|Auto-prune old win_* and overview_* files| AppData
```

### Core Design Principles
1. **Zero Out-of-Memory (OOM) Crashes**: Multi-gigabyte rasters and multi-million point clouds never load uncompressed into system RAM.
2. **Two-Tier Visual Progression**: Rasters load instantly using downsampled overview pyramids, seamlessly transitioning to viewport-bounded high-resolution window queries upon camera stabilization.
3. **Columnar Point Cloud Queries**: Millions of ASPRS LiDAR records are ingested into an in-process, zero-copy DuckDB database, enabling spatial bbox queries and classification filtering with sub-millisecond execution.
4. **Hardware-Accelerated WebGL Rendering**: OpenLayers renders raster and vector layers on WebGL contexts, while a dedicated floating WebGL canvas plots dense point clouds at 60 FPS.
5. **Air-Gapped & Offline Safety**: The map engine includes offline cartographic graticules and fallback procedural canvases, ensuring functionality in isolated networks.

---

## 💻 Component Architecture & Technology Stack

### Technology Stack Matrix

| Layer | Component / Library | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Desktop Host** | .NET WPF (Windows x64) | 8.0 | Native desktop shell, ribbon interface, layer management, threading |
| **Raster Engine** | `MaxRev.Gdal.Core` / Windows Runtime | 3.13.3.580 | Native C++ GDAL bindings, coordinate transformation (OSR), VSI caching |
| **Point Cloud DB** | `DuckDB.NET.Data.Full` | 1.5.6 | Embedded in-memory columnar database for fast spatial bbox point slicing |
| **Embedded Browser**| `Microsoft.Web.WebView2` | 1.0.4258.31 | High-performance Chromium web engine bridging C# to WebGL |
| **Cartographic Engine**| OpenLayers (`ol.js`, `ol.css`) | 8.2+ | Tiled web map rendering, vector topology, interaction tools, reprojection |
| **GeoTIFF Parser** | `geotiff.js` | 2.1+ | Client-side Cloud-Optimized GeoTIFF (COG) reading and raster decoding |
| **Shaders / Canvas**| WebGL 1.0 / 2.0 | Native | Custom elevation ramps, intensity shading, and point cloud visualization |

---

## 🎨 User Interface & Ribbon Design

The user interface follows modern GIS standards (inspired by ArcGIS Pro and QGIS 3), featuring a categorized fluent ribbon bar, left dockable layer management sidebar, WebGL central viewport, and real-time telemetry status bar.

```
+----------------------------------------------------------------------------------------------------+
|  GeoStudio v1.0.0 — Standalone GIS                                                    [-] [口] [X] |
+----------------------------------------------------------------------------------------------------+
| [PROJECT]   [NAVIGATION]   [DATA SOURCES]    [SELECTION]   [MEASURE]   [TERRAIN]   [LiDAR]   [DIGITIZE]|
| New Open    Pan Zoom Full  Vector BigTIFF    Info Rect     Dist Area   Shader ▾    Load LAS  Point Line|
| Save Print  Extent Refresh WebTiles DB Local Clear Poly    Angle       Profile 3D  ColorBy▾  Poly Snapp|
+-------------------+--------------------------------------------------------------------------------+
| LAYERS            |                                                                                |
| [🔍 Search...]    |                                                                                |
| ----------------- |                                                                                |
| [x] ⛰️ Orthomosaic|                               WEBGL MAP VIEWPORT                               |
|     Opacity: ===  |                                                                                |
|     100 GB BigTIFF|                        (Hardware-Accelerated OpenLayers Canvas)                |
|                   |                                                                                |
| [x] 📡 LiDAR 2026 |                                                                                |
|     Opacity: ===  |                                                                                |
|     8.4M Points   |                                                                                |
|                   |                                                                                |
| [x] 🌐 Basemap    |                                                                                |
+-------------------+--------------------------------------------------------------------------------+
| ⌖ X: 77.2090  Y: 28.6139 | ⛰️ Elev: 216 m | Scale: 1:25,000 | CRS: EPSG:4326 | 🟢 60 FPS (1.6ms)  |
+----------------------------------------------------------------------------------------------------+
```

### Ribbon Categories & Toolset

1. **PROJECT**:
   - **New**: Resets current workspace and purges transient layers.
   - **Open**: Opens raster, vector, or point cloud files with format auto-detection.
   - **Save**: Saves workspace layer composition and camera view state.
   - **Print / Export**: Exports current viewport to high-resolution georeferenced PNG/PDF.
2. **NAVIGATION**:
   - **Pan (`pan`)**: Default navigation tool. Drag to pan, scroll to zoom.
   - **Zoom In / Zoom Out**: Step zoom operations.
   - **Full Extent**: Fits map view to the collective bounding box of all active layers.
   - **Split / Compare**: Enables swipe-to-compare between overlapping rasters.
   - **Refresh**: Invalidates local tile cache and forces WebGL redraw.
3. **DATA SOURCES**:
   - **Vector**: Imports Shapefiles (`.shp`), GeoJSON (`.geojson`), and GeoPackage (`.gpkg`).
   - **BigTIFF / Raster**: Opens single and multi-band GeoTIFF, BigTIFF, DEM, Orthomosaic, and Satellite imagery (`.tif`, `.tiff`, `.vrt`, `.img`).
   - **Web Tiles**: Connects to XYZ, TMS, and WMS tile services.
   - **Spatial Database**: Connects to PostGIS, SpatiaLite, or local DuckDB spatial stores.
4. **SELECTION & QUERY**:
   - **Identify (`info`)**: Click to inspect pixel values, elevations, or vector attributes.
   - **Selection Modes**: Pointer, Bounding Rectangle, Polygon Select, Radius Circle.
   - **Clear**: Discards current selection highlights.
5. **MEASUREMENT**:
   - **Distance (`distance`)**: Interactive multi-segment ruler with real-time geodesic length in meters/kilometers.
   - **Area (`area`)**: Real-time geodesic area calculation in $m^2$, hectares, or $km^2$.
   - **Angle / Bearing**: Computes azimuth and slope angles between picked points.
6. **TERRAIN / ELEVATION**:
   - **Shader Modes**: Real-time hillshading, slope analysis, aspect, and hypsometric color ramps.
   - **Profile Tool**: Samples elevation along an interactive polyline to plot cross-sectional profiles.
   - **3D Surface**: Generates interactive 3D terrain wireframes using DEM rasters.
7. **LIDAR / POINT CLOUD**:
   - **Load LAS/LAZ**: Direct ingest of ASPRS LAS 1.0–1.4 files.
   - **Color Modes**: Elevation (Z), Intensity, Classification, True Color RGB, Return Number.
   - **Point Filters**: Filter points by ASPRS classification (Ground, High Veg, Buildings, Water).
   - **Rasterize Surface**: Converts raw LiDAR points into a gridded Digital Surface Model (DSM).
8. **DIGITIZING & TOPOLOGY**:
   - **Geometry Types**: Point, Polyline, Polygon, Circle, Freehand.
   - **Vertex Move Tool**: Interactive node manipulation with vertex addition and deletion.
   - **Snapping Engine**: Multi-mode snapping (`Vertex`, `Edge`, `Midpoint`) with configurable pixel tolerance.

---

## ⚡ Raster Processing Engine (100 GB+ BigTIFF)

### The Large-Raster Problem
Standard desktop GIS software often attempts to read raster files sequentially into RAM. A 100 GB 4-band aerial orthomosaic ($25,000 \times 28,000$ to $100,000 \times 100,000$ pixels) decompressing Deflate or LZW blocks will immediately cause Out-of-Memory exceptions or system freezes.

### GeoStudio Solution Architecture
GeoStudio handles massive rasters using [GdalRasterService.cs](file:///d:/GEO%20MAP/GeoStudio/Services/GdalRasterService.cs):

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Host as GeoStudio WPF Host
    participant GDAL as GdalRasterService (Native)
    participant Cache as Local SSD Cache
    participant WebGL as WebGL Map Engine

    User->>Host: Open 100GB+ BigTIFF
    Host->>GDAL: InspectMetadata(filePath)
    GDAL-->>Host: Dimensions, Bands, Bounding Box (EPSG:4326)
    Host->>GDAL: InspectAndGeneratePreview(filePath)
    alt Overview Pyramid (.ovr) Exists
        GDAL->>Cache: Extract 4096px downsampled overview
    else No Overviews Present
        GDAL->>GDAL: Subsampled single-pass decimation (Fast Scan)
        GDAL->>Cache: Save overview_*.jpg / png
        Host->>GDAL: QueueOverviewGeneration() (Background Thread)
    end
    Cache-->>WebGL: Load Base Raster Image Layer
    WebGL-->>User: Instant Display (< 1.5 seconds)

    loop Viewport Navigation (Pan / Zoom)
        User->>WebGL: Pan or Zoom In
        WebGL->>Host: requestRasterWindow(bounds, screenW, screenH)
        Host->>GDAL: RenderWindow(bounds, screenW, screenH)
        GDAL->>GDAL: Compute RasterIO window coordinates & downsample factor
        GDAL->>Cache: Write win_[hash].jpg
        Cache-->>WebGL: updateRasterWindow(imageUrl, bounds)
        WebGL-->>User: Seamless High-Resolution Tile Display
    end
```

### Key Technical Innovations in `GdalRasterService`

1. **Configured Memory & Threading Pool**:
   ```csharp
   GdalBase.ConfigureAll();
   Gdal.SetConfigOption("GDAL_CACHEMAX", "1024");             // 1 GB internal block cache
   Gdal.SetConfigOption("GDAL_RASTERIO_RESAMPLING", "NEAREST"); // Ultra-fast decimation
   Gdal.SetConfigOption("GDAL_NUM_THREADS", "ALL_CPUS");       // Parallel decompression
   Gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR");
   Gdal.SetConfigOption("VSI_CACHE", "TRUE");
   Gdal.SetConfigOption("VSI_CACHE_SIZE", "67108864");         // 64 MB virtual file cache
   ```

2. **CRS Transformation to EPSG:4326**:
   The engine reads native geotransforms (`GetGeoTransform`), projects bounding extents using `SpatialReference` and `CoordinateTransformation` with `SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER)`, and ensures precise geodetic registration against global basemaps.

3. **Dynamic Viewport Window Rendering (`RenderWindow`)**:
   Instead of loading the entire image, when the user zooms into a localized area, `RenderWindow()`:
   - Converts geodetic longitude/latitude bounds back into native dataset pixel coordinates ($X_{pixel}, Y_{pixel}, W_{pixel}, H_{pixel}$).
   - Computes target output resolution matching the physical monitor viewport ($W_{screen} \times H_{screen}$).
   - Executes `band.ReadRaster()` with on-the-fly decimation, reading only the required blocks from disk.
   - Encodes the buffer to JPEG using WPF `JpegBitmapEncoder` (Quality = 85) for minimal latency and disk footprint.

4. **Background Overview Pyramid Builder**:
   If an uploaded GeoTIFF lacks internal overviews, the system launches a background task that calls `ds.BuildOverviews("NEAREST", new int[] { 2, 4, 8, 16, 32, 64 })`, generating external `.ovr` pyramids without locking the primary UI thread.

---

## 📡 LiDAR & Point Cloud Engine (DuckDB Columnar)

### The LiDAR Volume Challenge
Modern airborne or terrestrial LiDAR surveys easily encompass $10^7$ to $10^9$ points with attributes: $X, Y, Z$, Intensity, Return Number, Classification, Scan Angle, and RGB. Rendering this volume directly in JavaScript freezes web browsers.

### GeoStudio Solution Architecture
GeoStudio combines native binary streaming with an embedded columnar database in [DuckDbPointCloudService.cs](file:///d:/GEO%20MAP/GeoStudio/Services/DuckDbPointCloudService.cs) and GPU WebGL shaders in [index.html](file:///d:/GEO%20MAP/GeoStudio/Resources/MapEngine/index.html):

```
+-------------------------------------------------------------+
|                      ASPRS LAS / LAZ File                   |
|           Header: Offsets, Scales, BBox, Total Points       |
+-------------------------------------------------------------+
                              |
                     Binary Stream Reader
                              |
                              v
+-------------------------------------------------------------+
|                Embedded DuckDB Columnar Store               |
|  TABLE las_points (                                         |
|      x DOUBLE, y DOUBLE, z FLOAT,                           |
|      intensity USMALLINT, return_num UTINYINT,              |
|      classification UTINYINT, r USMALLINT, g, b             |
|  )                                                          |
|  INDEX: Z-Order / Min-Max Spatial Pruning                   |
+-------------------------------------------------------------+
        |                                             |
   Full Extent                               View Zoom / Pan
        |                                             |
        v                                             v
+------------------------------------+   +------------------------------------+
|        Overview Batch              |   |       Spatial Viewport Batch       |
|  SELECT * USING RESERVOIR SAMPLING |   |  SELECT * WHERE x BETWEEN...       |
|  LIMIT 500,000 Points              |   |  AND y BETWEEN... LIMIT 500,000    |
+------------------------------------+   +------------------------------------+
                     \                               /
                      v                             v
               +-------------------------------------------+
               | Inter-Process Columnar Batch Transfer     |
               | Typed Arrays: Float32 (Z), Int32 (Coords) |
               +-------------------------------------------+
                                     |
                                     v
               +-------------------------------------------+
               | WebGL Floating Point Cloud Canvas         |
               | - Dynamic Hypsometric Elevation Ramp      |
               | - Sensor Intensity Shader                 |
               | - ASPRS Standard Classification Colors    |
               +-------------------------------------------+
```

### ASPRS Classification Legend

| Code | Classification | Default Visualization Color |
| :---: | :--- | :--- |
| `0` / `1` | Created / Unclassified | Gray (`#94A3B8`) |
| `2` | Ground | Warm Brown / Earth (`#B45309`) |
| `3` | Low Vegetation | Light Green (`#86EFAC`) |
| `4` | Medium Vegetation | Medium Green (`#22C55E`) |
| `5` | High Vegetation | Forest Green (`#15803D`) |
| `6` | Building / Structure | Crimson Red (`#EF4444`) |
| `7` | Low Point (Noise) | Violet (`#A855F7`) |
| `9` | Water | Deep Blue (`#3B82F6`) |
| `13` / `14`| Wire Guard / Conductor | Amber (`#F59E0B`) |
| `17` | Bridge Deck | Slate (`#64748B`) |

### Surface Rasterization (`LasSurfaceRasterizerService.cs`)
When digital elevation models are required from raw LiDAR points, GeoStudio provides an on-demand surface rasterizer:
1. Grids point cloud bounds into a user-specified raster grid ($2048 \times 2048$ to $8192 \times 8192$).
2. Applies **Inverse Distance Weighting (IDW)** or nearest-neighbor interpolation to compute continuous surface heights.
3. Automatically writes a georeferenced 32-bit floating-point GeoTIFF (`.tif`) that can be draped or analyzed as a DEM raster.

---

## ✏️ Vector Digitizing, Snapping & Measurement

GeoStudio includes an interactive vector digitizing suite operating within the OpenLayers engine with two-way synchronization to the WPF `Layers` panel:

### Digitizing Tools
- **Add Point (`Point`)**: Snaps and records point features with automatic coordinate registration.
- **Add Line (`LineString`)**: Multi-segment line recording with dynamic length tooltip and vertex snapping.
- **Add Polygon (`Polygon`)**: Closed polygon digitizing with real-time geodesic area calculation.
- **Modify / Move Vertex**: Select any digitized geometry to drag individual vertices, insert new vertices at midpoints, or delete vertices via `Alt + Click`.

### Intelligent Snapping Engine
The snapping engine operates across all active vector and digitized layers:
- **Snapping Modes**: `Vertex`, `Edge`, and `Midpoint`.
- **Pixel Tolerance**: Configurable radius (default: `12px`). When the cursor approaches an existing geometry within the tolerance threshold, the cursor automatically locks onto the target node with a visual snap marker.

### Geodesic Measurement System
- **Distance**: Calculates WGS84 ellipsoidal distance using Haversine and Vincenty equations across line segments.
- **Area**: Computes geodesic polygon area, automatically converting values into square meters ($m^2$), hectares ($ha$), or square kilometers ($km^2$).
- **Tooltips**: Dynamic, floating DOM overlays display real-time dimensions during drawing and remain pinned upon sketch completion.

---

## 🔌 Inter-Process Communication (IPC) Protocol

The communication bridge between the .NET 8 WPF Host (`MainWindow.xaml.cs`) and the WebGL Chromium Map Engine (`index.html`) operates via asynchronous JSON messages over WebView2:

### 1. Host $\rightarrow$ Map Engine Commands (`PostMessageToMap`)

| Action | Payload Parameters | Description |
| :--- | :--- | :--- |
| `loadRaster` | `layerId`, `name`, `bounds`, `previewUrl`, `width`, `height` | Initializes a new raster layer with overview image and bounding box |
| `updateRasterWindow` | `layerId`, `imageUrl`, `bounds` | Updates high-resolution raster viewport tile after camera pan/zoom |
| `loadPointCloud` | `stats`, `points` (initial batch) | Registers point cloud dataset, sets camera extent, loads initial points |
| `updatePointCloud` | `batch` (`{ count, x, y, z, r, g, b, c, i }`) | Transmits columnar point batch to WebGL canvas buffer |
| `setPointCloudColorMode`| `mode` (`'elevation' \| 'intensity' \| 'classification' \| 'rgb'`) | Changes WebGL point cloud fragment shader coloring mode |
| `filterClassification` | `classification` (int or null) | Restricts point cloud rendering to specific ASPRS class |
| `setLayerVisibility` | `id`, `visible` | Toggles rendering of specified layer ID |
| `setLayerOpacity` | `id`, `opacity` (0.0 to 1.0) | Adjusts alpha opacity of specified layer ID |
| `removeLayer` | `id`, `type` | Deletes layer from map context and frees associated GPU resources |
| `setTool` | `tool` (`'pan' \| 'distance' \| 'area' \| 'point' \| 'line' \| 'polygon'`) | Activates navigation, measurement, or digitizing interaction |
| `zoomIn` / `zoomOut` | *(none)* | Triggers smooth stepped viewport zoom |
| `zoomToExtent` | `bounds` (`[minX, minY, maxX, maxY]`) | Fits camera to specified geographic envelope |
| `setBasemap` | `basemap` (`'osm' \| 'satellite' \| 'none'`) | Switches global basemap provider |
| `toggleSnapping` | `enabled` (boolean) | Enables or disables snapping on digitizing tools |

### 2. Map Engine $\rightarrow$ Host Telemetry (`postToHost`)

| Action | Payload Parameters | Description |
| :--- | :--- | :--- |
| `ready` | *(none)* | Emitted when OpenLayers and WebGL contexts are fully initialized |
| `pointerMove` | `lon`, `lat`, `elev`, `scale` | Emitted on mouse move; updates status bar coordinates and scale |
| `viewportTelemetry` | `activity`, `zoom`, `redrawMs`, `fps`, `frameTimeMs`, `activeElements` | Emitted every frame; powers real-time GPU performance monitors |
| `gpuInfo` | `gpuRenderer` | Reports hardware GPU model (e.g., `NVIDIA GeForce RTX 4090 / D3D11`) |
| `requestRasterWindow`| `bounds`, `screenW`, `screenH`, `filePath`, `layerId` | Requests high-res tile decimation when viewport stabilizes |
| `queryPointCloudViewport`| `bounds`, `classification` | Requests point cloud LOD batch matching active viewport bounding box |
| `digitizedFeature` | `type`, `count` | Notifies host of newly completed vector sketch |

---

## 💾 Data, Cache & Memory Lifecycle Management

### Cache Location
To preserve workspace cleanlines and avoid polluting project repositories, all runtime temporary files, decimated viewports, and overview pyramids are isolated in the user's local application data directory:
```
%LOCALAPPDATA%\GeoStudio\Cache\
├── overview_[hash].jpg       # Pre-rendered 4096px overview pyramids
├── win_[hash].jpg            # Dynamic viewport window tiles
└── dsm_[hash].tif            # Generated LiDAR surface elevation rasters
```

### Automatic Cache Pruning (`PruneCache`)
To prevent unbounded disk consumption during extended GIS analysis sessions, `GdalRasterService.PruneCache()` runs automatically in the background:
- **Viewport Windows (`win_*`)**: Retains only the **4 most recent** viewport window captures; older files are pruned.
- **Overviews (`overview_*`)**: Retains the **8 most recently accessed** overview rasters based on `LastWriteTimeUtc`.

### Complete Layer Removal Cleanup
When a user removes a raster or point cloud layer from the `Layers` panel:
1. `MainWindow.xaml.cs` cancels all active asynchronous decoding tasks (`_rasterCts?.Cancel()`).
2. Dispatches `removeLayer` IPC message to the map engine to release GPU WebGL textures and vertex buffers.
3. If all data layers are closed, calls `GdalRasterService.ClearCache()` and `DuckDbPointCloudService.Clear()`, flushing unmanaged RAM and releasing dataset file locks.

---

## 📐 Scientific, Hydrological & Rule-Based Formulas

GeoStudio implements calibrated, peer-reviewed mathematical formulations, decision-tree rules, and physical models across all analysis pipelines:

```
                               GEOSTUDIO ANALYTICAL FORMULA MATRIX
+------------------------------------+------------------------------------+------------------------------------+
|   REMOTE SENSING & THERMAL         |   HYDROLOGY & ARTIFICIAL RECHARGE  |   TERRAIN, EARTHWORKS & LIDAR      |
| • NDVI, NDWI, MNDWI, EVI, NDBI     | • Barnes Priority-Flood Sink Fill  | • Central Difference 3D Gradients  |
| • Sobrino & Du Split-Window LST    | • D8 Flow Routing (Garbrecht-Martz)| • Multi-Source Lambertian Hillshade|
| • Planck Brightness Temperature    | • CGWB 2007/2020 Recharge Siting   | • Factored Cut & Fill & Bisection  |
| • Fractional Vegetation Cover (FVC)| • Strange's Table Catchment Yield  | • SMRF Filter & HAG Delaunay TIN   |
| • 22-Class LULC Decision Engine    | • FAO-56 Crop Water Planner (WAI)  | • Geodesic Haversine & A* Routing  |
+------------------------------------+------------------------------------+------------------------------------+
```

---

### 1. Remote Sensing & Multispectral Indices

Calculated across multispectral rasters (Landsat 8/9 OLI, Sentinel-2 MSI) via [raster_tasks.py](file:///d:/GEO%20MAP/GeoStudio/Python/PythonPipeline/tasks/raster_tasks.py) and [spectral_helpers.py](file:///d:/GEO%20MAP/GeoStudio/Python/PythonPipeline/tasks/spectral_helpers.py):

#### A. Normalized Difference Vegetation Index (NDVI)
$$
\text{NDVI} = \frac{\rho_{\text{NIR}} - \rho_{\text{Red}}}{\rho_{\text{NIR}} + \rho_{\text{Red}} + \epsilon}
$$
- **Bands**: Sentinel-2 ($B_8, B_4$), Landsat 8/9 ($B_5, B_4$).
- **Range**: $[-1.0, 1.0]$. Dense green canopy $\ge 0.45$, sparse/scrub $0.20 - 0.40$, barren rock/soil $< 0.20$, water $< 0$.
- $\epsilon = 10^{-6}$ prevents zero-division singularities over masked/nodata water pixels.

#### B. Normalized Difference Water Index (NDWI — McFeeters 1996)
$$
\text{NDWI} = \frac{\rho_{\text{Green}} - \rho_{\text{NIR}}}{\rho_{\text{Green}} + \rho_{\text{NIR}} + \epsilon}
$$
- **Bands**: Sentinel-2 ($B_3, B_8$), Landsat 8/9 ($B_3, B_5$).
- Pure open water features yield $\text{NDWI} > 0.0$; terrestrial vegetation and bare earth yield negative values.

#### C. Modified Normalized Difference Water Index (MNDWI — Xu 2006)
$$
\text{MNDWI} = \frac{\rho_{\text{Green}} - \rho_{\text{SWIR1}}}{\rho_{\text{Green}} + \rho_{\text{SWIR1}} + \epsilon}
$$
- **Bands**: Sentinel-2 ($B_3, B_{11}$), Landsat 8/9 ($B_3, B_6$).
- Replaces NIR with SWIR1 to suppress built-up urban noise and separate turbid water bodies from asphalt/concrete.

#### D. Enhanced Vegetation Index (EVI — Huete et al. 2002)
$$
\text{EVI} = 2.5 \cdot \frac{\rho_{\text{NIR}} - \rho_{\text{Red}}}{\rho_{\text{NIR}} + 6.0 \cdot \rho_{\text{Red}} - 7.5 \cdot \rho_{\text{Blue}} + 1.0}
$$
- Corrects for atmospheric aerosol scattering and soil background reflectance. Clamped to $[-1.5, 1.5]$.

#### E. Normalized Difference Built-Up Index (NDBI — Zha et al. 2003)
$$
\text{NDBI} = \frac{\rho_{\text{SWIR1}} - \rho_{\text{NIR}}}{\rho_{\text{SWIR1}} + \rho_{\text{NIR}} + \epsilon}
$$
- Highlights urban settlements, impervious roads, and industrial structures ($\text{NDBI} > 0$).

#### F. Normalized Burn Ratio (NBR — Key & Benson 2006)
$$
\text{NBR} = \frac{\rho_{\text{NIR}} - \rho_{\text{SWIR2}}}{\rho_{\text{NIR}} + \rho_{\text{SWIR2}} + \epsilon}
$$
- **Bands**: Sentinel-2 ($B_8, B_{12}$), Landsat 8/9 ($B_5, B_7$). Used for wildfire burn severity and fire scar perimeter delineation.

#### G. Bare Soil Index (BSI — Rikimaru et al. 2002)
$$
\text{BSI} = \frac{(\rho_{\text{SWIR1}} + \rho_{\text{Red}}) - (\rho_{\text{NIR}} + \rho_{\text{Blue}})}{(\rho_{\text{SWIR1}} + \rho_{\text{Red}}) + (\rho_{\text{NIR}} + \rho_{\text{Blue}}) + \epsilon}
$$

#### H. Tasseled Cap Wetness (TCW — Sentinel-2 MSI Crist Orthogonal Transform)
$$
\text{TCW} = 0.1509 B_2 + 0.1973 B_3 + 0.3279 B_4 + 0.3406 B_8 - 0.7112 B_{11} - 0.4572 B_{12}
$$

#### I. False-Color Infrared Dynamic Range Stretch
False-Color composites map $R \leftarrow \text{NIR}$, $G \leftarrow \text{Red}$, $B \leftarrow \text{Green}$ using a cumulative 2%–98% percentile linear contrast stretch:
$$
\text{DN}_{\text{out}} = \text{clip}\left(\frac{\text{DN} - P_{2\%}}{P_{98\%} - P_{2\%}} \cdot 255.0,\, 0,\, 255\right)
$$

---

### 2. Thermal Remote Sensing & Land Surface Temperature (LST)

Implemented in [landsat_tasks.py](file:///d:/GEO%20MAP/GeoStudio/Python/PythonPipeline/tasks/landsat_tasks.py) following USGS Landsat Collection 2 Level 1 calibration:

#### A. Top of Atmosphere (TOA) Spectral Radiance ($L_\lambda$)
$$
L_\lambda = M_L \cdot Q_{\text{cal}} + A_L
$$
- $Q_{\text{cal}}$: Calibrated digital number (DN).
- $M_L, A_L$: Band-specific radiance multiplicative and additive rescaling factors from scene `*_MTL.txt` (typically $M_{L,10} = 0.000380$, $A_{L,10} = 0.1$).

#### B. TOA Planetary Reflectance with Solar Angle Correction ($\rho_\lambda$)
$$
\rho_\lambda = \frac{M_\rho \cdot Q_{\text{cal}} + A_\rho}{\sin(\theta_{\text{SE}})} \cdot \frac{1}{\exp(-\tau_\lambda \cdot \text{Ozone})}
$$
- $\theta_{\text{SE}}$: Solar elevation angle in degrees ($\theta_{\text{SE}} = 90^\circ - \theta_{\text{SZA}}$).
- $\tau_\lambda$: Atmospheric ozone optical depth correction ($0.1133$ for Band 4, $0.012$ for Band 5).

#### C. At-Satellite Brightness Temperature ($T_B$)
Inverted Planck radiation function:
$$
T_B = \frac{K_2}{\ln\left(\frac{K_1}{L_\lambda} + 1\right)} - 273.15 \quad [^\circ\text{C}]
$$
- **TIRS Band 10**: $K_1 = 774.8853\,\text{W}/(\text{m}^2\cdot\text{sr}\cdot\mu\text{m})$, $K_2 = 1321.0789\,\text{K}$ (USGS Collection 2: $799.0284$ / $1329.2482$).
- **TIRS Band 11**: $K_1 = 480.8883\,\text{W}/(\text{m}^2\cdot\text{sr}\cdot\mu\text{m})$, $K_2 = 1201.1442\,\text{K}$ (USGS Collection 2: $497.6190$ / $1198.8194$).

#### D. Fractional Vegetation Cover ($P_v$ / FVC — Carlson & Ripley 1997)
$$
P_v = \left[\frac{\text{NDVI} - \text{NDVI}_{\text{min}}}{\text{NDVI}_{\text{max}} - \text{NDVI}_{\text{min}}}\right]^2, \quad \text{clamped to } [0.0, 1.0]
$$
- $\text{NDVI}_{\text{min}}, \text{NDVI}_{\text{max}}$ are dynamically extracted from scene 5th and 95th percentiles (bounded: $\text{NDVI}_{\text{min}} \in [0.05, 0.20]$, $\text{NDVI}_{\text{max}} \in [0.50, 0.85]$).

#### E. Land Surface Emissivity ($\varepsilon_\lambda$ — Sobrino et al. 2008)
$$
\varepsilon_\lambda = \varepsilon_{\text{veg}} \cdot P_v + \varepsilon_{\text{soil}} \cdot (1 - P_v) + C_\lambda
$$
- Cavity effect $C_\lambda = 0.005 \cdot (1 - \varepsilon_{\text{soil}}) \cdot \varepsilon_{\text{veg}} \cdot (1 - P_v)$.
- Simplified dynamic formulation for TIRS 10 & 11:
  $$
  \varepsilon_{10} = 0.986 + 0.004 \cdot P_v, \quad \varepsilon_{11} = 0.989 + 0.003 \cdot P_v
  $$
- Mean emissivity $\bar{\varepsilon} = \frac{\varepsilon_{10} + \varepsilon_{11}}{2}$, Emissivity difference $\Delta\varepsilon = \varepsilon_{10} - \varepsilon_{11}$.

#### F. Split-Window Land Surface Temperature (Du et al. 2015 / Sobrino 2008)
$$
T_s = T_{10} + c_1(T_{10} - T_{11}) + c_2(T_{10} - T_{11})^2 + c_0 + (c_3 + c_4 w)(1 - \bar{\varepsilon}) + (c_5 + c_6 w)\Delta\varepsilon - 273.15 \quad [^\circ\text{C}]
$$
Where $w$ is atmospheric precipitable water vapor ($\text{g}/\text{cm}^2$), and empirical coefficients switch according to atmospheric moisture regimes:

| Coefficient | Dry Atmosphere ($w \le 3.0\,\text{g/cm}^2$) | Humid / Tropical Atmosphere ($w > 3.0\,\text{g/cm}^2$) |
| :---: | :---: | :---: |
| $c_0$ | $-0.268$ | $-1.274$ |
| $c_1$ | $1.378$ | $1.832$ |
| $c_2$ | $0.183$ | $0.312$ |
| $c_3$ | $54.30$ | $68.20$ |
| $c_4$ | $-2.238$ | $-3.451$ |
| $c_5$ | $-129.20$ | $-145.40$ |
| $c_6$ | $16.40$ | $22.10$ |

#### G. Single-Channel LST Fallback (Artis & Carnahan 1982)
When Band 11 is unavailable or heavily degraded by stray light artifacts:
$$
T_s = \frac{T_{10}}{1 + \left(\frac{\lambda \cdot T_{10}}{\rho_{\text{planck}}}\right) \cdot \ln(\bar{\varepsilon})} - 273.15 \quad [^\circ\text{C}]
$$
- Effective wavelength $\lambda = 10.895\,\mu\text{m} = 10.895 \times 10^{-6}\,\text{m}$.
- Physical constant $\rho_{\text{planck}} = \frac{h \cdot c}{\sigma_B} = 1.438 \times 10^{-2}\,\text{m}\cdot\text{K}$.

#### H. Bitwise Cloud & Shadow Masking (`QA_PIXEL`)
Invalidates thermal pixels corrupted by atmospheric occlusion:
$$
\text{Masked} = (\text{QA} \gg 1)\,\&\,1 \quad (\text{Dilated Cloud}) \;\lor\; (\text{QA} \gg 3)\,\&\,1 \quad (\text{Cloud}) \;\lor\; (\text{QA} \gg 4)\,\&\,1 \quad (\text{Cloud Shadow})
$$

---

### 3. LULC Intelligence Classification Engine (Rule-Based Decision Trees)

Implemented in [lulc_tasks.py](file:///d:/GEO%20MAP/GeoStudio/Python/PythonPipeline/tasks/lulc_tasks.py). Applies physics-based, multi-sensor refinement across 22 hierarchical classes:

```mermaid
flowchart TD
    Raw[Sentinel-2 / Landsat Multispectral] --> Indices[Compute NDVI, NDWI, MNDWI, BSI, TCW, Slope]
    Indices --> Prior{Dynamic World Prior?}
    Prior -->|Yes| BaseDW[Map DW Classes 0..8 to LULC Taxonomy]
    Prior -->|No| BaseRules[Spectral Baseline: Forest, Crop, Water, Bare]
    
    BaseDW --> Refine
    BaseRules --> Refine[Physics-Based Decision Refinement]
    
    Refine --> F1["Forest Refinement (10)<br/>• BSI > 0.10 & NDVI < 0.40 ➔ Degraded Forest (13)<br/>• NDVI >= 0.45 ➔ Dense Forest (11)<br/>• 0.30 <= NDVI < 0.45 ➔ Sparse Forest (12)"]
    Refine --> C1["Cropland Refinement (40)<br/>• MNDWI > -0.05 & NDVI > 0.30 ➔ Irrigated (41)<br/>• NDVI < 0.25 & MNDWI <= -0.20 ➔ Fallow/Rainfed (42)<br/>• BSI > 0.08 & NDVI < 0.35 ➔ Degraded (13)"]
    Refine --> W1["Water Refinement (80)<br/>• MNDWI > 0.20 ➔ Permanent Water (81)<br/>• 0.0 <= MNDWI <= 0.20 ➔ Seasonal Water (82)"]
    Refine --> Wet1["Wetland Refinement (90)<br/>• NDVI > 0.20 & TCW > 0.0 ➔ Flooded Veg (91)<br/>• NDVI < 0.15 ➔ Mudflat / Bare Wetland (92)"]
    Refine --> B1["Bare Ground Refinement (60)<br/>• Slope > 8° ➔ Rocky / Barren (61)<br/>• BSI > 0.10 & Slope <= 8° ➔ Sandy / Alluvial (62)"]
    
    F1 & C1 & W1 & Wet1 & B1 --> Modal[3x3 Modal Majority Filter]
    Modal --> FinalLULC[Final 22-Class LULC GeoTIFF]
```

---

### 4. Terrain Morphology, 3D Shading & Viewshed

Implemented in [ElevationShadedRelief.cs](file:///d:/GEO%20MAP/GeoStudio/Raster/Rendering/ShadedRelief/ElevationShadedRelief.Renderer.cs), [relief_shading.py](file:///d:/GEO%20MAP/GeoStudio/PythonEngine/core/elevation/relief_shading.py), and [terrain_tasks.py](file:///d:/GEO%20MAP/GeoStudio/Python/PythonPipeline/tasks/terrain_tasks.py):

#### A. Central Difference Surface Gradient
$$
\frac{\partial z}{\partial x} = \frac{z(x+1, y) - z(x-1, y)}{2 \cdot \Delta x_m}, \qquad \frac{\partial z}{\partial y} = \frac{z(x, y+1) - z(x, y-1)}{2 \cdot \Delta y_m}
$$
- When DEM is in Geographic Coordinates (WGS84 degrees):
  $$
  \Delta x_m = \Delta x_{\text{deg}} \cdot 111320.0 \cdot \cos(\phi_{\text{lat}}), \qquad \Delta y_m = \Delta y_{\text{deg}} \cdot 111320.0
  $$

#### B. Dynamic Vertical Exaggeration ($z_{\text{factor}}$)
To prevent extreme flattening in lowlands and severe shadow blow-outs in rugged terrain, $z_{\text{factor}}$ adapts dynamically to localized elevation range $\Delta z = z_{\text{max}} - z_{\text{min}}$:
$$
z_{\text{factor}} = \begin{cases}
8.0 & \text{if } \Delta z \le 10\,\text{m} \quad (\text{Coastal Plains / Floodplains}) \\
5.0 & \text{if } 10 < \Delta z \le 30\,\text{m} \\
3.5 & \text{if } 30 < \Delta z \le 100\,\text{m} \\
2.0 & \text{if } 100 < \Delta z \le 300\,\text{m} \\
1.2 & \text{if } \Delta z > 300\,\text{m} \quad (\text{High Alpine Ridges})
\end{cases}
$$

#### C. Slope & Aspect
$$
\text{Slope} = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2} \cdot z_{\text{factor}}\right) \quad [\text{radians}]
$$
$$
\text{Slope}_{\text{deg}} = \text{Slope} \cdot \frac{180}{\pi}, \qquad \text{Slope}_{\%} = \tan(\text{Slope}) \cdot 100
$$
$$
\text{Aspect} = \text{atan2}\left(-\frac{\partial z}{\partial x},\, \frac{\partial z}{\partial y}\right) \pmod{2\pi} \quad [0 \text{ to } 360^\circ]
$$

#### D. Multi-Directional Lambertian 3D Hillshading
GeoStudio avoids single-light source shadow dropouts by combining three illumination vectors:
1. **Primary Key Light**: Azimuth $\alpha_1 = 315^\circ$ (NW), Altitude $\beta = 45^\circ$, Weight $= 0.60$
2. **Soft Fill Light**: Azimuth $\alpha_2 = 225^\circ$ (SW), Altitude $\beta = 45^\circ$, Weight $= 0.25$
3. **Ambient Rim Light**: Azimuth $\alpha_3 = 45^\circ$ (NE), Altitude $\beta = 45^\circ$, Weight $= 0.15$

$$
\text{HS}_i = \max\left(0.0,\, \sin\beta\cos(\text{Slope}) + \cos\beta\sin(\text{Slope})\cos(\alpha_i - \text{Aspect})\right)
$$
$$
\text{Illumination} = 0.22 + 0.78 \cdot \left(0.60 \cdot \text{HS}_{315^\circ} + 0.25 \cdot \text{HS}_{225^\circ} + 0.15 \cdot \text{HS}_{45^\circ}\right)
$$

#### E. Topographic Ruggedness Index (TRI — Riley et al. 1999)
$$
\text{TRI} = \sqrt{\frac{1}{8} \sum_{i=1}^8 \left(z_0 - z_i\right)^2}
$$

#### F. Topographic Position Index (TPI — Weiss 2001)
$$
\text{TPI} = z_0 - \bar{z}_{\text{neighborhood}}
$$
- Positive values indicate hilltops and ridges; negative values represent valley bottoms and drainage channels.

#### G. 3D Viewshed with Earth Curvature & Atmospheric Refraction
GDAL Viewshed line-of-sight elevation adjustment:
$$
\Delta h_{\text{curv}} = \frac{D^2}{2 \cdot R_{\text{earth}}} \cdot (1 - k)
$$
- $R_{\text{earth}} = 6,371,000\,\text{m}$.
- Atmospheric refraction index $k = 0.14286 \implies (1 - k) = 0.85714$.

---

### 5. Earthwork Volumetrics & Cut/Fill Balance Engine

Implemented in [cut_fill_engine.py](file:///d:/GEO%20MAP/GeoStudio/PythonEngine/core/earthworks/cut_fill_engine.py) and [VolumetricAnalysisWindow.xaml.cs](file:///d:/GEO%20MAP/GeoStudio/UI/Dialogs/Terrain/VolumetricAnalysisWindow.xaml.cs):

#### A. Elevation Differential Matrix
$$
\Delta z(x, y) = z_{\text{comp}}(x, y) - z_{\text{base}}(x, y)
$$
- **Cut Condition**: $\Delta z < -0.005\,\text{m}$ (Material excavation required)
- **Fill Condition**: $\Delta z > 0.005\,\text{m}$ (Material embankment required)
- **Daylight Condition**: $|\Delta z| \le 0.005\,\text{m}$ (Zero-grade grade daylight line)

#### B. Factored Volumetric Calculations
$$
V_{\text{cut,gross}} = \sum |\Delta z_{\text{cut}}| \cdot A_{\text{cell}}, \qquad V_{\text{fill,gross}} = \sum \Delta z_{\text{fill}} \cdot A_{\text{cell}}
$$
$$
V_{\text{cut,factored}} = V_{\text{cut,gross}} \cdot S_{\text{swell}}, \qquad V_{\text{fill,factored}} = V_{\text{fill,gross}} \cdot S_{\text{shrinkage}}
$$
$$
V_{\text{net}} = V_{\text{cut,factored}} - V_{\text{fill,factored}}, \qquad \text{Cut/Fill Ratio} = \frac{V_{\text{cut,factored}}}{V_{\text{fill,factored}}}
$$
- $S_{\text{swell}}$: Geotechnical bank-to-loose swell factor (default $1.00 - 1.25$).
- $S_{\text{shrinkage}}$: Loose-to-compacted embankment shrinkage factor (default $1.00 - 0.90$).

#### C. Optimal Neutral Balance Plane (Bisection Root-Finding)
Solves for the horizontal grading datum $z^*$ where excavation equals embankment ($V_{\text{net}}(z^*) = 0$):
$$
f(z^*) = \sum_{z_i < z^*} (z^* - z_i) \cdot S_{\text{shrinkage}} - \sum_{z_i > z^*} (z_i - z^*) \cdot S_{\text{swell}} = 0
$$
- Converges in $\le 35$ bisection iterations with residual volume tolerance $\epsilon < 0.001\,\text{m}^3$.

#### D. Reservoir Hypsometric Stage-Storage Curve
$$
V_{\text{storage}}(h) = \sum_{z_i < h} (h - z_i) \cdot A_{\text{cell}}, \qquad A_{\text{water}}(h) = N_{\text{submerged}} \cdot A_{\text{cell}}
$$

---

### 6. Hydrological Modeling & Watershed Analysis

Implemented in [hydrology_engine.py](file:///d:/GEO%20MAP/GeoStudio/PythonEngine/core/hydrology/hydrology_engine.py), [sink_filling.py](file:///d:/GEO%20MAP/GeoStudio/PythonEngine/core/hydrology/sink_filling.py), and [flow_routing.py](file:///d:/GEO%20MAP/GeoStudio/PythonEngine/core/hydrology/flow_routing.py):

#### A. Barnes Priority-Flood Sink Filling
Priority queue (min-heap) propagating elevations from DEM raster boundaries inwards:
$$
z_{\text{filled}}(u) = \max\left(z_{\text{raw}}(u),\, z_{\text{spill}}(v)\right)
$$
Guarantees strictly non-decreasing drainage networks without creating artificial plateaus or dams.

#### B. D8 Steepest Slope Routing
$$
S_i = \frac{z_0 - z_i}{d_i}, \qquad d_i = \begin{cases} \Delta x_m \text{ or } \Delta y_m & \text{cardinal neighbors} \\ \sqrt{\Delta x_m^2 + \Delta y_m^2} & \text{diagonal neighbors} \end{cases}
$$
Flow direction code is assigned to the neighbor $i \in \{1, 2, 4, 8, 16, 32, 64, 128\}$ with $\max(S_i)$.

#### C. Garbrecht & Martz Flat Area Resolution
To prevent parallel raster artifacts in zero-slope valley floors and lake beds, flow vectors are routed across flat surfaces via Euclidean Distance Transform to the nearest lower spill point:
$$
D_{\text{spill}} = \text{EDT}(\text{FlatCells}) \implies \vec{v}_{\text{flow}} = -\nabla D_{\text{spill}}
$$

#### D. Kahn's Topological Flow Accumulation
Cells are sorted into a Directed Acyclic Graph (DAG) by in-degree counts, propagating upstream cell contributions downstream in linear $O(N)$ time:
$$
A(u) = 1 + \sum_{v \in \text{Inflow}(u)} A(v)
$$

#### E. Strahler Stream Ordering
Hierarchical stream orders assigned at channel confluences:
$$
S_{\text{confluence}} = \begin{cases}
\max(S_1, S_2) + 1 & \text{if } S_1 = S_2 \\
\max(S_1, S_2) & \text{if } S_1 \ne S_2
\end{cases}
$$

#### F. Chaikin's Corner-Cutting Curve Smoothing
Stream vectors are smoothed for cartographic display:
$$
Q_i = 0.75 P_i + 0.25 P_{i+1}, \qquad R_i = 0.25 P_i + 0.75 P_{i+1}
$$

---

### 7. Central Ground Water Board (CGWB) Artificial Recharge Engineering

Implemented in [CgwbMasterPlanService.cs](file:///d:/GEO%20MAP/GeoStudio/Hydrology/Services/CgwbMasterPlanService.cs) and [RechargeBoqService.cs](file:///d:/GEO%20MAP/GeoStudio/Hydrology/Services/RechargeBoqService.cs) following CGWB Master Plan (2007 & 2020) guidelines:

#### A. Three Mandatory Screening Gates
1. **Waterlogging Exclusion Gate**: Post-monsoon Depth to Water (DTW) $< 3.0\,\text{m bgl} \implies$ **REJECTED** (Recharge prohibited to prevent root-zone waterlogging and secondary soil salinization).
2. **Groundwater Salinity Ceiling**: Native groundwater Electrical Conductivity (EC) $> 2,500\,\mu\text{S/cm} \implies$ **REJECTED** (Recharge prohibited to avoid mobilizing subterranean halite/gypsum).
3. **Decline Trend Gate**: For moderate DTW ($3.0 - 9.0\,\text{m bgl}$), long-term post-monsoon declining trend must be $|\Delta h_{\text{trend}}| \ge 0.20\,\text{m/year}$.

#### B. Subsurface Storage Capacity & Required Water
$$
T_{\text{unsat}} = \max\left(0,\, \text{DTW} - 3.0\right) \quad [\text{m}]
$$
$$
V_u = \text{Area}_{\text{district}} \cdot T_{\text{unsat}} \quad [\text{MCM}]
$$
$$
V_{\text{storage}} = V_u \cdot S_y \quad [\text{MCM}]
$$
$$
W_{\text{gross\_required}} = \frac{V_{\text{storage}}}{0.75} \quad [\text{MCM}] \quad (\text{Accounting for 75\% recharge efficiency})
$$
$$
W_{\text{feasible}} = \min\left(W_{\text{gross\_required}},\, \text{Surplus Runoff Available}\right)
$$
- $S_y$: Aquifer Specific Yield ($0.08 - 0.12$ for Alluvium, $0.02 - 0.04$ for Hard Rock / Schist / Granite).

#### C. Catchment Runoff Yield ($Y_c$ — Strange's Table / SCS Proxy)
$$
Y_c = 10.0 \cdot C_{\text{catchment}} \cdot P_{75\%} \cdot A_{\text{catchment}} \quad [\text{m}^3]
$$
- $P_{75\%}$: 75% dependable annual rainfall in millimeters.
- $A_{\text{catchment}}$: Micro-catchment area in hectares.
- $C_{\text{catchment}}$: Catchment runoff coefficient ($0.22$ for Good/Rocky, $0.16$ for Average, $0.10$ for Bad/Sandy).

#### D. Siting Multi-Criteria Scoring (0–100 Points)
- **Check Dam / Anicut**:
  - Slope: $0.5^\circ - 3.0^\circ$ ($+35$), $3.0^\circ - 5.0^\circ$ ($+20$), $5.0^\circ - 8.0^\circ$ ($+10$).
  - Catchment: $25 - 250\,\text{ha}$ ($+30$), $10 - 500\,\text{ha}$ ($+15$).
  - Water Depth: $5 - 25\,\text{m}$ ($+25$), $> 25\,\text{m}$ ($+15$).
  - Stream Order: Strahler 1–3 ($+10$).
- **Percolation Tank**: Slope $\le 2^\circ$ ($+40$), Catchment $40 - 400\,\text{ha}$ ($+30$), DTW $6 - 30\,\text{m}$ ($+30$).
- **Farm Pond (Khet Talai)**: Slope $\le 3^\circ$ ($+50$), Catchment $2 - 50\,\text{ha}$ ($+50$).

#### E. Bill of Quantities (BOQ) Standard Unit Rates (Rajasthan WRD/WDSC BSR)
Calculated with $+3\%$ unforeseen contingencies and $+2\%$ quality control & supervision:
$$
\text{Total Estimate} = \left(\sum \text{Qty}_i \cdot \text{Rate}_i\right) \times 1.05
$$

| Item Description | BSR Schedule Reference | Unit | Base Rate (INR) |
| :--- | :--- | :---: | :---: |
| Earthwork excavation in pond basin / riverbed | Raj WRD Item 1.2 / 1.4 | $\text{m}^3$ | ₹ 165.00 – 240.00 |
| Random Rubble Masonry (RRM) in Cement Mortar 1:5 | Raj WRD Item 4.3 | $\text{m}^3$ | ₹ 3,400.00 |
| Cement Concrete M20 (1:2:4) Crest Cap / Weir Coping | Raj WRD Item 6.1 | $\text{m}^3$ | ₹ 6,200.00 |
| Cement Concrete M15 (1:3:6) Downstream Stilling Basin | Raj WRD Item 5.2 | $\text{m}^3$ | ₹ 4,800.00 |
| Dry Stone Pitching (1:2 slope protection) | Raj WRD Item 4.1 | $\text{m}^3$ | ₹ 2,800.00 |
| Graded Gravel Filter Pack (3–7mm silica pea gravel) | Standard Special Item | $\text{m}^3$ | ₹ 1,850.00 |
| 500-Micron Multi-layer HDPE Geomembrane Liner | BIS 15351 / WRD Spec | $\text{m}^2$ | ₹ 190.00 |
| 450mm Rotary Borehole Drilling (Recharge Shaft) | GW Dept BSR Item 3 | $\text{m}$ | ₹ 850.00 |
| 200mm Slotted High-Collapse PVC Well Casing | GW Dept BSR Item 5 | $\text{m}$ | ₹ 950.00 |

---

### 8. Agricultural Water Budget & Crop Water Planner

Implemented in [recharge_tasks.py](file:///d:/GEO%20MAP/GeoStudio/Python/PythonPipeline/tasks/recharge_tasks.py):

#### A. Water Availability Index (WAI)
$$
\text{WAI} = 0.40 \cdot S_{\text{gw}} + 0.25 \cdot S_{\text{depth}} + 0.20 \cdot S_{\text{rain}} + 0.15 \cdot S_{\text{aquifer}} + 15.0 \cdot \min(1.0,\, \text{Canal Index})
$$
- $S_{\text{gw}}$: Safe ($100$), Semi-Critical ($70$), Critical ($45$), Over-Exploited ($20$).
- $S_{\text{depth}}$: DTW $\le 6\,\text{m}$ ($100$), $6-12\,\text{m}$ ($75$), $12-20\,\text{m}$ ($50$), $20-30\,\text{m}$ ($30$), $> 30\,\text{m}$ ($15$).
- $S_{\text{rain}}$: Rain $\ge 800\,\text{mm}$ ($100$), $600-800\,\text{mm}$ ($90$), $450-600\,\text{mm}$ ($65$), $300-450\,\text{mm}$ ($40$), $< 300\,\text{mm}$ ($20$).
- $S_{\text{aquifer}}$: Alluvium ($100$), Dune Sand ($70$), Sandstone/Limestone ($60$), Hard Rock/Basalt ($40$).
- **Hydrological Safety Cap**: If block is Over-Exploited (OE), $\text{WAI} \le 38.0$ (or $35.0 + 20.0 \cdot \text{Canal Index}$).

#### B. 4-Tier Crop Planning Matrix & Water Conservation

| Tier | WAI Score | Classification | Target Saving | Recommended Kharif | Recommended Rabi | Horticulture |
| :---: | :---: | :--- | :---: | :--- | :--- | :--- |
| **Tier 1** | $< 40$ | Extreme Deficit | **40%** | Moth Bean, Guar, Bajra | Isabgol, Barley, Gram | Date Palm, Ber, Kair |
| **Tier 2** | $40 - 54$ | Moderate Deficit | **25%** | Moong, Groundnut, Bajra | Cumin, Mustard, Chickpea | Pomegranate, Aonla |
| **Tier 3** | $55 - 69$ | Moderate Availability | **10%** | Soybean, Maize, Cotton | Mustard, Wheat, Chickpea | Guava, Mandarin, Kinnow |
| **Tier 4** | $\ge 70$ | High Availability | **0%** | Soybean, Maize, Groundnut | High-Yield Wheat, Mustard | Kinnow, Mango, Guava |

#### C. Applied Water Savings & Farmer Profit Estimations
$$
\text{Water Saved} = \text{Baseline Water} \cdot \left(\frac{\text{Target Saving \%}}{100}\right) \quad [\text{mm}], \qquad \text{Volume Saved} = \text{Water Saved} \cdot 10.0 \quad [\text{m}^3/\text{ha}]
$$
$$
\Delta \text{Profit} = \left(\text{Volume Saved} \cdot 2.0\,\text{INR}\right) + \text{Intervention Bonus} \quad [\text{₹/ha}]
$$

---

### 9. LiDAR & Point Cloud Spatial Processing

Implemented in [LasSurfaceRasterizerService.cs](file:///d:/GEO%20MAP/GeoStudio/PointCloud/LasSurfaceRasterizerService.cs) and [lidar_tasks.py](file:///d:/GEO%20MAP/GeoStudio/Python/PythonPipeline/tasks/lidar_tasks.py):

#### A. Inverse Distance Weighting (IDW) Surface Interpolation
$$
z(x, y) = \frac{\sum_{i=1}^k w_i \cdot z_i}{\sum_{i=1}^k w_i}, \qquad w_i = \frac{1}{d_i^p} \quad (\text{Power parameter } p = 2.0)
$$

#### B. Simple Morphological Filter (SMRF — Pingel et al. 2013)
Progressive morphological opening with linearly expanding structuring element window $w_k$:
$$
T_k = s \cdot w_k \cdot c_s + t_{\text{base}}
$$
- Slope tolerance $s = 0.15$, Window scaling step $c_s = 1.25$, Elevation base threshold $t_{\text{base}} = 0.45\,\text{m}$.
- Points where $z_i - \text{Open}(z)_i \le T_k$ are classified as ASPRS Class 2 (Ground).

#### C. Delaunay TIN Height Above Ground (HAG) & Canopy Stratification
Normalized height above bare earth TIN: $z_{\text{HAG}} = z_i - z_{\text{TIN\_ground}}(x_i, y_i)$.
- **ASPRS Class 2 (Ground)**: $z_{\text{HAG}} < 0.3\,\text{m}$
- **ASPRS Class 3 (Low Veg)**: $0.3\,\text{m} \le z_{\text{HAG}} < 1.8\,\text{m}$
- **ASPRS Class 4 (Medium Veg)**: $1.8\,\text{m} \le z_{\text{HAG}} < 4.0\,\text{m}$
- **ASPRS Class 5 (High Veg / Tree Canopy)**: $z_{\text{HAG}} \ge 4.0\,\text{m}$

#### D. Planar Rooftop Building Extraction (ASPRS Class 6)
Point candidates must satisfy three criteria:
1. **Pulse Return Filter**: Single return only ($N_{\text{returns}} \le 1$ or $R_{\text{num}} = N_{\text{returns}}$) to reject multi-bounce canopy.
2. **Height & Planarity**: $2.2\,\text{m} \le z_{\text{HAG}} \le 65.0\,\text{m}$, Local $k$-NN elevation standard deviation $\sigma_z < 0.22\,\text{m}$.
3. **Connected-Component Footprint**: Ball-tree spatial clustering ($r = 2.2\,\text{m}$) requiring $\ge 50$ points and footprint area $\Delta x \cdot \Delta y \ge 15.0\,\text{m}^2$.

---

### 10. Geodesics, Snapping & Road Network Routing

Implemented in [ShortestPathSolver.cs](file:///d:/GEO%20MAP/GeoStudio/Routing/Services/ShortestPathSolver.cs) and [RoadRoutingService.cs](file:///d:/GEO%20MAP/GeoStudio/Routing/Services/RoadRoutingService.cs):

#### A. Great-Circle Haversine Geodesic Distance
$$
a = \sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)
$$
$$
d = 2 \cdot R_{\text{earth}} \cdot \arcsin\left(\sqrt{a}\right) \quad [\text{meters}] \qquad (R_{\text{earth}} = 6,371,000\,\text{m})
$$

#### B. Geodesic Polygon Area (Spherical Excess)
$$
A_{\text{poly}} = R_{\text{earth}}^2 \cdot \left| \sum_{i=1}^n \left(\lambda_{i+1} - \lambda_{i-1}\right) \cdot \sin(\phi_i) \right| \cdot \frac{1}{2} \quad [\text{m}^2]
$$

#### C. Vector Digitizing Snapping Engine
Cursor coordinates $\vec{p} = (x, y)$ snap to active vector vertex $\vec{v}_i$ or line segment $\overline{\vec{v}_1 \vec{v}_2}$ within screen tolerance radius $\tau = 12\,\text{px}$:
$$
t = \text{clamp}\left(\frac{(\vec{p} - \vec{v}_1) \cdot (\vec{v}_2 - \vec{v}_1)}{\|\vec{v}_2 - \vec{v}_1\|^2},\, 0,\, 1\right), \qquad \vec{p}_{\text{proj}} = \vec{v}_1 + t(\vec{v}_2 - \vec{v}_1)
$$
$$
\text{Snap Triggered if } \|\vec{p} - \vec{p}_{\text{proj}}\| \le \tau
$$

#### D. CSR Road Graph Geodesic A* Shortest Path
Node evaluation priority queue score:
$$
f(u) = g(u) + h(u)
$$
- $g(u)$: Exact accumulated geodesic distance or travel duration from start node.
- $h(u)$: Admissible geodesic distance heuristic to destination:
  $$
  h(u) = \begin{cases}
  \text{Haversine}(u, \text{Target}) & \text{Shortest Distance Optimization} \\
  \frac{\text{Haversine}(u, \text{Target})}{v_{\text{max}}} & \text{Fastest Time Optimization } (v_{\text{max}} = 33.33\,\text{m/s} = 120\,\text{km/h})
  \end{cases}
  $$

---

## 📁 Project Structure

```
d:\GEO MAP\
├── README.md                          # Comprehensive Documentation
├── run_geostudio.bat                  # Instant one-click launcher
└── GeoStudio\                         # .NET 8 WPF Solution
    ├── GeoStudio.csproj               # Project dependencies and build settings
    ├── App.xaml / App.xaml.cs         # Application entry point & exception handlers
    ├── AssemblyInfo.cs                # Assembly metadata and manifest
    ├── GlobalUsings.cs                # Global namespace usings for clean modular architecture
    ├── MainWindow.xaml                # XAML UI layout (Ribbon, Sidebar, Status Bar)
    ├── MainWindow.xaml.cs             # UI core lifecycle & WebView2 initialization
    │
    ├── DuckDB\                        # Embedded DuckDB LiDAR database & spatial querying
    │   ├── DuckDbConnectionManager.cs # In-memory database connection pooling
    │   ├── DuckDbLasIngestor.cs       # ASPRS LAS binary to DuckDB streaming ingestion
    │   ├── DuckDbPointCloudService.cs # High-level point cloud service interface
    │   └── DuckDbQueryEngine.cs       # Viewport spatial bounding box & LOD SQL queries
    │
    ├── WebView\                       # WebView2 integration & WebGL MapEngine
    │   ├── MainWindow.MapInteractions.cs # Host IPC message handlers (postMessage / WebMessageReceived)
    │   └── MapEngine\                 # WebGL / OpenLayers map canvas & shader engine
    │       ├── index.html             # Main WebView viewport entry point
    │       ├── mapEngine.js           # Map engine initialization & layers
    │       ├── mapHostBridge.js       # Host IPC bridge
    │       ├── mapTelemetry.js        # GPU FPS / frame telemetry
    │       ├── pointCloudCanvas.js    # WebGL floating point cloud shader canvas
    │       ├── rasterLayerManager.js  # Dynamic overview & tile manager
    │       ├── ol.js / ol.css         # OpenLayers 8+ standalone cartographic library
    │       └── geotiff.js             # Client-side GeoTIFF decoding library
    │
    ├── Raster\                        # GDAL raster engine & tile processing
    │   ├── Core\                      # High-level façade service & models
    │   │   ├── GdalRasterService.cs   # Main GDAL service orchestrator
    │   │   └── GdalRasterModels.cs    # Metadata & viewport request models
    │   ├── Rendering\                 # Decimation, overviews & hillshading
    │   │   ├── GdalWindowRenderer.cs  # Stabilized high-res viewport decimation
    │   │   ├── GdalOverviewGenerator.cs # Low-res pyramid generator
    │   │   ├── ElevationShadedRelief.cs # Hypsometric tint & hillshade shader
    │   │   └── SparseRasterPreview.cs # Fast scanline preview decoder
    │   ├── Tiling\                    # XYZ web tile streaming & caching
    │   │   ├── RasterTileService.cs   # In-process WebView2 tile server hook
    │   │   ├── TileCache.cs           # Memory cache for rendered tiles
    │   │   ├── TileLayer.cs           # Tile layer state & configuration
    │   │   └── TilePooledReader.cs    # Multi-threaded pooled GDAL tile reader
    │   ├── Caching\                   # Disk cache management & task queue
    │   │   ├── GdalCacheManager.cs    # LocalAppData cache lifecycle & auto-pruning
    │   │   └── OptimizationQueue.cs   # Asynchronous background job queue
    │   └── IO\                        # Format readers & converters
    │       ├── BigTiffService.cs      # Memory-mapped 64-bit BigTIFF reader
    │       ├── CogBuilder.cs          # Cloud-Optimized GeoTIFF builder
    │       └── GdalMetadataReader.cs  # Header, bounds & coordinate ref system reader
    │
    ├── PointCloud\                    # ASPRS LAS/LAZ point cloud processing
    │   ├── LasPointCloudService.cs    # Direct binary ASPRS LAS/LAZ parser
    │   ├── LasDecompressor.cs         # Native LASzip LAZ decompression
    │   ├── LasSampleReader.cs         # Fast header and bounding box reader
    │   ├── LasSurfaceRasterizerService.cs # Point cloud to DEM surface grid interpolator
    │   └── PointCloudModels.cs        # Point cloud batch, header, and classification models
    │
    ├── Python\                        # Python pipeline execution service
    │   ├── PythonPipelineService.cs   # Background python subprocess runner & progress reporter
    │   └── PythonPipeline\            # Python bridge script
    │       └── pipeline_bridge.py     # Task runner for analytical scripts
    │
    ├── UI\                            # WPF UI dialogs, windows and commands
    │   ├── Dialogs\                   # Standalone analysis dialog windows
    │   │   ├── CutFillWindow.xaml / .cs # Earthwork volumetric cut & fill calculator
    │   │   └── ElevationProfileWindow.xaml / .cs # Interactive terrain profile window
    │   └── Commands\                  # MainWindow partial command classes
    │       ├── MainWindow.DataLoading.cs
    │       ├── MainWindow.DigitizingCommands.cs
    │       ├── MainWindow.LayerManagement.cs
    │       ├── MainWindow.LidarCommands.cs
    │       ├── MainWindow.NavigationCommands.cs
    │       ├── MainWindow.ProjectCommands.cs
    │       ├── MainWindow.Telemetry.cs
    │       └── MainWindow.TerrainCommands.cs
    │
    ├── Models\                        # Data models
    │   └── LayerItem.cs               # Layer model (visibility, opacity, metadata, icons)
    │
    ├── Resources\                     # Application static resources
    │   └── Icons\                     # Ribbon UI icon PNG assets (60+ icons)
    │
    └── PythonEngine\                  # Standalone Python algorithms and tool suite
```

---

## 🚀 Prerequisites & Build Instructions

### System Requirements
- **Operating System**: Windows 10 (version 1809+) or Windows 11 (x64).
- **Runtime Environment**:
  - [.NET 8.0 Desktop Runtime](https://dotnet.microsoft.com/en-us/download/dotnet/8.0) or .NET 8.0 SDK.
  - [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) (Pre-installed on Windows 11).
- **Hardware Acceleration**: DirectX 11 / OpenGL 3.3 compatible GPU (NVIDIA, AMD, or Intel Iris Xe) recommended for high-density point clouds.

### Method 1: Instant Launcher (Recommended)
Double-click `run_geostudio.bat` in the root folder, or execute from terminal:
```cmd
run_geostudio.bat
```

### Method 2: Command Line Compilation & Execution
Open PowerShell or Windows Terminal in the repository root:
```powershell
# 1. Ensure .NET 8 is in your PATH
$env:PATH = "$env:LOCALAPPDATA\Microsoft\dotnet;" + $env:PATH

# 2. Navigate to the project directory
cd GeoStudio

# 3. Restore NuGet dependencies
dotnet restore

# 4. Build and Run in Release mode
dotnet run -c Release
```

---

## 📊 Performance Benchmarks & Optimizations

Empirical testing performed on an Intel Core i7 / 32 GB RAM / NVIDIA RTX GPU with NVMe SSD:

| Dataset Type | File Size / Count | Cold Load Time | Viewport Pan / Redraw | Memory Footprint (RAM) |
| :--- | :--- | :---: | :---: | :---: |
| **GeoTIFF Orthomosaic** | 1.8 GB ($18,000 \times 16,000$) | **0.82 s** | **< 16 ms** (60 FPS) | ~ 140 MB |
| **BigTIFF Satellite** | 104 GB ($98,000 \times 84,000$) | **1.45 s** *(overview)* | **32 ms** *(decimated window)* | ~ 285 MB |
| **ASPRS LiDAR (LAS 1.4)**| 12.5M Points (580 MB) | **2.10 s** *(DuckDB ingest)* | **< 16 ms** (60 FPS) | ~ 320 MB |
| **ASPRS LiDAR (LAS 1.2)**| 48.0M Points (2.1 GB) | **6.40 s** *(DuckDB ingest)* | **< 20 ms** (55-60 FPS) | ~ 510 MB |
| **Vector Polygons** | 50,000 Parcels (GeoJSON) | **0.65 s** | **< 16 ms** (60 FPS) | ~ 110 MB |

---

## ❓ Troubleshooting Guide

### 1. WebView2 Map Canvas Appears Blank
- **Cause**: The Microsoft Edge WebView2 runtime is missing, corrupted, or blocked by local group policies.
- **Fix**: Download and run the Evergreen WebView2 Runtime bootstrapper from Microsoft: [Download WebView2](https://go.microsoft.com/fwlink/p/?LinkId=2124703).

### 2. GDAL Native Binary Initialization Warning
- **Symptom**: Console reports `GDAL Init Warning: Unable to load DLL 'gdal'`.
- **Cause**: Missing Visual C++ Redistributable or 32-bit/64-bit architecture mismatch.
- **Fix**: Install the latest [Visual C++ 2015-2022 Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe). Verify `GeoStudio.csproj` compiles strictly for `net8.0-windows` on `x64`.

### 3. High-Resolution Raster Window Does Not Refresh on Zoom
- **Cause**: Zoom stabilization debounce threshold has not elapsed.
- **Explanation**: To prevent flooding the GDAL decoder during rapid wheel scrolling, viewport queries are debounced by `200ms`. Once zoom motion stops, the high-resolution tile generates and updates automatically.

### 4. GPU Performance Shows Low FPS
- **Cause**: System is using software emulation or integrated low-power GPU.
- **Fix**: Ensure Windows Graphics Settings sets `GeoStudio.exe` to **High Performance** (Discrete GPU). Verify hardware renderer name shown in the GeoStudio status bar tooltip.

---

## 📄 License & Attribution

- Built with .NET 8 WPF and OpenLayers.
- GDAL bindings provided via [MaxRev.Gdal.Core](https://github.com/MaxRev-Dev/gdal.netcore).
- Embedded columnar spatial database provided via [DuckDB.NET](https://github.com/Giorgi/DuckDB.NET).
- Cartographic tiles © [CartoDB](https://carto.com/attributions) / [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors / [Esri](https://www.esri.com/).
