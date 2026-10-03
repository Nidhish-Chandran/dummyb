# Application Feature Specification

## 1. Overview
An AI-powered public-safety and wildlife-response web platform for snake identification, venom detection, sighting reporting, geographic risk monitoring, and coordinated authority–ranger response.

## 2. User Roles

### Citizen
- Register, login, logout, and manage profile.
- Upload snake images for analysis.
- Detect snake vs. non-snake images.
- Identify supported snake species.
- Determine venomous/non-venomous status and confidence.
- Submit snake sighting reports.
- Provide latitude/longitude for sightings.
- View submitted reports.
- Use the wound/snake-bite checker.
- Access emergency/SOS functionality.

### Authority
- Secure authority authentication and role protection.
- Land directly on the Authority Map after login.
- Monitor individual snake incidents on a GIS map.
- View marker details, species, venom status, coordinates, and report status.
- Assign a suitable nearby available Ranger to a specific incident.
- Track Ranger assignment/response status.
- Access Risk Zones and DBSCAN hotspot information.
- Review and manage reported incidents.

### Ranger
- Secure Ranger authentication.
- Ranger-specific dashboard.
- Profile with name, contact, registered location, coordinates, and availability.
- See only incidents explicitly assigned to the Ranger.
- Accept and update assigned incidents.
- Track response through statuses such as ASSIGNED, ACCEPTED, ON_THE_WAY, AT_LOCATION, and COMPLETED.
- Availability states: AVAILABLE, BUSY, OFFLINE.
- Location-aware Ranger matching.
- Cannot access the Authority dashboard, all reports, other Rangers' assignments, or assignment controls.

### Admin
- Django administrative access.
- User/account administration.
- System and application-data administration according to permissions.

## 3. Authentication & Sessions
- User registration and login.
- Role-based routing and protected URLs.
- Persistent authenticated sessions during normal navigation.
- Proper logout/session termination.
- Redirect to login when unauthenticated users access protected pages.
- Re-login after logout.
- Appropriate session expiration.
- No unnecessary logout-success banner.
- Authentication errors remain available.

### Authority Login Flow
```text
Authority Login
      ↓
Authority Map
      ↓
Monitor Incident
      ↓
Open Report
      ↓
Assign Nearby Available Ranger
```

## 4. Snake AI Identification

### Image Analysis
- Image upload and preview.
- Fresh analysis whenever the selected image changes.
- Previous results cleared when a new image is selected.
- Error handling for failed analysis.

### Snake / Not-Snake
- Determine whether the image contains a snake.
- Support a NOT_SNAKE negative class where included in the trained model.
- Avoid forcing unrelated images into a snake class.

### Species & Venom
- Classify supported snake species using the trained CNN pipeline.
- Determine venomous/non-venomous status.
- Display species, venom status, and confidence where available.
- Use the actual trained model class mapping rather than an incorrect hard-coded mapping.

### Reporting Gate
- A venomous result can expose an option for the citizen to report the sighting.
- Reporting remains a user action separate from prediction.

## 5. Snake Sighting Reports
Reports can contain:
- Snake species.
- Venom status.
- Image/result information.
- Sighting location.
- Latitude/longitude.
- Date/time.
- Report status.
- Ranger assignment/response information where applicable.

Reports are stored in the database and made available to authorized authorities.

## 6. Geographic Location
- Browser GPS detection.
- Latitude/longitude capture.
- Location display.
- Coordinate storage.
- Geographic report visualization.
- Location-aware Ranger matching.
- Haversine distance calculation where coordinates are available.

## 7. Authority GIS Map
The Authority Map is the primary Authority incident-management interface.

Features:
- Dedicated `/authority/map/` page.
- Authority login redirects directly to the map.
- Map is the first major item in the Authority navbar.
- Individual snake report markers.
- Marker colors/statuses.
- Marker popups.
- Report details.
- Species and venom information.
- Coordinates.
- Ranger assignment from report details.
- Nearby available Ranger discovery.
- Assignment/status tracking.

### Authority Navbar
```text
Map | Risk Zones | Wound Checker | Emergency SOS | Profile | User Identity | Logout
```

There must be only one Logout button.

## 8. Ranger Assignment
Authorities assign Rangers to specific reports.

### Matching
Filter Rangers by:
- Ranger role.
- Availability.
- Registered location.
- Coordinates.
- Distance from incident.

When coordinates exist, Haversine distance can rank nearby Rangers.

### Assignment Workflow
```text
ASSIGNED
   ↓
ACCEPTED
   ↓
ON_THE_WAY
   ↓
AT_LOCATION
   ↓
COMPLETED
```

Optional states:
- DECLINED
- CANCELLED

Object-level security ensures a Ranger sees only assigned incidents.

## 9. DBSCAN Risk Zones
- Spatial clustering of snake reports.
- Geographic hotspot identification.
- Cluster visualization.
- Authority-level risk monitoring.
- Separate Risk Zones feature from individual incident management.

## 10. Wound / Snake-Bite Checker
Separate AI workflow:
```text
Wound Image
    ↓
EfficientNetB0
    ↓
Analysis
    ↓
Snake-bite / Non-snake-bite Result
```

