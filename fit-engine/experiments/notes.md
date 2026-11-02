# P0 experiment notes

Body model and preset results for Stylewise. Every number below can be regenerated from the scripts named next to it.

## Summary

- **MHR works as the body model.** From height plus three girths, the inverse fit reaches a mean girth error of 0.01 cm (worst 0.04 cm) and 0.8 mm mean surface distance on 50 synthetic bodies (B-A). Single-girth edits stay local (B-B).
- **210 preset bodies** (2 sexes × 5 silhouettes × XS–3XL × 3 heights) were fitted on NSCC ASPIRE 2A. **All 210 land inside their stated ± range and keep their FFIT shape class**; mean girth error 0.15 cm. Girths are measured at ISO 8559-1-style landmarks, and women's presets have female proportions.
- Sizes come from **real data**: ANSUR II, split into sizes with the ISO 8559-3 approach.
- The fit engine handles **fabric**: stretch, elastic waists and bulky fabrics (section 7).
- **21 catalogue garments** can be fitted, alone or as outfits. 14 have chart- or product-sourced cm and 7 are estimated and flagged (section 8).
- A **fit-shell view** shows each garment on any preset body from three angles, with the verdicts drawn on (section 9).
- **Oval is the hardest shape** (women: mean 0.59 cm, worst 1.63 cm), a limit of MHR's 20 body coeffs.

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

**B-A at n = 50 (NSCC, final settings: ISO-style landmarks, prior 0.2, 25 steps)** → `results/mhr_ba_n50.csv`, `cluster/nscc_ba.pbs`. 50 random bodies (20 coeffs ~ N(0, 0.7), height 155–185 cm), each reproducible from (seed, index).

| | n = 3 (old landmarks, prior 2.0, 15 steps) | n = 50 (final) |
|---|---|---|
| mean abs girth error | 0.40 cm | **0.01 cm** |
| median / p95 / worst | – / – / 0.73 cm | 0.00 / 0.02 / **0.04 cm** |
| mean vertex distance to the reference body | – | **0.08 cm** (max 0.16) |
| time per body | 35–72 s | 79 s (1 core) |

Within MHR's own shape space, height + 3 girths recover the body almost exactly, not just its numbers. The vertex distance shows this. **Caveat:** the references come from the same model and the same measurement operator, and from the same prior distribution the fit assumes. This shows the procedure works; it is not validation against real people.

## 2b. B-B: editing one measurement

`experiments/mhr_bb.py` → `results/mhr_bb.csv`. Two base bodies (female rectangle M 165, male rectangle L 175). Each was fitted, then re-fitted warm-started with one girth +4 cm.

| body | edit | edited err cm | unedited girths, max change cm | shoulder/hip change | arms / legs / head mean mm | max vertex move mm |
|---|---|---|---|---|---|---|
| female M | waist +4 | −0.08 | 0.05 | 0.000 | 0.4 / 0.8 / 0.0 | 10.9 |
| female M | hip +4 | +0.03 | 0.02 | 0.001 | 0.5 / 1.4 / 0.0 | 14.4 |
| female M | chest +4 | −0.01 | 0.04 | 0.000 | 0.3 / 0.7 / 0.0 | 16.0 |
| male L | waist +4 | −0.02 | 0.03 | 0.000 | 0.2 / 0.6 / 0.0 | 10.3 |
| male L | hip +4 | −0.10 | 0.01 | 0.000 | 0.7 / 1.4 / 0.0 | 13.6 |
| male L | chest +4 | −0.04 | 0.03 | 0.000 | 0.4 / 0.8 / 0.0 | 12.2 |

**Edits are local.** The edited girth reaches its new target within 0.1 cm, and the unedited girths move by at most 0.05 cm. Unconstrained parts barely move: arms and legs by about 1 mm on average, the head by 0. A +4 cm girth change is ~6.4 mm of radius, so the 10–16 mm max displacement sits on the edited region. Caveat: n = 2 bodies × 3 edits.

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

## 5. Preset results (210 bodies, final run 2026-11-02)

`fixtures/presets/index.json`. Contact sheets: `scripts/render_presets.py --sheets-only`. This run uses ISO-style landmarks (bust-point and buttock vertices, arm faces excluded) and the shape-aware shoulder-to-hip sex cue. ~80 s per body; 32 cores.

