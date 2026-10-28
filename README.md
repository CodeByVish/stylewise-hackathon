# Stylewise Fit Lab

**Know what works with your wardrobe before you buy.** Stylewise is a fit-aware shopping and virtual closet prototype for the Meta hackathon, October 28-November 4, 2026.

## Product goal

Help someone decide whether to investigate buying a garment by comparing documented garment measurements with user-provided measurements and preferences, checking their existing wardrobe, and showing an approximate 3D outfit. Recommendations are conditional, explain their evidence, and are not guarantees of physical fit.

The purchase decision simulator compares:

- Buy size S.
- Buy size M.
- Skip the purchase and build a similar outfit from the user's wardrobe.

## Prototype scope

- One garment category with two size variants and known, sourced measurements.
- Optional height, chest, waist, and hip inputs; a fitted Meta MHR body is an experiment, with a controlled mannequin fallback.
- A garment photo mask and structured attributes, while keeping pixel segmentation separate from garment dimensions and fabric properties.
- Deterministic ease, clearance, and unknown-evidence checks, plus one supported pose or closure preference.
- Wardrobe-aware outfit suggestions, a multi-view 3D viewer, and Nisha responses in text and voice where available.
- Fixture meshes and JSON so body/fit and garment/viewer work can proceed independently.

Out of scope: arbitrary-garment fit guarantees, full cloth physics, Quest support, and disability comfort claims. If evidence is missing, show the uncertainty instead of filling it in.

## Technical direction

- Frontend: Next.js App Router, React, TypeScript, and Tailwind CSS.
- Garment understanding: Meta SAM 3.1 for image segmentation; Muse Spark / Open for structured attributes and tool reasoning, subject to access.
- Body: Meta MHR research, with a parametric mannequin fallback.
- Garment geometry: legally usable GarmentCode/Blender assets or prepared meshes with measurement provenance.
- Fit: deterministic Python geometry and measurement comparisons; never let a language model invent physical measurements.
- Viewer: Three.js, using the same body and garment meshes for front, side, and back views.

## Working contracts

Keep the shared request/result contract stable from the start. A fit request carries user measurements in centimeters, pose or preference, garment size-chart values, mesh references, and provenance. A fit report carries computed ease, supported checks, warnings, unknowns, and evidence-backed advice. Mesh references should identify the asset and its source; fixture assets remain valid inputs while either engine is in progress.

Ease differences are arithmetic, not proof of comfort. For example, a 90 cm chest and a documented 98 cm garment chest gives +8 cm chest ease; it does not establish that the garment will feel comfortable.

## Team workstreams

- **P0: body and fit intelligence.** Measurement-to-body experiments, deterministic fit calculations, uncertainty, API/CLI, Muse tool semantics, and Nisha integration.
- **P1: garment and try-on.** Segmentation, sourced size variants, garment meshes, pose experiments, viewer, and Fit Lab UI.
- **Shared:** freeze the JSON/GLB contract, integrate on October 31 and November 2, rehearse November 3, and submit on November 4.

Neither workstream should block on the other: P0 runs against synthetic garment specs, and P1 runs against fixture bodies and fit JSON.

## Milestones

| Date | Gate |
| --- | --- |
| Oct 28 | Freeze JSON/GLB contract; independent body and rotating-viewer baselines run. |
| Oct 29-30 | Measure mesh accuracy, compare sizes/views, and decide MHR/mannequin and drape/static-shell fallbacks. |
| Oct 31 | First integrated measurements-to-avatar-to-garment result. |
| Nov 1 | One supported preference changes an evidence-backed recommendation. |
| Nov 2 | Second integration; evaluate at least 12 controlled fit cases and two sizes across three views. |
| Nov 3 | Freeze implementation, methods, limitations, docs, and demo; clean-run rehearsal. |
| Nov 4 | Verify provenance, privacy, eligibility, demo links, and submission deadline; submit early. |

## Getting started

Requirements: Node.js and npm.

```bash
npm install
npm run dev
```

Open http://localhost:3000. Useful checks: `npm run lint` and `npm run build`.

## Hackathon eligibility and provenance

This folder is a fresh starter. A pre-existing Stylewise project is also present on this desktop, and the event rules described by the team may distinguish new contributions from reused work. Confirm the applicable rules with organizers in writing before copying code or assets into this repo. Track what is built during the event, record model versions and asset sources, and disclose prior work as required by the submission rules.
This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
