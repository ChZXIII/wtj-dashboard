---
name: ui-ux-design
description: |
  Comprehensive UI/UX design director guidelines, including heuristic evaluation, visual hierarchy, spacing, typography, accessibility (WCAG), and theme integration. Use this skill when evaluating, designing, or implementing web interfaces to ensure premium aesthetics and optimal user experience.
---

# UI/UX & Aesthetic Design Guidelines

This skill provides a structured framework for evaluating and designing modern, premium web interfaces. It defines principles for visual design, layout structure, interaction feedback, accessibility, and theme management.

## 1. Core UX Foundations & Heuristics

### Nielsen's Usability Heuristics
- **Visibility of System Status**: Always keep users informed about what is happening (e.g., loading spinners, progress bars, active status indicators, and transaction logs).
- **Match Between System and Real World**: Use familiar terminology, logical layouts, and standard iconography.
- **User Control and Freedom**: Provide clear "Undo", "Cancel", and "Close" mechanisms (e.g., in modals or wizard flows).
- **Consistency and Standards**: Follow established UI design patterns. Maintain uniform styles across all pages and modules.
- **Error Prevention and Recovery**: Help users avoid mistakes (e.g., disabling invalid buttons, auto-validating fields) and provide clear, helpful error messages with recovery paths.
- **Flexibility and Efficiency of Use**: Offer keyboard shortcuts, action cards, and advanced telemetry modes for experienced users.
- **Aesthetic and Minimalist Design**: Avoid clutter. Expose essential information first, then use progressive disclosure (accordion cards, details tabs) for deeper insights.

---

## 2. UI Layout & Density Guidelines

### Spacing and Grid Systems
- **Base Grid**: Use a strict 4px/8px spacing system for all padding, margins, gaps, and heights. Never use arbitrary pixel sizes.
- **Layout Density**:
  - *Cockpit UI / Telemetry*: High density, sharp lines, compact margins, font size 12-14px for telemetry.
  - *Standard Web/Content*: Moderate density, generous white space (24px+ gaps), larger titles (32px+).

### Visual Hierarchy
- **Typography Contrast**: Contrast sizes (`h1`, `h2`, `body`, `caption`) and font weights (700 bold vs 400 regular) clearly. Use distinct font families (e.g., `Orbitron` for futuristic headers, `Share Tech Mono` for logs/numbers, and `Inter` for general content).
- **Action Hierarchy**:
  - *Primary Actions*: Strong visual weight (solid border, filled color, or high contrast text).
  - *Secondary Actions*: Muted background, outline borders, lower contrast.
  - *Tertiary Actions*: Clean text-only buttons with hover highlights.

---

## 3. Theme Integration and Token Systems
To avoid hardcoded styles, always design with CSS custom properties (variables) that adapt to themes:

| Element | Ptolemy Light Mode | Veda Flat Dark Mode | Veda Neon Dark (Color Mode) |
| :--- | :--- | :--- | :--- |
| **Background** | Clean, gray-white (`#f3f4f1`) | Deep matte navy (`#13141d`) | Space black (`#05070a`) |
| **Borders** | Solid black/dark gray (`#111111`) | Crisp white-gray (`#e5e5e5`) | Neon cyan/green (`#00f0ff` / `#00e676`) |
| **Shadows & Glows** | Solid offset shadow, no glow | Flat dark offset shadow | Glowing box-shadows, glow filters |
| **Text Primary** | Dark charcoal (`#111111`) | Light gray (`#e5e5e5`) | Radiant neon cyber cyan (`#00f0ff`) |

---

## 4. Accessibility (WCAG 2.1 AA Checklist)
All interfaces must adhere to basic accessibility standards:
- **Color Contrast**: Text-to-background contrast ratio must be at least 4.5:1 for body text, and 3.0:1 for large headings.
- **Interactive Elements**: Every interactive control (buttons, links, inputs) must have a visible focus outline.
- **Semantic HTML**: Use proper tags (`<header>`, `<main>`, `<section>`, `<nav>`, `<article>`, `<button>`) instead of generic nested `<div>` tags.
- **Touch Targets**: Mobile interactive targets must be at least 44x44 pixels.

---

## 5. Interaction & Micro-animations
- **Active State Feedback**: Buttons and tabs must transition smoothly (`transition: all 0.2s ease-out`).
- **Hover indicators**: Implement visual feedback on hover (e.g., side border reveals, text color shift, background fill animations).
- **Transitions**: Use CSS transitions or View Transitions API for state changes. Avoid jerky animations or heavy JS libraries.
