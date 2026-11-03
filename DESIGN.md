---
name: Omiver website
description: The Clear Clinic system for Omiver's public pages, and the target system for the provider portal, demo and auth screens migrating onto it.
colors:
  action: "#436e57"
  action-hover: "#3a6049"
  action-press: "#30503d"
  sage: "#67997d"
  sage-soft: "rgba(103, 153, 125, 0.14)"
  ring: "rgba(67, 110, 87, 0.45)"
  ink: "#0f1720"
  ink-2: "#4e5862"
  ink-3: "#5d666e"
  bg: "#ffffff"
  canvas: "#f6f8f7"
  panel: "#eef3f0"
  panel-strong: "#e2ebe5"
  line: "rgba(15, 23, 32, 0.1)"
  line-strong: "rgba(15, 23, 32, 0.18)"
  featured-tick: "#cfe3d6"
  success-ink: "#1c4a33"
  error-ink: "#94261f"
  error-soft: "rgba(148, 38, 31, 0.08)"
typography:
  display:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "clamp(2.5rem, 1.7rem + 2.6vw, 3.75rem)"
    fontWeight: 650
    lineHeight: 1.02
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "clamp(2rem, 1.5rem + 1.8vw, 3rem)"
    fontWeight: 650
    lineHeight: 1.08
    letterSpacing: "-0.028em"
  title:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.1875rem"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  lede:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "clamp(1.125rem, 1rem + 0.4vw, 1.3125rem)"
    fontWeight: 400
    lineHeight: 1.5
  body:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    lineHeight: 1.4
  micro:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.65
rounded:
  sm: "10px"
  md: "16px"
  lg: "24px"
  full: "999px"
spacing:
  gutter: "clamp(20px, 4vw, 48px)"
  section: "clamp(72px, 9vw, 128px)"
  wrap: "1200px"
  panel-pad: "26px 28px 28px"
  grid-gap: "20px"
components:
  button-primary:
    backgroundColor: "{colors.action}"
    textColor: "{colors.bg}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    padding: "0 26px"
    height: "52px"
  button-primary-hover:
    backgroundColor: "{colors.action-hover}"
  button-primary-active:
    backgroundColor: "{colors.action-press}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.action}"
    rounded: "{rounded.full}"
    padding: "0 26px"
    height: "52px"
  button-secondary-hover:
    backgroundColor: "{colors.sage-soft}"
  button-small:
    rounded: "{rounded.full}"
    padding: "0 18px"
    height: "42px"
  button-light:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.action}"
    rounded: "{rounded.full}"
  button-light-hover:
    backgroundColor: "{colors.panel}"
  benefit-panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "26px 28px 28px"
  plan-card:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "clamp(28px, 3vw, 40px)"
  plan-card-featured:
    backgroundColor: "{colors.action}"
    textColor: "{colors.bg}"
  input-field:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "13px 14px"
  molecule-chip:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.full}"
    padding: "14px 22px 14px 16px"
  journey-step-number:
    backgroundColor: "{colors.sage-soft}"
    textColor: "{colors.action}"
    rounded: "{rounded.full}"
    size: "44px"
  platform-band:
    backgroundColor: "{colors.action}"
    textColor: "{colors.bg}"
    padding: "clamp(48px, 6vw, 88px) clamp(24px, 5vw, 72px) 0"
  site-header:
    backgroundColor: "rgba(255, 255, 255, 0.82)"
    textColor: "{colors.ink}"
    height: "76px"
---

# Design System: Omiver website

Scope: every surface served by `omiver-website`. The colour values deliberately match the React app's `omiver-app/src/styles/tokens.css` so the site and app read as one product, but this file governs only `omiver-website`. Tokens live as CSS custom properties on `:root` in `core/static/core/site.css`; `core/static/core/legal/style.css` consumes them. The frontmatter above is normative and describes only the Clear Clinic system; no legacy value appears in it.

