---
name: Field Bio-Clinical Modern
colors:
  surface: '#f8f9ff'
  surface-dim: '#ccdbf3'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e6eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d5e3fc'
  on-surface: '#0d1c2e'
  on-surface-variant: '#3d4a42'
  inverse-surface: '#233144'
  inverse-on-surface: '#eaf1ff'
  outline: '#6d7a72'
  outline-variant: '#bccac0'
  surface-tint: '#006c4a'
  primary: '#006948'
  on-primary: '#ffffff'
  primary-container: '#00855d'
  on-primary-container: '#f5fff7'
  inverse-primary: '#68dba9'
  secondary: '#006a61'
  on-secondary: '#ffffff'
  secondary-container: '#86f2e4'
  on-secondary-container: '#006f66'
  tertiary: '#bb0112'
  on-tertiary: '#ffffff'
  tertiary-container: '#e02928'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#85f8c4'
  primary-fixed-dim: '#68dba9'
  on-primary-fixed: '#002114'
  on-primary-fixed-variant: '#005137'
  secondary-fixed: '#89f5e7'
  secondary-fixed-dim: '#6bd8cb'
  on-secondary-fixed: '#00201d'
  on-secondary-fixed-variant: '#005049'
  tertiary-fixed: '#ffdad6'
  tertiary-fixed-dim: '#ffb4ab'
  on-tertiary-fixed: '#410002'
  on-tertiary-fixed-variant: '#93000b'
  background: '#f8f9ff'
  on-background: '#0d1c2e'
  surface-variant: '#d5e3fc'
typography:
  display-lg:
    fontFamily: Space Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-xl:
    fontFamily: Space Grotesk
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Space Grotesk
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: 0em
  title-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: 0em
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
    letterSpacing: 0em
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0em
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
  code-sm:
    fontFamily: Space Grotesk
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system establishes a life-critical, authoritative, and biologically grounded aesthetic for AI-assisted venomous reptile classification, bite prevention, and medical emergency management. It balances the analytical precision of clinical healthcare software with the approachable, field-ready ruggedness required by outdoor professionals, researchers, and rural residents.

The interface delivers high-stakes reassurance:
- **Clinical Competence:** Visual rhythm and typography signal forensic reliability and scientific accuracy.
- **Urgency Separation:** Critical hazards (venom severity, venomous vs. non-venomous calls) remain sharply distinct from standard navigation and routine metadata, preventing alert fatigue while providing unmistakable immediate guidance.
- **Field Ergonomics:** High legibility under direct sunlight, well-proportioned touch targets for stressful outdoor interactions, and high optical contrast.

The visual direction pairs **Modern Bio-Minimalism** with structural card-based layouts, utilizing soft botanical tints, disciplined hairline borders, and subdued environmental shadows to cultivate deep trust and clarity.

## Colors

The palette balances serene natural tones with unmistakable biosafety accents:

- **Canvas & Surfaces:**
  - Base Canvas: `#F8FAFC` (Slate-50) for a glare-free, clinical backdrop.
  - Secondary Canvas / Neutral Sections: `#F1F5F9` (Slate-100).
  - Elevated Surfaces / Cards: Pure white `#FFFFFF`.
  - Bio-Tint Accent Panels: `#ECFDF5` (Mint-50) and `#F0FDF4` (Emerald-50) for habitat, non-threatening identification highlights, and low-risk verification panels.

- **Brand & Actions:**
  - Primary Core: `#059669` (Emerald-600) driving core interactive paths, search, navigation, and safe field actions.
  - Active/Hover State: `#047857` (Emerald-700).
  - Secondary Core: `#0D9488` (Teal-600) dedicated to sensor telemetry, AI confidence scores, and analytical metadata.

- **Status & Hazard Hierarchy:**
  - **Safe / Harmless:** `#15803D` (Forest Green) on `#DCFCE7` (Green-100) background. Communicates harmless/non-venomous classification.
  - **Caution / Mild Venom / Lookalike:** `#D97706` (Amber-600) on `#FEF3C7` (Amber-100) background. Flags rear-fanged, non-fatal venom, or uncertain machine vision certainty.
  - **Danger / Highly Venomous / Antivenom Protocol:** `#DC2626` (Red-600) on `#FEE2E2` (Red-100). Restricted strictly to medically significant species, active envenomation warnings, and SOS calls to poison control.

- **Borders & Dividers:**
  - Primary Border: `#E2E8F0` (Slate-200) for clean structural boundaries.
  - Accent Bio-Border: `#A7F3D0` (Emerald-200) used when highlighting confirmed non-venomous results or medical safe-zones.

## Typography

Typography establishes an immediate division between technical identification and rapid behavioral triage:

- **Headlines (Space Grotesk):** Provides structured geometric legibility with an authoritative, scientific tone. It is utilized across high-level headers, species names, and AI confidence metric indicators.
- **Body & Labels (Plus Jakarta Sans):** Selected for its humanist, open aperture profile, delivering effortless legibility in critical emergency instructions, treatment protocols, and data tables.
- **Scientific Nomenclature Rule:** Binomial nomenclature (e.g., *Crotalus atrox*) must always be italicized within `body-md` or `title-md`, maintaining standard biological typesetting while preserving Space Grotesk for the common name headline.
- **Labels & Micro-data:** Micro badges and status pills use `label-sm` in uppercase tracking (`letter-spacing: 0.05em`) to ensure instant recognition in high-stress triage situations.

## Layout & Spacing

The layout is built upon an adaptive 12-column grid designed to integrate with Django server-rendered templates, CSS grids, and mobile emergency viewports:

