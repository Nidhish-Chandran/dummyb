# VENOMWATCH Design Reference

This directory contains the **Stitch design system reference** for the VENOMWATCH project.
It is extracted from `stitch_venomwatch_ui_platform.zip` and organized for use during UI development.

## Directory Structure

```
design/
├── DESIGN.md                          ← Master design reference (colors, typography, components, layout)
├── README.md                          ← This file
│
├── themes/
│   ├── DESIGN_dark_tactical.md        ← Full Stitch DESIGN.md — "Tactical Bio-Intelligence" (dark theme)
│   └── DESIGN_light_clinical.md      ← Full Stitch DESIGN.md — "Field Bio-Clinical Modern" (light theme)
│
└── assets/
    ├── screens/                       ← All screen mockups (PNG screenshots + Stitch HTML source)
    │   ├── dashboard_venomwatch.png / .html
    │   ├── landing_page_venomwatch.png / .html
    │   ├── sign_in_venomwatch.png / .html
    │   ├── register_venomwatch.png / .html
    │   ├── sign_in_register_venomwatch.png / .html
    │   ├── identify_a_snake_venomwatch.png / .html
    │   ├── report_a_snake_sighting_venomwatch.png / .html
    │   ├── risk_zones_dbscan_map_venomwatch.png / .html
    │   ├── wound_checker_emergency_sos_venomwatch.png / .html
    │   ├── wildlife_authority_dashboard_venomwatch.png / .html
    │   ├── authority_all_sightings_venomwatch.png / .html
    │   └── authority_sighting_details_10_venomwatch.png / .html
    │
    └── logo/
        ├── venomwatch_modern_light_logo.png
        └── venomwatch_modern_light_logo.html
```

## How to Use This Reference

1. **Read `DESIGN.md`** for the consolidated quick-reference covering colors, typography, spacing, components, buttons, badges, forms, navigation, and responsive rules.
2. **Open `themes/DESIGN_dark_tactical.md`** for the full structured design system specification of the primary dark HUD theme (used in the main app).
3. **Open `themes/DESIGN_light_clinical.md`** for the light clinical theme (used in authority/admin views).
4. **Browse `assets/screens/`** — open any `.html` file in a browser to view the live Stitch mockup, or view the `.png` for a quick screenshot.
5. **Check `assets/logo/`** for the logo design reference.

## Primary Theme

The primary app theme is **Tactical Bio-Intelligence (Dark)**.
- Fonts: `Space Grotesk` (headings/labels) + `Geist` (body)
- Primary color: `#10B981` (emerald/bio-telemetry green)
- Background: `#101413` (near-black)
- Icons: Google Material Symbols Outlined

## Source

Extracted from: `stitch_venomwatch_ui_platform.zip`
Date added: 2026-09-18