Referenced model:
`venom_watch_snakebite_efficientnetb0.keras`

## 11. Emergency SOS
- Emergency-response interface.
- Accessible through the application navigation.
- Supports emergency-response information/workflows implemented by the project.

## 12. Profile
- User profile page.
- Account information.
- Role information.
- Ranger operational information where applicable.
- Navbar identity area links to `/accounts/profile/`.

## 13. Security & Access Control

### Citizen
Can access citizen functionality, own reports, AI analysis, wound checker, and emergency functionality.

Cannot access Authority-only incident management or Ranger administration.

### Authority
Can access Authority Map, incident management, Ranger assignment, Risk Zones, and Authority operational tools.

### Ranger
Can access assigned incidents and Ranger operational functions.

Cannot access Authority dashboard, all reports, other Rangers' assignments, or assignment controls.

### Admin
Has administrative/system-level access according to Django permissions.

## 14. Map & Marker System
- Leaflet-based interactive maps where currently used.
- Individual report markers.
- Marker status/colors.
- Species and venom information.
- Coordinates.
- Marker click → report details.
- Report details → Ranger assignment.

The map basemap should use a legitimate configured provider and must not depend on an invalid CARTO/API-key configuration.

## 15. Technology Stack

### Backend
- Python
- Django
- Django ORM
- Django authentication
- SQLite currently
- PostgreSQL planned/possible for future deployment

### AI/ML
- Python
- TensorFlow/Keras
- CNN-based snake classification
- EfficientNetB0 wound classifier
- Image preprocessing and inference

### Frontend
- HTML
- CSS
- JavaScript
- Django Templates
- Leaflet where used
- Responsive UI

### Geospatial
- Latitude/longitude
- DBSCAN
- Haversine distance

### Database
Application data includes:
- Users/profiles
- Snake sightings/reports
- Hotspot clusters
- Emergency-response data
- Ranger assignments/operational data where implemented

## 16. AI Architecture

### Snake Pipeline
```text
User Image
    ↓
Preprocessing
    ↓
CNN
    ↓
Snake / Not-Snake
    ↓
Species
    ↓
Venom Status
    ↓
Confidence / Result
    ↓
Optional Report
```

### Wound Pipeline
```text
Wound Image
    ↓
Preprocessing
    ↓
EfficientNetB0
    ↓
Classification
    ↓
Result
```

YOLO is not part of the intended final snake-identification pipeline.

## 17. End-to-End Workflow

```text
Citizen
   ↓
Upload Snake Image
   ↓
AI Analysis
   ↓
Snake + Species + Venom Status
   ↓
Citizen Chooses to Report
   ↓
Sighting Report + Location
   ↓
Authority Map
   ↓
Authority Reviews Incident
   ↓
Nearby Ranger Matching
   ↓
Ranger Assignment
   ↓
Ranger Response
   ↓
Status / Outcome
```

## 18. Main Modules

| Module | Purpose |
|---|---|
| Authentication | Registration, login, logout, sessions |
| Citizen | Snake analysis and reporting |
| Snake AI | Snake/species/venom analysis |
| Wound Checker | Snake-bite/wound analysis |
| Reports | Snake sighting management |
| Authority Map | GIS incident monitoring |
| Ranger | Assigned incident response |
| Risk Zones | DBSCAN hotspot detection |
| Emergency SOS | Emergency-response functionality |
| Profiles | Account/operational information |
| Admin | System administration |

## 19. Core Goals
1. Assist users in identifying snakes from images.
2. Determine venomous status.
3. Enable structured snake-sighting reports.
4. Attach geographic information to incidents.
5. Provide authorities with a centralized GIS incident view.
6. Identify geographic risk hotspots.
7. Match incidents with nearby available Rangers.
8. Restrict incident visibility according to role and assignment.
9. Track Ranger response status.
10. Provide AI-assisted wound/snake-bite checking.
11. Provide emergency-response functionality.
12. Maintain secure authentication and role-based access.

## 20. Responsibility Model

```text
CITIZEN
  Reports incident
       ↓
AUTHORITY
  Reviews and assigns response
       ↓
RANGER
  Handles assigned incident
       ↓
AUTHORITY
  Monitors response/outcome
```

## 21. Setup Instructions & Demo Credentials

### Setup Instructions
1. **Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Database Migrations:**
   ```bash
   python manage.py migrate
   ```
3. **Demo Data Seeding:**
   ```bash
   python seed_demo_data.py
   ```
4. **Run Development Server:**
   ```bash
   python manage.py runserver 127.0.0.1:8000
   ```

### Demo Accounts & Credentials
| Role | Username | Password | Default Landing Page |
|---|---|---|---|
| **Authority** | `authority_demo` | `authority_demo123` | `/authority/map/` |
| **Ranger** | `ranger_demo` | `ranger_demo123` | `/ranger/` |
| **Citizen** | `john_citizen` | `citizen_demo123` | `/reports/` |
| **Administrator** | `admin_demo` | `admin_demo123` | `/admin/` |