| Surface | Templates / CSS | Status |
|---|---|---|
| Public pages: home, `/information`, header/footer, contact, `/terms`, `/privacy` | `core/templates/core/`, `core/static/core/` | **Clear Clinic**, implemented |
| Provider portal `/dashboard/` (clients, profile, plans, support, settings, chatbot) | `dashboard/`, `components/` | **Legacy**, migrating to Clear Clinic |
| Product walkthrough `/demo/` | `demo/` | **Legacy**, migrating to Clear Clinic |
| Login and register | `core/templates/core/login.html`, `register.html` (extend `demo/two_column_layout.html`), `core/static/core/login/` | **Legacy**, migrating to Clear Clinic |

Legacy surfaces inherit `templates/base.html` (Open Sans from Google Fonts, `static/style.css`), don't read the `:root` tokens, and hard-code every value. They are written down below as an inventory of known debt so nobody copies them by mistake. They are not a second system.

## Overview

**Creative North Star: "The Clear Clinic"**

A calm, well-lit consulting room for your own biology: a white, faintly green-tinted canvas, one confident sans, and a single deep sage colour that means "act here". The world is the category standard for at-home health testing, done carefully. It earns trust through restraint, real product photography and real product screenshots, not through decoration.

Density is low and the rhythm is generous: sections breathe on a fluid 72–128px vertical step, copy sits in narrow measures, and content groups into soft rounded pale-sage panels or open lists divided by thin hairlines. Motion is quiet: a short fade-up reveal on scroll, small hover shifts, nothing that loops.

Depth comes mostly from tone (white → canvas → panel), with one soft ambient shadow reserved for photography and screenshots.

**Key Characteristics:**
- Near-white canvas with a green cast; ink text, never pure black.
- Deep sage (`action`) is the only filled-control colour; mid sage is for tints only.
- One family, Figtree variable, self-hosted, with tight negative tracking on headings.
- Soft geometry: 24px panels, 16px inner frames, full-pill controls and chips.
- Real assets only: kit photograph, report and platform screenshots.

**In the portal.** The provider portal is an Operate surface: providers scan client rosters, intake profiles, plans and tickets. When a portal screen moves onto Clear Clinic it keeps the same face, palette, focus ring and shapes, but tightens the rhythm. Tables and lists come before panels, hairlines come before boxes, and there are no reveal animations. The brand shows up in precise details, not in big hero bands. Until a screen is migrated, its legacy styling is debt to remove, not a pattern to extend.

## Colors

A cool, low-chroma green-grey world with one saturated-enough sage to carry every action.

### Primary
- **Deep Sage** (`action`): every filled button, the featured plan card, the platform band, benefit tick discs, checklist and list icons, text links, active nav and legal TOC states. Chosen because white on it passes contrast where mid sage does not.
- **Deep Sage Hover / Press** (`action-hover`, `action-press`): progressively darker fills for hover and active on filled controls.

### Secondary
- **Brand Sage** (`sage`): the recognisable brand green. Used only as a tint source: `sage-soft` (14% alpha) for secondary-button hover, journey step numbers and success messages, and a 28% alpha for text selection. Never as a fill behind white text.
- **Focus Sage** (`ring`): the 3px focus outline and input focus halo.

### Neutral
- **Ink** (`ink`): headings, body and nav text.
- **Slate** (`ink-2`): ledes, supporting paragraphs, footer meta.
- **Muted Slate** (`ink-3`): small labels, placeholders, the footer disclaimer.
- **White** (`bg`): page background, plan cards, inputs, chips.
- **Mist Canvas** (`canvas`): alternating full-bleed sections, contact form panel, footer.
- **Pale Sage Panel** (`panel`) / **Deeper Panel** (`panel-strong`): benefit panels, framed media, TLDR and callout cards, journey hover, contact badges.
- **Hairline** (`line`) / **Strong Hairline** (`line-strong`): dividers and card borders; input and toggle borders.

### Feedback
- **Success Ink** (`success-ink`) on `sage-soft`; **Error Ink** (`error-ink`) on `error-soft`: form response messages only.
- **Featured Tick** (`featured-tick`): icon colour inside the featured (filled) plan card.

### Named Rules
**The Deep Sage Rule.** Any control with white text sits on `action` (or darker). Mid `sage` behind white text is 3.27:1 and is never used as a fill.

