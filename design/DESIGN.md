# VENOMWATCH — Stitch Design System Reference

This directory contains the Stitch-generated design system for the VENOMWATCH platform.
It is a **read-only design reference** used to guide UI/template development.

---

## Themes

VENOMWATCH has two design themes, both defined in `themes/`:

| File | Theme Name | Mode | Use Case |
|------|------------|------|----------|
| [`DESIGN_dark_tactical.md`](themes/DESIGN_dark_tactical.md) | Tactical Bio-Intelligence | **Dark** | Primary app UI — HUD-style, field operations, night mode |
| [`DESIGN_light_clinical.md`](themes/DESIGN_light_clinical.md) | Field Bio-Clinical Modern | **Light** | Clinical / authority views, reports, light-environment use |

---

## Quick Reference — Primary Theme (Dark Tactical)

> The primary applied theme is **Tactical Bio-Intelligence** (dark mode).

### Colors

| Role | Token | Value |
|------|-------|-------|
| Canvas / Background | `surface` / `background` | `#101413` |
| Card Foundation | `surface-container` | `#1C201F` |
| Elevated Surface | `surface-bright` | `#363A39` |
| Primary (Emerald) | `primary` | `#4EDEA3` |
| Primary Interactive | `primary-container` | `#10B981` |
| Secondary (Teal) | `secondary` | `#6BD8CB` |
| Danger / Venomous | `error` | `#EF4444` |
| Caution | — | `#F59E0B` |
| Primary Text | `on-surface` | `#E0E3E1` |
| Secondary Text | `on-surface-variant` | `#BBCABF` |
| Border | `outline-variant` | `#3C4A42` |
| Border (structural) | — | `#1E2E2A` |

### Typography

| Scale | Font | Size | Weight |
|-------|------|------|--------|
| `display-lg` | Space Grotesk | 48px | 700 |
| `headline-lg` | Space Grotesk | 32px | 600 |
| `headline-md` | Space Grotesk | 24px | 600 |
| `headline-sm` | Space Grotesk | 18px | 600 |
| `body-lg` | Geist | 16px | 400 |
| `body-md` | Geist | 14px | 400 |
| `body-sm` | Geist | 12px | 400 |
| `label-lg` | Space Grotesk | 14px | 600 |
| `label-md` | Space Grotesk | 12px | 500 |
| `label-sm` | Space Grotesk | 10px | 600 |

**Fonts to import**: `Space Grotesk`, `Geist`

### Spacing

| Token | Value |
|-------|-------|
| `space-xs` | 4px (0.25rem) |
| `space-sm` | 8px (0.5rem) |
| `space-md` | 16px (1rem) |
| `space-lg` | 24px (1.5rem) |
| `space-xl` | 40px (2.5rem) |
| `gutter` | 16px (1rem) |
| `gutter-desktop` | 24px (1.5rem) |
| `margin` | 16px (1rem) |
| `margin-desktop` | 32px (2rem) |

### Border Radius

| Token | Value |
|-------|-------|
| `rounded-sm` | 2px (0.125rem) |
| `rounded` (DEFAULT) | 4px (0.25rem) |
| `rounded-md` | 6px (0.375rem) |
| `rounded-lg` | 8px (0.5rem) |
| `rounded-xl` | 12px (0.75rem) |
| `rounded-full` | 9999px |

### Elevation / Shadows

| Layer | Surface | Blur | Shadow |
|-------|---------|------|--------|
| Layer 0 — Canvas | `#0B0F0E` solid | — | — |
| Layer 1 — Card | `#111716` @ 85% opacity | `blur(12px)` | `0 8px 24px rgba(0,0,0,0.6)` |
| Layer 2 — Floating / Hover | `#16201E` @ 92% opacity | `blur(16px)` | `0 12px 32px rgba(0,0,0,0.75)` |
| Layer 3 — Modal / Alert | `#121817` @ 96% opacity | `blur(20px)` | `0 0 20px rgba(239,68,68,0.15)` |

---

## Components Summary

### Buttons

| Type | Background | Text | Border | Hover |
|------|-----------|------|--------|-------|
| Primary Tactical | `#10B981` | `#0B0F0E` | none | `#059669` |
| Secondary HUD | `rgba(13,148,136,0.12)` | `#14B8A6` | `rgba(20,184,166,0.3)` | bg `rgba(13,148,136,0.24)` |
| Emergency / SOS | `#DC2626` | `#FFFFFF` | `#EF4444` | pulsing glow |
| Ghost / Tertiary | transparent | `#94A3B8` | `#1E2E2A` | text `#F1F5F9` |

