# GIS and DBSCAN Spatial Analysis Audit — VenomWatch

**Project Title:** VenomWatch — AI-Assisted Snake Sighting Monitoring and Community Safety Platform  
**Document Reference:** MCA-VW-2026-GIS-AUDIT  
**Audit Date:** October 20, 2026  
**Auditor:** Senior Software Architect (Antigravity AI Pair Engineer)  
**Implementation Source:** [`hotspots/services.py:DBSCANHotspotService`](file:///d:/dummyb/hotspots/services.py), [`reports/dispatch.py`](file:///d:/dummyb/reports/dispatch.py), [`reports/views.py`](file:///d:/dummyb/reports/views.py)  

---

## 1. Coordinate Sourcing, Validation and Preprocessing

### 1.1 Source of Geographic Coordinates
- **Citizen Sightings:** Captured on report creation via HTML5 Geolocation API (`navigator.geolocation.getCurrentPosition`) or user-selected point on the interactive location picker.
- **Ranger Operational Base:** Configured during account provisioning (`UserProfile.latitude`, `UserProfile.longitude`).
- **Hospital Directory:** Stored in `Hospital` model records.

### 1.2 Coordinate Validation and Filtering
- Implemented in `reports/views.py:_is_valid_coord(lat, lng)`:
  ```python
  def _is_valid_coord(lat, lng):
      try:
          if lat is None or lng is None:
              return False
          lat = float(lat)
          lng = float(lng)
          return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0 and not (lat == 0.0 and lng == 0.0)
      except (ValueError, TypeError):
          return False
  ```
- Excludes `None`, non-numeric inputs, latitude outside $[-90, 90]$, longitude outside $[-180, 180]$, and null island coordinates $(0.0, 0.0)$.

---

## 2. Spherical Distance Mathematics & Earth Radius

### 2.1 Haversine Implementation
The application implements spherical great-circle distance calculations across multiple modules:
- **`reports/dispatch.py:haversine_km(lat1, lon1, lat2, lon2)`:**
  - Earth radius constant: $R = 6371.0088\text{ km}$.
  - Returns distance rounded to 2 decimal places.
- **`reports/services.py:haversine_distance_meters(lat1, lon1, lat2, lon2)`:**
  - Earth radius constant: $R = 6,371,000.0\text{ meters}$.
- **`emergency/models.py:Hospital.distance_from(user_lat, user_lng)`:**
  - Earth radius constant: $R = 6371.0\text{ km}$.

### 2.2 Conversion to Radians
In `hotspots/services.py`, latitude and longitude coordinates are explicitly converted from decimal degrees to radians prior to scikit-learn DBSCAN execution:
```python
coords_rad = np.radians(coords)
kms_per_radian = 6371.0
epsilon = eps_km / kms_per_radian
```
This is a critical mathematical necessity: standard Euclidean distance on raw decimal degrees introduces massive spatial distortion because one degree of longitude shrinks towards the poles ($\cos(\phi)$). Converting to radians and using `metric='haversine'` guarantees geodesic accuracy.

---

## 3. DBSCAN Hotspot Clustering Engines

The application implements two separate DBSCAN clustering methods in `hotspots/services.py`:

### 3.1 Public Community Risk Zones (`compute_community_risk_zones()`)
- **Primary View:** [`reports/views.py:risk_zones_public_view`](file:///d:/dummyb/reports/views.py#L585-L610) (`/reports/risk-zones/`).
- **Algorithm Configuration:**
  - `metric = 'haversine'`
  - `algorithm = 'ball_tree'`
  - `eps_km = 1.5` $\implies \epsilon = 1.5 / 6371.0 \approx 0.0002354\text{ radians}$
  - `min_samples = 1` (Groups even single isolated incidents into distinct monitored risk zones).
- **Eligibility Filter:**
  - Non-rejected reports created within the total evaluation window:
    $$\text{max\_cutoff} = \text{now} - (\text{active\_hours} + \text{cooldown\_hours} + \text{retention\_hours}) = \text{now} - (24 + 24 + 48) = \text{now} - 96\text{ hours}$$
  - Excludes duplicates (`duplicate_flag=False`, `duplicate_of__isnull=True`) so multiple reports of the same snake count as **1 distinct incident**.
- **Four-State Incident Lifecycle per Zone:**
  - **RED (High Risk):** $\ge 3$ distinct active snake incidents within the zone ($color = \text{'#dc2626'}$).
  - **ORANGE (Caution):** 1–2 distinct active snake incidents ($color = \text{'#f97316'}$).
  - **YELLOW (Recently Resolved):** Captured or confirmed resolved within 24-hour cooldown ($color = \text{'#eab308'}$).
  - **GREEN (No Recent Active Incidents):** Cooldown completed; safe retention active for up to 48 hours ($color = \text{'#10b981'}$).
- **Centroid & Radius Calculation:**
  ```python
  center_lat = float(np.mean(clats))
  center_lng = float(np.mean(clngs))
  # If multiple points, radius covers maximum point distance + 250m padding
  radius_meters = max(500, int(np.max(distances)) + 250)
  ```
- **Privacy Preservation:** The public map renders circular boundary sectors and general locality labels (`reports[0].location_name`), strictly concealing exact resident coordinates.

### 3.2 Authority Surveillance Hotspot Radar (`compute_hotspots()`)
- **Primary View:** [`hotspots/views.py:hotspots_view`](file:///d:/dummyb/hotspots/views.py#L9-L18) (`/hotspots/`).
- **Algorithm Configuration:**
  - `eps_km = 1.0` $\implies \epsilon = 1.0 / 6371.0 \approx 0.00015696\text{ radians}$
  - `min_samples = 2` (Identifies density clusters containing at least 2 reports within 1.0 km).
  - Time window: reports submitted within 48 hours (`hours = 48`).
- **Noise Point Handling ($label = -1$):**
  - Isolated sightings that do not meet the core density threshold are not ignored:
    - If the isolated report is **venomous**, it is recorded as a single-incident cluster with `alert_level = 'MEDIUM_ALERT'`.
    - If non-venomous, it is added to `green_spots`.
- **Core Density Clusters ($label \ge 0$):**
  - If any report in the cluster is venomous: `alert_level = 'HIGH_ALERT'`.
  - If all reports in the cluster are non-venomous: `alert_level = 'GREEN_ZONE'`.

---

## 4. Frontend Map Rendering Architecture

- **Mapping Library:** Leaflet.js (v1.9.4).
- **Tile Layers:**
  - Primary: CartoDB Positron (`https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png`).
  - Fallback: Esri World Street Map & OpenStreetMap standard tiles.
- **Dynamic Polling & Marker Lifecycle:**
  - Authority map polls `GET /reports/api/map-reports/` every 30 seconds.
  - Sighting markers are dynamically color-coded:
    - Red: Unassigned venomous encounter.
    - Orange: Unassigned non-venomous encounter.
    - Blue: Active ranger response (`ACCEPTED`, `ON_THE_WAY`, `AT_LOCATION`, `OUTCOME_SUBMITTED`).
    - Green/Grey: Verified resolved / closed encounter.
- **Marker Spiderfying:** Reports sharing identical coordinates are visually separated using Leaflet radial spiderfying to prevent overlapping pins.

---

## 5. Limitations of Interpreting Report Density as Snake Risk

1. **Reporting / Population Bias:**
   - Sighting density correlates with human population density and smartphone access. Densely populated suburban areas generate higher report volumes than uninhabited forest reserves where snakes are actually more abundant.
2. **False Alarms & Species Misidentification:**
   - Unverified citizen submissions may include non-snake objects or harmless species before Authority verification.
3. **Temporal Ephemerality:**
   - Snakes are highly mobile ectotherms; a sighting represents a point-in-time encounter rather than a permanent territorial nest. The 24-hour active window and 24-hour resolution cooldown partially mitigate this limitation.