| | n | mean abs err cm | worst cm | all girths ≤1 cm | accepted |
|---|---|---|---|---|---|
| Women | 105 | 0.18 | 1.63 | 94% | 105/105 |
| Men | 105 | 0.11 | 0.73 | 100% | 105/105 |

By shape (girth error mean / worst cm; shoulder-to-hip ratio error, worst):

| shape | women | men | ratio err (W / M) |
|---|---|---|---|
| hourglass | 0.09 / 0.57 | 0.07 / 0.21 | 0.008 / 0.005 |
| triangle | 0.12 / 0.51 | 0.17 / 0.62 | 0.011 / 0.006 |
| inverted triangle | 0.05 / 0.42 | 0.04 / 0.21 | 0.006 / 0.004 |
| rectangle | 0.07 / 0.46 | 0.06 / 0.23 | 0.009 / 0.004 |
| **oval** | **0.59 / 1.63** | **0.23 / 0.73** | 0.014 / 0.005 |

- **No re-fits were needed in the final run.**
- Oval improved from 0.84 to 0.59 cm mean for women, because the waist is no longer measured where it collapsed onto the hip.
- Oval is still the hardest shape. With 20 shape coeffs, MHR cannot make the waist as large as the chest without also growing the chest.
- Visually (contact sheets), the women's presets now read as female, and inverted triangles keep their broad shoulders.

**Earlier runs, for the record.**
- Run 1 (band-search landmarks, no sex cue): 209/210 accepted. `female_oval_XS_175` stalled at +3.7 / −4.6 / +2.5 cm and was fixed by warm-starting from `female_oval_XS_165` (+0.8 / −1.5 / +1.2 cm). The generator now does this automatically.
- Run 2 (fixed per-sex shoulder target): 207/210 accepted; see open issue 2 below.

## 6. Issues found and fixed

**1. Landmarks sat at the edges of their search bands (fixed in the final run).** `results/preset_landmark_heights.json` stores each landmark's height as a fraction of stature:

| landmark | band | at the band's top edge |
|---|---|---|
| chest | 69–74% | **202 / 210** |
| waist | 56–69% | 72 / 210 |
| hip | 46–56% | 44 / 210 |

Girth on MHR keeps increasing toward the armpit, so "max girth in 69–74%" returns the 74% cap (set to keep the arms out), not the bust point that ISO 8559-1 defines. On 9 large ovals, the waist and hip slices also collapse onto the same height (gap < 2% of stature). The fitted numbers match their targets, but they are measured at partly arbitrary heights. **Cause:** the girth rise above 70% of stature is real chest anatomy (the nipple line is at ~74% on MHR), not arm contamination; arms only merge above ~75%. **Fix (`mhr_body.landmarks`):**
- Slice with arm faces removed; arm vertices are those skinned mainly to shoulder joints 39/75 or their children.
- Bust/chest at the height of bust-point vertex 6034 (73.9% on the neutral body).
- Hip at the height of buttock vertex 7323 (55.8%), the greatest posterior protrusion, as ISO 8559-1 defines hip girth.
- Waist = the narrowest girth between them, keeping 15% margins clear of both.

Because MHR's topology is fixed, these vertices hold for every body. Fitting also got faster (~80 s vs ~110 s per body).

