# Venom Watch — Technical Implementation Report

**Project Title:** Venom Watch — AI-Assisted Snake Sighting, Surveillance & Emergency Support System  
**Academic Level:** Intermediate MCA Prototype  
**Framework:** Django 5.1 / Python 3.11  
**Database:** SQLite 3 (`db.sqlite3`)  
**Design Theme:** Public Safety Light-Neutral Theme (`#f8fafc` background, crisp white cards, forest/teal green `#0d9488` primary accent)

---

## 1. Executive Summary & Project Overview

**Venom Watch** is an AI-assisted snake sighting, incident monitoring, and emergency response platform. It bridges community reporting with wildlife authorities and medical emergency responders. The system enables citizens to upload snake sighting photos for feature analysis, log GPS coordinates, track verification progress, access an AI wound screening tool, locate nearby anti-venom hospitals sorted by spatial distance, and view aggregated community risk zones without exposing private citizen coordinates.

Wildlife authorities receive a dedicated GIS surveillance console featuring interactive Leaflet maps, real-time incident markers, DBSCAN spatial density clustering, duplicate and spam review flags, verification controls, and responder task assignment workflows.

---

## 2. Problem Addressed

1. **Human-Wildlife Conflict & Delayed Response**: Rapid urbanization increases snake encounters. Lack of instant identification leads to panic, delayed medical care, or unnecessary killing of harmless non-venomous species.
2. **Geospatial Reporting Inflation**: Multiple citizens reporting the same snake produce duplicate records, artificially inflating incident counts if not algorithmically flagged.
3. **Public Privacy vs. Surveillance Conflicts**: Exposing exact coordinates of citizen reports to the public compromises user privacy and creates localized panic.
4. **Emergency Logistics Delay**: Snakebite victims often struggle to find which medical centers have active polyvalent anti-venom stocks and ICU beds nearby.

---

## 3. System Architecture & Tech Stack

```
                                +-------------------------+
                                |   Citizen / Responder   |
                                +------------+------------+
                                             |
                                   (Public / Role Views)
                                             |
+-------------------+           +------------v------------+           +-------------------+
|  Emergency Module | <-------> |    Django Web Engine    | <-------> |   AI & Feature    |
| (Haversine Sort)  |           | (Views, Auth, Models)   |           | Processing Engine |
+-------------------+           +------------+------------+           +-------------------+
                                             |
                                    (ORM / SQLite 3)
                                             |
                                +------------v------------+
                                |  Wildlife Authority GIS |
                                | (DBSCAN / Risk Zones)   |
                                +-------------------------+
```

### Technology Stack Rationale

| Layer | Technology | Selection Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | Python / Django 5.1 | Robust MVT architecture, built-in ORM, secure auth & `@login_required` / `@never_cache` decorators. |
| **Database Engine** | SQLite 3 | Relational RDBMS, lightweight, standard 64-bit auto-increment keys (`BigAutoField`). |
| **Computer Vision Engine** | OpenCV (`cv2`) & NumPy | Dual-puncture contour geometry & HSV erythema feature extraction, bounding box overlays. |
| **Spatial Clustering** | scikit-learn (`DBSCAN`) | Density-based spatial clustering using Haversine metric without predefined cluster counts. |
| **Distance Metric** | Haversine Formula | Exact spherical distance computation for hospital locator and duplicate detection. |
| **Frontend & GIS** | HTML5, CSS3, JS, Leaflet | Clean light-neutral palette, crisp cards, interactive map rendering via OpenStreetMap tiles. |

---

## 4. Database Architecture & Data Models

### 4.1. Core Entities

1. **`auth_user` & `UserProfile` (`accounts`)**:
   - Extends Django user model via `OneToOneField` with `post_save` signals.
   - Role Enum: `citizen` (Public), `authority` (Forest Officer/Wildlife Authority), `responder` (Medical/Rescue Team).
   - Session & Authentication: Standard Django auth (`django.contrib.auth.logout`) with `@never_cache` header enforcement to prevent session leaks on browser back navigation.
