# P0 experiment notes

Body model and preset results for Stylewise. Every number below can be regenerated from the scripts named next to it. Gallery of all presets: https://claude.ai/artifact/T8HGZop52zu7CC32ZsWbS5

## Summary

- **MHR works as the body model.** From height plus three girths, the inverse fit reaches a mean girth error of 0.40 cm on synthetic bodies (B-A, n=3).
- **210 preset bodies** (2 sexes × 5 silhouettes × XS–3XL × 3 heights) were fitted on NSCC ASPIRE 2A. **All 210 land inside their stated ± range and keep their FFIT shape class.** Mean girth error is 0.15 cm.
- Sizes come from **real data**: ANSUR II, split into sizes with the ISO 8559-3 approach. The earlier synthetic chart is gone.
- **Oval is the hardest shape.** It has a consistent bias (chest too big, waist too small), and one body needed a warm-start re-fit.
- **Two open issues** affect what the girth numbers mean: (1) the chest landmark sits at the edge of its search band on 202/210 bodies; (2) the female presets look anatomically male. Both are explained under *Open issues*.

## 1. MHR setup

MHR (facebookresearch/MHR; Apache-2.0 code and assets), TorchScript `mhr_model.pt`, LOD 1, 18,439 vertices, run on CPU. The rest pose is an A-pose, Y-up, in cm (converted to m for our GLB contract). One body takes 0.24 s to generate.

- The 45 identity coeffs do not change stature (the neutral body is always 172.7 cm). Height is matched with a uniform global scale. This is a simplification: it also scales girths, and the optimizer compensates with the shape coeffs.
- **Measurement operator** (`stylewise_fit.measure.landmark_circumferences`): a horizontal slice, keeping only the loops centred near x=0 (which drops the arms), then the convex-hull perimeter, like a tape measure. Landmarks are found by search: chest = max girth at 69–74% of stature, waist = min at 56–69%, hip = max at 46–56%.
- **Optimizer:** `scipy.least_squares` over the first 20 identity coeffs, with an L2 prior toward MHR's mean body. SciPy's built-in Jacobian returned zero at coeffs = 0 (the run stopped after 1 eval), so we use explicit forward differences with a 0.05 step.
- The bottleneck is mesh slicing (~0.23 s per body), not the model. A GPU barely helps; parallel CPU workers do.

## 2. B-A: inverse fit from 4 measurements

`experiments/mhr_ba.py` → `results/mhr_ba.csv`, seed 0. Three random reference bodies (20 coeffs ~ N(0, 0.7), height 155–185 cm), each re-fitted from height + chest + waist + hip. Prior weight 2.0, 15-step cap.

| body | height cm | chest target / err | waist target / err | hip target / err | time |
|---|---|---|---|---|---|
| 0 | 155.9 | 99.4 / −0.47 | 85.2 / +0.27 | 98.4 / +0.22 | 35 s |
| 1 | 164.7 | 115.2 / +0.47 | 104.5 / −0.65 | 113.4 / −0.08 | 72 s |
| 2 | 157.7 | 111.6 / −0.73 | 95.2 / +0.54 | 112.5 / −0.15 | 68 s |

Mean abs girth error **0.40 cm**, worst **0.73 cm**. Caveats: n=3; every run hit the step cap; the references come from the same model and operator, so this tests the fitting procedure, not real anthropometry; four numbers do not uniquely determine a body.

## 3. Size chart: ANSUR II with the ISO 8559-3 approach

`scripts/ansur_sizes.py` → `stylewise_fit/data/size_chart_ansur2.json` (raw CSVs are checksummed in the JSON).

- **Data:** ANSUR II public release (US Army 2012, public domain), 1,986 women and 4,082 men. Columns used: chest circumference, waist circumference, buttock circumference (= hip) and stature.
- **Method** (our reading of ISO 8559-2/-3; the standard text is not reproduced): chest is the primary dimension for tops. The central 90% (P5–P95) is split into 5 equal intervals, XS–XL. 2XL and 3XL continue the same interval width above P95, so larger bodies are not dropped (they add 92 women and 196 men).
- The ± range on preset girths is half an interval: **±2.7 cm** (women) and **±2.85 cm** (men).