**2. Female presets looked anatomically male (fixed in the final run).** MHR has no sex parameter: identity is 45 PCA coeffs with no semantic axes (MHR paper, arXiv 2511.15586). Matching three girths left the shoulders as broad as the mean body's.
- **Cue chosen from data.** In ANSUR II, the strongest female/male separators among available measurements are biacromial ÷ hip breadth (F 1.037, M 1.204; 2.2 SD apart) and chest depth ÷ chest girth (2.1 SD). The neutral MHR body already has a female-range bust depth (0.257), so shoulder-to-hip width was the missing cue.
- **Measured on the mesh** as the shoulder-joint distance (joints 39/75) ÷ hip breadth (arm-free slice at the buttock vertex). The neutral ratio is 0.913.
- **Calibration assumption:** MHR's mean body is taken as the midpoint of the ANSUR female and male ratios. That maps mesh 0.913 → 1.12 and gives mesh targets **F 0.846, M 0.983** (`SHOULDER_HIP_TARGET` in `mhr_body.py`).
- **Added as a fourth fit target** (weight: 0.01 of ratio = 1 cm of girth). Test fits: female hourglass M and rectangle M reach a ratio of 0.848–0.849 with girth errors ≤ 0.21 cm, and the silhouettes read as female (narrower shoulders, wider hips). `female_oval_3XL_165` reaches 0.85 and `male_oval_M_175` 0.98, both accepted.
- **First cluster run with a fixed target per sex: 207/210 accepted.** The 3 failures were women's inverted triangles (XS 165/175, S 175), fitted as rectangles with hip +3.4 to +6.5 cm. A fixed "wide hips" ratio contradicts a narrow-hipped shape.
- **Fix: shape-aware target.** `shoulder_hip_target = T_sex × (bust + typical hip−bust) / hip`, where the ANSUR II median hip − bust is +7.7 cm (F) and −3.7 cm (M). Since hip breadth scales with hip girth, this holds the **absolute shoulder width** at the sex-typical value and lets the ratio follow the shape's own hips (women M: triangle 0.81, rectangle 0.90, hourglass 0.90, oval 0.94, inverted triangle 1.05). The 3 failed presets then fit within 0.42 cm and keep their class.
- Alternatives considered and not used: an LDA "sex direction" over MHR coeffs (needs sex-labelled scans), SOMA/Anny mapping, and SMPL→MHR registration (both add a second body model).

**3. Height uses a global scale (open).** A 155 cm preset is a scaled-down 172.7 cm body, not a shorter-proportioned one. **Fix to test:** fit MHR's per-bone scale parameters for stature.

## 7. Fabric and stretch (contract v0.4.0)

Ease = garment − body assumes a rigid garment, and fabric breaks that assumption. `stylewise_fit/fabric.py` adds three **project heuristics**, which are not measurements:
- **Rigid wovens** (silk, satin, cotton, polyester): no give. Below the minimum ease, the verdict is tight.
- **Stretch** (elastane, jersey, knit): the garment can give 5% of its girth. **Elastic or drawstring waists** give the range printed on the chart (e.g. Indubindu pant waist 86–92 cm → 6 cm). A region that only fits by stretching is `borderline`, with an `advice_facts` line saying so.
- **Bulky** (velvet, wool): +1 cm minimum ease for the fabric's own thickness.
- **Rib knit**: the garment can give 10% of its girth, since rib knits are cut to sit below body size. A plain stretch blend gives 5%.
- **Unknown fabric** is listed under `unknowns`, never assumed rigid.

## 8. Garment sources

`scripts/make_catalogue_garments.py` → `stylewise_fit/data/catalogue_garments.json`. Catalogue items come from the Stylewise app (synthetic brands, letter sizes only), so cm had to come from elsewhere.
- **Indubindu kurta-set chart** (states "actual garment measurements in centimeter") for 3 kurtas, 3 trousers and 6 sets. Its L hip is printed as "107-44" (a typo) and is left blank.
- **Uniqlo SG Product Size tables** (flat-laid; body width ×2 = bust) for a crew-neck tee (E465193) and a cotton-stretch long dress (E487286; its "hip width" is read as a circumference, since doubling it would give 217+ cm). **Cross-brand finding:** the Uniqlo L tee (105 cm chest) is tight on our general L body (ANSUR II L, 112 cm) by −7 cm. Letter sizes are brand-specific, which is the reason to compare garment cm with a body instead of trusting the label.
- **Estimated** (flagged "no verified source"): blouse, shell top, 2 skirts and 2 dresses use Uniqlo body-chart midpoints plus a design-ease guess per garment type. A "reference dress" table that was not a specific product is kept separate and flagged.
- **Rejected sources:** Tjori (unclear whether body or garment measurements), Dissh (a "garment" chart that contradicts itself), and most Western brands (body charts only).

## 9. Garment-on-body visualisation