- **Grid Systems:**
  - **Desktop (1200px+):** 12-column grid, 80px max column width, 24px (`gutter`) gutters, 32px (`margin`) page gutters. Max canvas container pinned at `1280px`.
  - **Tablet (768px – 1199px):** 8-column layout, 20px gutters, 24px margins. Two-column card arrangements reflow into single vertical stacks where hazard severity is heightened.
  - **Mobile (<768px):** 4-column layout with 16px (`gutter-mobile`) gutters and 16px (`margin-mobile`) horizontal margin. All critical emergency actions (e.g., "Call Antivenom Center", "Identify Snake") pin to fixed bottom thumb zones with full container width.
- **Spacing Rhythm:** Standard spacing increments adhere strictly to a 4px/8px baseline grid to keep data density crisp and scanning effortless.

## Elevation & Depth

Visual hierarchy uses clean structural boundaries and ambient lighting:

- **The Ground Plane:** Canvas begins at `#F8FAFC`. Base content sits on solid white `#FFFFFF` cards with a crisp 1px perimeter border (`#E2E8F0`).
- **Diffused Ambient Shadows:** Avoid stark, drop-shadow black. Elevation uses subtle forest-tinted diffusion:
  - **Level 1 (Standard Card / Resting Component):** `0 1px 3px 0 rgba(15, 23, 42, 0.05), 0 1px 2px -1px rgba(15, 23, 42, 0.05)` coupled with a 1px border (`#E2E8F0`).
  - **Level 2 (Interactive Hover / Floating Panels):** `0 10px 15px -3px rgba(5, 150, 105, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.04)` combined with primary brand border shift (`#A7F3D0`).
  - **Level 3 (Emergency Modals / Critical Diagnostic Overlay):** `0 20px 25px -5px rgba(220, 38, 38, 0.12), 0 8px 10px -6px rgba(15, 23, 42, 0.06)` with high-contrast safety red reinforcement (`#FECACA`).
- **Tonal Layers:** Tonal stacking is favored over multiple shadow layers. Emergency sidebars and metadata tables rely on light tint fills (`#ECFDF5` for safe context, `#FEE2E2` for lethal venoms) nested directly inside white cards.

## Shapes

The design uses a balanced rounded shape system (Level 2):
- **Base Geometry:** Standard components (cards, text inputs, modal dialogue bodies) use `0.5rem` (8px) corner radii.
- **Large Assemblies:** Image diagnostic cards, map containers, and medical treatment flow wrappers use `1rem` (16px) corner radii.
- **Pill Tags & Status Badges:** Badges, triage alerts, and verification indicators use pill boundaries (`9999px`) to immediately signal interactive or status categorization distinct from structural card containers.
- **Camera Viewfinder / Scan Targets:** AI detection bounding boxes apply a 4px corner radius with an internal dashed hairline border to reinforce computer vision analysis without obscuring reptile morphology.

## Components

### Buttons
- **Primary Action (Standard):** Deep emerald background (`#059669`), white text, `0.5rem` radius, `0.75rem 1.5rem` padding. On hover: `#047857`. Focus ring: 3px `#A7F3D0`.
- **Emergency / Danger Action (Venom Warning / Call SOS):** High-contrast safety red (`#DC2626`), white text, bold font-weight (`600`). On hover: `#B91C1C`. Focus ring: 3px `#FECACA`.
- **Secondary Action:** White background with `#E2E8F0` border, `#0F172A` text. Hover brings `#F8FAFC` background with `#059669` border.
- **Ghost / Tertiary:** Transparent background, `#059669` text, hover with `#ECFDF5` fill.

### Status Chips & Badges
- **Venomous Status Pill:** `#FEE2E2` background, `#DC2626` text, bold `label-sm` typography, accompanied by a solid warning icon.
- **Harmless Status Pill:** `#DCFCE7` background, `#15803D` text, bold `label-sm` typography, accompanied by a shield icon.
- **AI Confidence Score:** Pill with `#F0FDFA` background, `#0D9488` border and text, displaying exact percentage with `code-sm`.

### Input Fields & Upload Drag-Drop
- **Field Inputs:** Crisp `#FFFFFF` background, 1px border (`#CBD5E1`), 8px radius, `0.625rem 1rem` padding. On focus: border shifts to `#059669` with a 3px halo of `#ECFDF5`.
- **Diagnostic Upload Box:** Dashed border (`2px dashed #A7F3D0`) over an `#ECFDF5` canvas. Drag-over switches border to `#059669` with `#D1FAE5` background.

### Cards & Species Classification Containers
- **Standard Card:** Crisp `#FFFFFF` surface, 1px `#E2E8F0` border, `1.5rem` internal padding, subtle Level 1 shadow.
- **Diagnostic Result Card (Venomous):** `#FFFFFF` surface featuring a bold 4px left-accent border in `#DC2626`, top hazard banner in `#FEE2E2`, and immediate first-aid collapsible drawer.
- **Diagnostic Result Card (Harmless):** `#FFFFFF` surface with a 4px left-accent border in `#15803D` and verification mark badge.

### Lists & Protocol Steps
- **Emergency Bite Steps:** Ordered list utilizing solid circular badges with red backgrounds (`#DC2626`) for DO steps, and crossed circular slate badges for DO NOT steps (e.g., "Do not tourniquet", "Do not cut wound").
- **Species Attribute Table:** Alternating rows using `#FFFFFF` and `#F8FAFC`, hairline dividers (`#E2E8F0`), with bolded biological key traits in `title-md`.