| Chest/bust cm | XS | S | M | L | XL | 2XL | 3XL |
|---|---|---|---|---|---|---|---|
| Women | 85.1 | 90.5 | 95.9 | 101.3 | 106.7 | 112.1 | 117.5 |
| Men | 95.1 | 100.8 | 106.4 | 112.2 | 117.8 | 123.6 | 129.2 |

**Shape mix in ANSUR II** (FFIT classification):

| | rectangle | triangle | oval | inverted triangle | hourglass | other |
|---|---|---|---|---|---|---|
| Women (n=1,986) | 54% | 31% | 5% | 0.5% | 0.2% | 10% |
| Men (n=4,082) | 73% | 0.2% | 12% | 13% | 0% | 1% |

All five silhouettes are offered to both sexes for inclusivity. Women's prototypes are hand-placed inside each FFIT class. Men's rectangle, inverted triangle and oval prototypes are the ANSUR II medians of men in that class; men's hourglass and triangle are hand-placed, because ANSUR II has almost no such men.

Limitation: ANSUR II is a US military sample, fitter and younger than the general public. Demographic-specific charts can be added as further entries in the chart file.

## 4. Preset generation

`scripts/gen_presets.py`, run on NSCC ASPIRE 2A (PBS, 32 cores, `cluster/nscc_presets.pbs`). Prior weight 0.2, 25-step cap, ~110 s per body on one core, ~15 min wall time for 210 bodies.

**Choosing the prior weight** (`experiments/prior_sweep.py`, size M, 165 cm, old chart). At prior 2.0, hourglass and oval drifted to rectangle, because the prior pulls toward MHR's mean body:

| shape | prior | chest err | waist err | hip err | class |
|---|---|---|---|---|---|
| hourglass | 0.5 | −0.38 | +0.32 | +0.07 | hourglass |
| hourglass | 0.2 | −0.07 | +0.06 | +0.01 | hourglass |
| hourglass | 0.05 | 0.00 | 0.00 | 0.00 | hourglass |
| oval | 0.5 | +1.51 | −2.04 | +0.43 | oval |
| oval | 0.2 | +1.25 | −1.73 | +0.68 | oval |
| oval | 0.05 | +1.20 | −1.72 | +0.68 | oval |

We use **0.2**. A weaker prior gains little and risks implausible bodies.

**Acceptance rule.** A preset is accepted when its fitted girths keep the target's FFIT class and every girth error is within the ± range we report to the user. Rejected presets get a second pass, warm-started from the nearest accepted preset of the same sex and shape (`warm_start` in `index.json`).

## 5. Preset results (210 bodies)

`fixtures/presets/index.json`, renders in `fixtures/presets/renders/` (`scripts/render_presets.py`).

| | n | mean abs err cm | worst cm | all girths ≤1 cm | accepted |
|---|---|---|---|---|---|
| Women | 105 | 0.19 | 1.84 | 85% | 105/105 |
| Men | 105 | 0.11 | 1.13 | 98% | 105/105 |

By shape:

| shape | women mean / worst cm | men mean / worst cm |
|---|---|---|
| hourglass | 0.04 / 0.08 | 0.03 / 0.06 |
| triangle | 0.03 / 0.05 | 0.05 / 0.09 |
| inverted triangle | 0.03 / 0.07 | 0.01 / 0.05 |
| rectangle | 0.00 / 0.01 | 0.01 / 0.03 |
| **oval** | **0.84 / 1.84** | **0.43 / 1.13** |

Size (XS–3XL) and height have no systematic effect on error.

**Oval.** Signed mean error, women: chest +0.8, waist −1.2, hip +0.5 cm; men: +0.2, −0.6, +0.4 cm. With 20 shape coeffs, MHR cannot make the waist as large as the chest without also growing the chest, so the fit trades one off against the other. All ovals are still inside the ± range.