2. **`SightingReport` (`reports`)**:
   - Core transaction model containing `user`, `title`, `original_image`, `processed_image`, `latitude`, `longitude`, `location_name`, `status` (`PENDING`, `VERIFIED`, `REJECTED`, `RESOLVED`).
   - AI Metadata: `ai_detected`, `species_predicted`, `common_name`, `venom_category`, `toxicity_level`, `danger_score`, `ai_confidence`.
   - Security & Task Flags: `duplicate_flag`, `duplicate_of`, `spam_flag`, `spam_reason`, `assigned_responder`, `response_status` (`UNASSIGNED`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`).
3. **`Hospital` (`emergency`)**:
   - Stores emergency medical infrastructure, contact helplines, `latitude`, `longitude`, `anti_venom_available`, `anti_venom_stock_vials`, `has_icu`, and `operating_hours`.

---

## 5. Key Workflows & Algorithm Specifications

### 5.1. Snake Identification & Species Mapping Pipeline
- Image uploaded $\rightarrow$ OpenCV converts to HSV & Grayscale $\rightarrow$ Canny edge & contour detection locates bounding box $\rightarrow$ HSV hue/value hashing maps species using controlled `SNAKE_DATABASE` dictionary $\rightarrow$ Annotated image output generated.
- Results labeled as **"AI-Assisted Screening (Evaluation in Progress)"** using verified species-to-venom category mappings (`HIGHLY_VENOMOUS`, `VENOMOUS`, `NON_VENOMOUS`).

### 5.2. Snakebite Wound Image Checker (`WoundScreeningService`)
- Dedicated binary screening tool (`/ai/wound-check/`).
- Performs adaptive thresholding, dual puncture contour geometry (fang distance $15\text{px} \le d \le 150\text{px}$), and HSV erythema ratio analysis.
- Binary Output ONLY: **`Snake Bite`** (`Possible Snake Bite Pattern Detected`) vs **`Not Snake Bite`** (`No Snake-Bite Pattern Detected`).
- Clearly labeled as: *"Prototype / Heuristic Visual Feature Screening (Dataset Model Training In Progress)"*.
- Mandatory Disclaimer Attached: *"This is an AI-assisted screening tool and is NOT a medical diagnosis. If a snakebite is suspected, seek emergency medical care immediately."*

### 5.3. Duplicate & Spam Detection Engine (`DuplicateSpamDetectionService`)
- **Duplicate Rule**: Flags reports submitted within **500 meters** ($0.5\text{ km}$) spatial distance and **2 hours** temporal window of a recent report (`duplicate_flag = True`, links `duplicate_of`).
- **Spam Rule**: Flags rate-limit violations (>3 submissions in 5 mins by same user) (`spam_flag = True`, `spam_reason`).
- Reports are **flagged for authority review** rather than automatically deleted.

### 5.4. Community Risk Zones vs. Authority GIS Map
- **Public Community Risk Zones** (`/reports/risk-zones/`):
  - **GREEN**: 0 active reports in 24h window
  - **YELLOW**: 1–5 active reports in 24h window
  - **RED**: >5 active reports in 24h window
  - Aggregated by locality; **NO** individual markers or exact citizen coordinates exposed.
- **Authority GIS Map Console** (`/dashboard/`):
  - Restricted to `Authority` and `Admin` users via `@authority_required`.
  - Displays full map with exact markers, DBSCAN density rings, filter controls, verification form, and responder assignment tools.

### 5.5. Haversine Emergency Hospital Locator
- Computes spherical distance $d = 2R \arcsin\left(\sqrt{\sin^2(\Delta \phi/2) + \cos \phi_1 \cos \phi_2 \sin^2(\Delta \lambda/2)}\right)$.
- Sorts medical centers by distance in kilometers; displays anti-venom vial inventory and 24/7 ICU availability.

---

## 6. Implementation Status & Feature Breakdown

| Feature | Category | Implementation Status | Description |
| :--- | :--- | :--- | :--- |
| **Role-Based Access (RBAC)** | Security | **COMPLETED** | Enforced across Django views via decorators & backend checks. |
| **Django Logout & Session Protection** | Auth / Security | **COMPLETED** | Direct POST form dropdown, session flush, `@never_cache` on protected views. |
| **Light-Neutral Theme** | UI/UX | **COMPLETED** | Modern palette (`#f8fafc`, crisp white cards, `#0d9488` teal accents). |
| **GPS Geolocation & Fallback**| Reporting | **COMPLETED** | Auto GPS capture with explicit warning alert and manual map picker fallback. |
| **OpenCV AI Feature Engine** | AI / Vision | **COMPLETED** | Contour bounding boxes, species database mapping, evaluation label. |
| **Snakebite Wound Checker** | AI Screening | **COMPLETED** | Binary screening (`Snake Bite` vs `Not Snake Bite`) with dual puncture pair geometry & disclaimer. |
| **Duplicate Detection** | Algorithmic | **COMPLETED** | 500m & 2h spatial-temporal duplicate flagging. |
| **Spam Rate Limiting** | Algorithmic | **COMPLETED** | User submission rate limit flagging. |
| **24h Public Risk Zones** | GIS / Safety | **COMPLETED** | Aggregated GREEN (0), YELLOW (1-5), RED (>5) community zones. |
| **Authority GIS Map** | GIS / Security | **COMPLETED** | Interactive surveillance map with DBSCAN density rings (Authority Only). |
| **Responder Task Workflow** | Logistics | **COMPLETED** | Task assignment (`UNASSIGNED`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`). |
| **Haversine Hospital Locator** | Emergency | **COMPLETED** | Distance sorting, anti-venom stock count, verified helplines (108/1926). |
| **Deep Learning Model Training**| AI Training | **IN PROGRESS** | Model dataset training and evaluation labeled as in-progress. |

---

## 7. Commands to Run & Test the Project

```bash
# 1. Activate Python Environment & Navigate to Directory
cd d:\miniproj\venomwatch

# 2. Run Database Migrations
python manage.py makemigrations
python manage.py migrate

# 3. Seed Demo Data (Hospitals, Users, Sample Sightings)
python seed_demo_data.py

# 4. Execute Automated Unit Tests
python manage.py test

# 5. Start Local Development Server
python manage.py runserver 0.0.0.0:8000
```