**The One Action Colour Rule.** Sage is the only hue on the page besides neutrals and the photography. Don't introduce a second accent for emphasis; use weight, size or a filled sage panel instead. Status colour is the only exception: error red in form messages and the amber alert icon (#7d4e06) in legal callouts.

**The Retired Mauve Rule.** Mauve (#a8879d) is legacy. Login, register, demo and portal CTAs move to Deep Sage (`action`). White on mauve is about 3.2:1, and it was never part of the system.

### Legacy palette (portal, demo, auth): do not extend
Hard-coded in `dashboard/`, `demo/`, `components/` and `core/static/core/login/`. Each value maps to the Clear Clinic token that replaces it when its screen is migrated:

| Legacy value | Where | Replace with |
|---|---|---|
| Brand Sage #67997d as a fill behind white text | `#info-block` banners, active day tabs, sidebar active icon, feedback buttons, demo landing | `action` (fails AA as-is: 3.27:1) |
| Gradient #8db299 → #67997d | plans header | flat `action` or `panel` |
| Mauve #a8879d / #9b7a91 | login/register CTA, demo next/links, pill generator | `action` / `action-hover` |
| Tailwind blue #3b82f6 / #2563eb | clients `.btn-primary`, input focus | `action` / `action-hover`; focus `ring` |
| Grey #6b7280, red #ef4444 | `.btn-secondary`, `.btn-danger` | secondary button; `error-ink` |
| Browns #8d6e63, #a08068, #8b6f5b, dusty blue #88a9c3 | plans focus headers, exercise/meal themes | `panel` / `panel-strong` with `ink` text |
| Orange #ea580c, cyan #0891b2, red #dc2626 | plan-tier badges | one neutral chip style; the tier is shown by its label |
| #dcfce7 / #166534, #fef3c7 / #92400e | status badges, success message | `sage-soft` / `success-ink`; amber pair only for pending |
| Greys #333, #666, #374151, #1e293b, #111827 | text | `ink`, `ink-2`, `ink-3` |
| #f8f9fa, #f8fafc, #ebe9ea, #e0e0e0, #eee, #e2e8f0 | backgrounds, borders | `canvas`, `panel`, `line`, `line-strong` |
| Gradients #667eea → #764ba2, #ff6b6b → #ee5a52 | profile page | remove |

## Typography

**Display Font:** Figtree variable (300–900), self-hosted woff2, `font-display: swap`, with system-ui / -apple-system / Segoe UI fallback.
**Body Font:** the same family.

**Character:** a friendly geometric-humanist sans used at confident sizes with tight tracking; the variable axis carries intermediate weights (550, 650) that give headings presence without heaviness.

### Hierarchy
- **Display** (650, fluid 40→60px, 1.02, −0.035em): the hero H1 only, capped at ~15ch.
- **Headline** (650, fluid 32→48px, 1.08, −0.028em): section H2s, contact title, platform band, legal page titles.
- **Title** (650, 19–26px, 1.15–1.3, −0.01 to −0.02em): journey steps (1.1875rem), plan names (1.625rem), legal section headings (1.5rem), TLDR cards (1.125rem).
- **Benefit statement** (550, fluid 19→23px, 1.3, −0.015em): the three home benefit panels.
- **Lede** (400, fluid 18→21px, 1.5, `ink-2`): one-line or short-paragraph intros under headings, measure 46–62ch.
- **Body** (400, 17px, 1.6; legal 1.7): running copy, measure ≤60–72ch.
- **Label** (600, 15px): form labels, "Plan includes", contact list headings, legal sidebar heading. Sentence case.
- **Micro** (400, 13px, 1.65, `ink-3`): footer disclaimer only.

### Named Rules
**The Negative Tracking Rule.** Tracking tightens as size grows: −0.035em display, −0.028em headline, −0.01 to −0.02em titles, 0 for body. Headings use `text-wrap: balance`, paragraphs `pretty`.

**The Sentence Case Rule.** No uppercase labels or letter-spaced small caps; hierarchy comes from size and weight.

### Portal scale (provisional)
Not built yet. This is guidance for portal screens as they migrate, using existing tokens: body and table cells at `--fs-small` (15px, 400, 1.5); column headers, field labels and metadata at `--fs-micro` (13px, 600, sentence case); page titles at `--fs-h3` (1.375rem, 650, −0.015em). Display, headline and lede sizes stay on the public pages. Use tabular figures (`font-variant-numeric: tabular-nums`) for dates, counts and biomarker values.

**Legacy:** portal, demo and auth pages render in Open Sans (loaded in `templates/base.html`), with 100-weight page titles, keyword sizes (`larger`, `xx-large`) and `vh`-based type. The clients table header is uppercase with 0.05em tracking, which breaks the Sentence Case Rule.

## Layout

- **Container:** content max 1200px plus a fluid gutter (`clamp(20px, 4vw, 48px)`) each side.
- **Vertical rhythm:** sections pad `clamp(72px, 9vw, 128px)` top and bottom; consecutive same-tone sections collapse the shared padding. Tone alternates white / Mist Canvas full-bleed bands to separate chapters without lines.
- **Hero:** two columns ~1.05fr / 0.95fr, copy left and the kit photograph right (5:4), collapsing to one column at 860px (image 4:3).
- **Split rows:** equal two-column copy/media, or a media-wide 1.25fr / 0.75fr variant; a `reverse` modifier puts media first. One column below 860px.
- **Grids:** benefits 3-up (gap 20px) → 1-up at 860px; checklist 3-up → 2-up at 960px → 1-up at 600px; plans 2-up → 1-up at 760px; legal pages 260px sticky TOC + content (≤72ch) → single column at 900px with a horizontally scrolling pill TOC.
- **Breakpoints in use:** 960px, 900px (legal), 860px (main), 760px, 600px.
- **Header:** sticky, 76px desktop / 64px mobile; `scroll-padding-top: 88px` for anchors.

**Portal density (provisional):** table and list rows at least 44px tall with 12–16px cell padding, divided by `line` hairlines; page gutter 24–32px; section spacing 32–48px rather than the public `--section` step. Wide tables scroll horizontally inside their container instead of collapsing below 768px.

**Legacy portal shell:** a 100px header, a fixed left icon sidebar with content offset 120px, and content in a `#f8f9fa` 15px-radius `inner_content` well. Each page opens with a filled-sage `#info-block` banner holding a cartoon illustration. Breakpoints are ad hoc (1200, 1000, 900, 768, 480px), and the demo sizes type and buttons in `vh`/`vw`.

## Elevation & Depth

Hybrid, mostly tonal. Surfaces separate by stepping white → `canvas` → `panel`, and by 1px hairlines. A single soft two-layer ambient shadow lifts photography and screenshots (hero image, framed screenshots). The sticky header uses translucency plus backdrop blur, and gains a hairline only after scrolling. The open mobile menu carries its own drop shadow.

### Shadow Vocabulary
- **Media lift** (`box-shadow: 0 1px 2px rgba(15, 23, 32, 0.05), 0 12px 32px rgba(15, 23, 32, 0.07)`): hero photograph and screenshots inside framed panels.
- **Menu drop** (`box-shadow: 0 16px 32px rgba(15, 23, 32, 0.08)`): mobile navigation sheet only.

### Named Rules
**The Shadows Lift Pictures Rule.** Shadows belong to images and the floating mobile menu. Panels, cards, buttons and chips stay flat and separate by tone or hairline.

**Legacy:** portal cards, tables and buttons use about a dozen ad hoc black-alpha shadows (most often `0 2px 8px rgba(0, 0, 0, 0.1)`) plus a hover lift on buttons. Migrated screens drop all of them. The one exception is a modal, which may take Menu drop over a `rgba(15, 23, 32, 0.4)` scrim.

## Shapes

Soft, rounded, never sharp. Large containers (benefit panels, plan cards, framed media, hero photo, contact form, TLDR cards) use 24px; nested frames, journey rows and legal callouts use 16px; inputs, the menu toggle, skip link and form messages use 10px. Buttons, tick discs, step numbers, contact badges and molecule chips are full pills/circles. The platform band takes a larger fluid radius (`clamp(20px, 3vw, 36px)`). Borders are 1px hairlines; the secondary button uses a 1.5px sage outline. Icons are 24-grid stroked line icons (2px stroke, round caps and joins) at 18–20px.

Legacy surfaces use 15px for nearly everything, plus 8, 12, 16, 20, 25, 80 and 100px, `0.5rem`/`0.75rem` and a 40% blob. On migration, snap them to the scale: inputs and badges 10px, rows and nested frames 16px, cards and modals 24px, controls full pill.

## Components

### Buttons
Confident, rounded and quiet.
- **Shape:** full pill (`rounded.full`), 52px tall (42px small in the header), 600-weight 1rem label, 8px gap for a trailing arrow icon.
- **Primary:** Deep Sage fill, white text. Hover darkens to `action-hover`, active to `action-press` and nudges down 1px. A trailing arrow icon slides 2px up-right on hover.
- **Secondary:** transparent with a 1.5px 45%-alpha sage outline and Deep Sage text; hover firms the outline and adds the `sage-soft` wash.
- **Light:** white fill, Deep Sage text, used only on the Deep Sage platform band; hover goes to `panel`.
- **Text link:** Deep Sage 600-weight with trailing arrow, underline on hover.
- **Transitions:** 160ms on `--ease-out` (`cubic-bezier(0.16, 1, 0.3, 1)`).

### Chips
- **Molecule chip:** white pill with hairline border, 600-weight 1.125rem, leading sage check-circle icon. Static (not interactive).

### Cards / Containers
- **Benefit panel:** Pale Sage, 24px radius, 26–28px padding, a 36px Deep Sage tick disc above a benefit statement.
- **Plan card:** white, hairline border, 24px radius, fluid 28–40px padding; the **featured** variant is filled Deep Sage with white text and `featured-tick` icons.
- **Framed media:** Pale Sage 24px panel with 16–28px padding holding a 16px-radius screenshot carrying Media lift.
- **Legal TLDR / callout:** Pale Sage, 24px / 16px radius, no border.

### Inputs / Fields
- **Style:** white, 1px `line-strong` border, 10px radius, 13px × 14px padding, 1rem/1.5 text, `ink-3` placeholder, label above at 600/15px.
- **Hover:** border darkens to 32% ink.
- **Focus:** border turns Deep Sage plus a 3px `ring` halo; no outline.
- **Busy:** submit button at 60% opacity with progress cursor while the htmx request runs.

### Navigation
- **Header:** OMIVER green wordmark left (148px; 124px mobile); right-aligned links at 500/1rem ink, hover and `aria-current` in Deep Sage; the last item is a small primary button.
- **Mobile (≤860px):** 44px bordered menu toggle; a full-width white sheet drops below the bar with hairline-separated 1.0625rem links and the button at the bottom; closes on Escape or link click.
- **Footer:** Mist Canvas, wordmark and links on top, hairline, 13px disclaimer, then copyright and legal links in `ink-2`.

### Journey List (signature)
A numbered five-step list on the information page. Each row is a 44px number disc (`sage-soft` with Deep Sage numeral, tabular figures) beside a title and `ink-2` description. Hover or focus-within washes the row with Pale Sage (16px radius) and fills the disc Deep Sage with a white numeral, over 200ms.

### Checklist
A 3-column grid of 500-weight 1.125rem statements with sage check-circle icons, divided by top and bottom hairlines instead of boxes.

### Platform Band
A full-width Deep Sage rounded band with centred white headline, 86%-white lede, a Light button, and the device screenshot bleeding off the bottom edge.

### Reveal Motion
Sections marked for reveal fade up 18px from 4px blur over 700ms on `--ease-out`, staggered 70ms per item. Content is visible by default; the script only hides elements below the fold once it can animate them. Reduced motion disables reveal, smooth scroll and transitions.

### Portal Components (legacy inventory)
Everything here is hard-coded and off-system. When you touch one, migrate it as noted; don't copy it to a new screen.

- **Page banner** (`#info-block`, on every dashboard page): Brand Sage fill, white text, 15px radius, cartoon illustration. → A plain page title and `ink-2` description on the page background. No illustration (this follows the real-assets rule).
- **Clients table** (`.clients-table`): white container with a shadow, uppercase grey headers, slate hover rows. → Hairline-bordered 16px container, no shadow, sentence-case 13px/600 `ink-2` headers on `canvas`, `line` row dividers, `canvas` row hover, 44px minimum rows.
- **Buttons** (`.btn-primary` blue, `.btn-secondary` grey, `.btn-danger` red, 8px radius, hover lift; `.feedback-btn` sage; `.action-button` mauve; `.pill-generator-button` mauve): → the Clear Clinic primary / secondary / small buttons. A destructive action is a secondary button in `error-ink`, never a filled red.
- **Plan and status badges** (`.plan-badge` orange/cyan/red filled pills; `.status-badge` green/amber tints): → one 10px-radius chip with a text label; active on `sage-soft` / `success-ink`, pending on an amber tint with #7d4e06 text, tiers neutral on `panel`.
- **Form fields** (`.form-group`): grey border, 8px radius, blue focus halo. → The Clear Clinic input-field spec.
- **Day tabs** (`.day-tab`, plans): rounded-top tabs with a Brand Sage active fill. → A text tab with a 2px `action` underline and `ink` active label.
- **Plans grid** (`.training-grid`): brown and dusty-blue header cells. → `panel` header cells with `ink` text; tell exercise and meal apart by label and icon, not hue.
- **Support tickets** (`.ticket-preview`, `#reply-input`): previews in bordered blocks, a pill reply field with a black-bordered send button. → A hairline-divided list with `canvas` hover; the input-field spec and a small primary button.
- **Shared components:** `ibutton` (40px circular icon button, #fbfbfc), `setting_item` (row with a grey icon tile and an #e0e0e0 divider), `custom_slider` (#608479 thumb, red error state), `demo_modal` (#ebe9ea body, 12px radius, black 50% scrim). → `canvas` icon buttons with the `ring` focus; `line` dividers; an `action` thumb and `error-ink` error; a 24px white modal with Menu drop over the ink scrim.
- **Demo and auth layout** (`two_column_layout`): a half-screen darkened photo with an 80px radius beside a white panel; 60px mauve next button; 2px black back button. → Carry over the public site's split-row and button language.
- **Third-party:** `profile.html` loads the Tailwind CDN at runtime and Flickity 1.0 from cdnjs. Remove them when that screen is migrated.

## Do's and Don'ts

### Do:
- **Do** put every filled control on Deep Sage (`action`) with white text, darkening to `action-hover` / `action-press` on hover and active.
- **Do** separate chapters with white / Mist Canvas bands and the fluid section step (`clamp(72px, 9vw, 128px)`) rather than rules or boxes.
- **Do** group related items in 24px Pale Sage panels, or as hairline-divided lists.
- **Do** use real Omiver photography and screenshots, rounded (24px hero, 16px inside frames) with the Media lift shadow.
- **Do** keep headings in Figtree 650 with negative tracking, and keep ledes in `ink-2` at 46–62ch.
- **Do** give every interactive element the 3px `ring` focus outline, and keep reveal motion opt-in and disabled under reduced motion.
- **Do** build new or refactored portal, demo and auth screens on the `:root` tokens in `core/static/core/site.css` and Figtree, at the portal scale and density.
- **Do** use the legacy palette table to map old values when you touch a legacy screen, and migrate the whole screen, not one component.

### Don't:
- **Don't** use mid `sage` as a fill behind white text (3.27:1).
- **Don't** add a second accent hue for emphasis; outside status messages and the legal alert icon, the page is neutrals, sage and photography.
- **Don't** put shadows on panels, cards, buttons or chips; depth comes from tone and hairlines.
- **Don't** use uppercase, letter-spaced labels or small eyebrow text above headings.
- **Don't** use stock or illustrated imagery in place of real product assets.
- **Don't** use pure black text or a second typeface.
- **Don't** copy any legacy portal value (Open Sans, mauve, Tailwind blue, browns, gradients, ad hoc shadows, 15px radii) into new work.
- **Don't** colour-code plan tiers or record types with extra hues; label them.