`scripts/render_fit.py <preset[,preset…]> <garment:size>…` → PNG (front/side/back, one row per body) and a vertex-coloured GLB for the viewer.
- **Fit shell:** the body surface offset outward by the garment's ease at each height (Δgirth / 2π), in the garment's colour. Below the hip, kurtas, dresses, skirts and long tops hang as a tube around both legs, built from the convex hull of each slice plus a typical flare. Trousers follow the legs. Sleeves are typical lengths per garment type.
- **Verdicts** are drawn as dashed lines at the measured chest, waist and hip, with coloured labels.
- **It is not cloth simulation:** no drape, folds or gravity. Garment cuts (hem, sleeve, flare) are typical values per type, not measured. It shows how much room the size chart leaves.
- **Proposed scaling (from discussion with the supervisor):** the viewer rotates a GLB live, so different views cost nothing. What is expensive is fitting a custom body (~80 s on CPU). Cache fitted bodies by a hash of (sex, measurements rounded to 0.5 cm, model + engine version), like a Redis key, and serve the nearest preset while a custom body fits. A versioned key makes a TTL unnecessary for correctness; use TTL or LRU only to cap storage.

## 10. Garment modelling: next steps (research, not built)

- **Done:** SAM 3.1 (Meta Model API) cuts the garment out of a product photo; verified on a catalogue photo.
- **Next:** photo → 3D garment mesh with TRELLIS.2 or Hunyuan3D, then scale it with the sourced size chart so the mesh matches the measurements. Pixels never set cm.
- **Not for fit claims:** image and video try-on models (OutfitAnyone, Veo, Seedance, WAN) generate appearance with no measured geometry, so they suit visuals only.
- **Real drape** would need sewing patterns (e.g. GarmentCode) plus cloth simulation.

## 10b. Nisha on Muse (live check, 2026-11-02)

Model `muse-spark-1.3` (available: muse-spark-1.1–1.3, muse-wonder-1.0, sam-3.1). Body 165 / 92 / 87 / 100.
- "Will the green kurta in M fit me?" → one `evaluate_fit` call (garment_id green-kurta, M) with the right body. The reply repeats chest and waist "ok", "hip unknown" and "not a comfort promise". 12.5 s.
- "And the gold trousers in M?" → waist −1 cm **borderline**, "works only if the stretch gives, about 6 cm"; hip +2 ok. 12.9 s.
- Nisha only repeated facts from the report. Both replies offered to check size L as a next step.

## 11. Controlled evaluation cases

`scripts/eval_cases.py` (also run by `tests/test_eval_cases.py`): known body × garment pairs with the verdict we expect and why. They cover the ease bands, preferences, elastic and fabric stretch, missing measurements and preset uncertainty.

| case | garment | region | ease cm | expected | got | | why |
|---|---|---|---|---|---|---|---|
| Kurta, roomy chest | green-kurta M | chest | +9.0 | ok | ok | pass | +9 cm is inside the regular band (2-12) |
| Kurta one size down | green-kurta XS | chest | -3.0 | tight | tight | pass | -3 cm, and silk cannot stretch |
| Same kurta, snug preference | green-kurta M | chest | +9.0 | loose | loose | pass | +9 cm is above the snug band (0-6) |
| Trousers on elastic waist | gold-trousers M | waist | -1.0 | borderline | borderline | pass | -1 cm relaxed, fits only by using the 6 cm elastic |
| Trousers waist beyond elastic | gold-trousers M | waist | -10.0 | tight | tight | pass | -10 cm, more than the elastic can give |
| Stretch dress at the bust | uniqlo-dress-E487286 M | chest | -2.0 | borderline | borderline | pass | -2 cm relaxed; cotton stretch gives ~4 cm |
| Missing hip measurement | green-kurta M | hip | - | unknown | unknown | pass | never estimated when not given |
| Preset body near band edge | green-kurta M | chest | +3.1 | borderline | borderline | pass | +3.1 cm ±2.7 crosses the 2 cm minimum |

8/8 cases pass

## 12. Caveats for the write-up

- Preset girths are estimates from silhouette + usual size, never measurements. The engine reports them with a ± range and a `borderline` verdict.
- ANSUR II is a military sample, and the FFIT shape thresholds were developed on women.
- B-A uses synthetic references from MHR itself; no real-scan validation has been done yet.
- Fabric rules, garment cuts and estimated garments are project heuristics. Every report that relies on an estimated chart carries a warning.
- Shoulder-to-hip calibration assumes MHR's mean body is midway between ANSUR II women and men.