**The one stalled fit.** `female_oval_XS_175` (tall, smallest bust, round waist) first fitted to +3.7 / −4.6 / +2.5 cm and was classified as rectangle. Re-fitting from its own result with 3× the steps and a weaker prior did not help: it is a local minimum, not a step budget problem. **Warm-starting from `female_oval_XS_165` fixed it: +0.8 / −1.5 / +1.2 cm, oval, in 22 s.** The generator now does this automatically.

## 6. Open issues

**1. Landmarks sit at the edges of their search bands.** `results/preset_landmark_heights.json` stores each landmark's height as a fraction of stature:

| landmark | band | at the band's top edge |
|---|---|---|
| chest | 69–74% | **202 / 210** |
| waist | 56–69% | 72 / 210 |
| hip | 46–56% | 44 / 210 |

Girth on MHR keeps increasing toward the armpit, so "max girth in 69–74%" returns the 74% cap (set to keep the arms out), not the bust point that ISO 8559-1 defines. On 9 large ovals, the waist and hip slices also collapse onto the same height (gap < 2% of stature). The fitted numbers match their targets, but they are measured at partly arbitrary heights. **Fix:** anchor the landmarks to MHR's skeleton or fixed mesh vertices (bust point, natural waist, buttock) instead of band search, then regenerate. This changes all presets, so it is a deliberate next step, not a patch.

**2. Female presets looked anatomically male (fixed in code, cluster rerun pending).** MHR has no sex parameter: identity is 45 PCA coeffs with no semantic axes (MHR paper, arXiv 2511.15586). Matching three girths left the shoulders as broad as the mean body's.
- **Cue chosen from data.** In ANSUR II, the strongest female/male separators among available measurements are biacromial ÷ hip breadth (F 1.037, M 1.204; 2.2 SD apart) and chest depth ÷ chest girth (2.1 SD). The neutral MHR body already has a female-range bust depth (0.257), so shoulder-to-hip width was the missing cue.
- **Measured on the mesh** as the shoulder-joint distance (joints 39/75) ÷ hip breadth (arm-free slice at the buttock vertex). The neutral ratio is 0.913.
- **Calibration assumption:** MHR's mean body is taken as the midpoint of the ANSUR female and male ratios. That maps mesh 0.913 → 1.12 and gives mesh targets **F 0.846, M 0.983** (`SHOULDER_HIP_TARGET` in `mhr_body.py`).
- **Added as a fourth fit target** (weight: 0.01 of ratio = 1 cm of girth). Test fits: female hourglass M and rectangle M reach a ratio of 0.848–0.849 with girth errors ≤ 0.21 cm, and the silhouettes read as female (narrower shoulders, wider hips). `female_oval_3XL_165` reaches 0.85 and `male_oval_M_175` 0.98, both accepted.
- **First cluster run with a fixed target per sex: 207/210 accepted.** The 3 failures were women's inverted triangles (XS 165/175, S 175), fitted as rectangles with hip +3.4 to +6.5 cm. A fixed "wide hips" ratio contradicts a narrow-hipped shape.
- **Fix: shape-aware target.** `shoulder_hip_target = T_sex × (bust + typical hip−bust) / hip`, where the ANSUR II median hip − bust is +7.7 cm (F) and −3.7 cm (M). Since hip breadth scales with hip girth, this holds the **absolute shoulder width** at the sex-typical value and lets the ratio follow the shape's own hips (women M: triangle 0.81, rectangle 0.90, hourglass 0.90, oval 0.94, inverted triangle 1.05). The 3 failed presets then fit within 0.42 cm and keep their class.
- Alternatives considered and not used: an LDA "sex direction" over MHR coeffs (needs sex-labelled scans), SOMA/Anny mapping, and SMPL→MHR registration (both add a second body model).

**3. Height uses a global scale.** A 155 cm preset is a scaled-down 172.7 cm body, not a shorter-proportioned one. **Fix to test:** fit MHR's per-bone scale parameters for stature.

## 7. Caveats for the write-up

- Preset girths are estimates from silhouette + usual size, never measurements. The engine reports them with a ± range and a `borderline` verdict.
- ANSUR II is a military sample, and the FFIT shape thresholds were developed on women.
- B-A uses synthetic references from MHR itself; no real-scan validation has been done yet.