### Status Badges / Hazard Pills

| State | Background | Text | Border |
|-------|-----------|------|--------|
| Venomous — Danger | `rgba(239,68,68,0.15)` | `#EF4444` | `rgba(239,68,68,0.4)` |
| Caution / Under Review | `rgba(245,158,11,0.15)` | `#F59E0B` | `rgba(245,158,11,0.4)` |
| Safe / Non-Venomous | `rgba(16,185,129,0.12)` | `#10B981` | `rgba(16,185,129,0.3)` |
| Telemetry Tag | `#16201E` | `#94A3B8` | `#1E2E2A` |

### Input Fields

- Background: `#111716`
- Border: `1px solid #1E2E2A`
- Placeholder text: `#475569`
- Active text: `#F1F5F9`
- Focus border: `#10B981` with `box-shadow: 0 0 0 1px #10B981`

### Cards

- Foundation: Layer 1 elevation (`#111716` bg, `1px #1E2E2A` border)
- Padding: `space-md` (16px) or `space-lg` (24px)
- Hazard top hairline: `2px` — `#EF4444` (venomous), `#10B981` (harmless)

### Checkboxes & Toggles

- Checkbox: 16×16px, 3px radius, inactive `#111716` bg / `#1E2E2A` border; checked: `#10B981` bg with dark checkmark
- Toggle: track `#1E2E2A`, thumb `#94A3B8`; active track `#064E3B`, active thumb `#10B981`

### Navigation

- Fixed top bar with `backdrop-blur`
- Active link: highlighted with `primary-container` background
- Emergency SOS link: pill-shaped red badge with pulsing animation

### Responsive Layout

| Breakpoint | Columns | Gutter | Notes |
|-----------|---------|--------|-------|
| Mobile (< 768px) | 1 col | 16px | Persistent threat banner, pinned SOS button |
| Tablet (768–1024px) | 8 col | — | 5-col map + 3-col triage stack |
| Desktop (1025px+) | 12 col | 24px | Full HUD layout, 32px outer margin |

---

## Screen References

All Stitch-generated screen mockups are in [`assets/screens/`](assets/screens/).

| Screen | PNG | HTML |
|--------|-----|------|
| Dashboard | `dashboard_venomwatch.png` | `dashboard_venomwatch.html` |
| Landing Page | `landing_page_venomwatch.png` | `landing_page_venomwatch.html` |
| Sign In | `sign_in_venomwatch.png` | `sign_in_venomwatch.html` |
| Register | `register_venomwatch.png` | `register_venomwatch.html` |
| Sign In / Register Combined | `sign_in_register_venomwatch.png` | `sign_in_register_venomwatch.html` |
| Identify a Snake | `identify_a_snake_venomwatch.png` | `identify_a_snake_venomwatch.html` |
| Report a Sighting | `report_a_snake_sighting_venomwatch.png` | `report_a_snake_sighting_venomwatch.html` |
| Risk Zones / DBSCAN Map | `risk_zones_dbscan_map_venomwatch.png` | `risk_zones_dbscan_map_venomwatch.html` |
| Wound Checker / Emergency SOS | `wound_checker_emergency_sos_venomwatch.png` | `wound_checker_emergency_sos_venomwatch.html` |
| Wildlife Authority Dashboard | `wildlife_authority_dashboard_venomwatch.png` | `wildlife_authority_dashboard_venomwatch.html` |
| Authority — All Sightings | `authority_all_sightings_venomwatch.png` | `authority_all_sightings_venomwatch.html` |
| Authority — Sighting Details | `authority_sighting_details_10_venomwatch.png` | `authority_sighting_details_10_venomwatch.html` |

Logo reference in [`assets/logo/`](assets/logo/).

---

## Icons

The design system uses **Google Material Symbols Outlined** icons, loaded via:

```html
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" rel="stylesheet"/>
```

Usage: `<span class="material-symbols-outlined">icon_name</span>`

Common icons used in screens: `verified_user`, `emergency`, `biotech`, `speed`, `nest_eco_leaf`, `person`, `settings`, `logout`, `expand_more`

---

> **Note**: This `design/` folder is a reference only. Do not apply changes to backend, models, views, or existing templates based on this folder until explicitly instructed.
