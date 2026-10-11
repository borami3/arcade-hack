# Project brief: "Match Without Matching" (Arcade Shopping 3.0 hackathon)

Read this before writing any code. I'm building solo. Hard deadline: **build done by 2:45pm**, submission due **3:15pm** (today). Optimize for one polished happy path, not features.

## Concept
A bridal party gets **coordinated but individual** jewelry: one shared theme from the bride, one unique piece per bridesmaid that fits her personal style. Tagline: "Together, yet individual" / "Match without matching."
Origin story (pitch only): Nigerian *aso-ebi*, where wedding guests share a fabric but each tailors it to herself. The product and demo are for any bridal party (diverse group, universal theme like a sage-and-gold garden wedding).

Why it needs Arcade: quantity-of-one manufacturing is what makes "matching but different" possible. Arcade's jewelry API turns a text prompt into a real, priced, orderable product.

## User flow (demo)
1. Bride provides inspiration images -> app extracts a shared **theme** (palette, metal, motifs, formality).
2. Each of ~4 bridesmaids provides 2-3 style images -> app writes a **personal jewelry prompt** = shared theme + her style.
3. Each prompt -> Arcade -> real product (image, title, metal, price).
4. **Group view**: all women side by side, each with her piece; shared theme shown at top. Tap one for detail + "why this fits her."
5. **One group checkout**: all pieces in a single Arcade checkout link, with the group total.

## Arcade API (jewelry) — verified from docs.arcade.ai
- Base URL: `https://platform.arcade.ai/v1`. Every request is **POST** with JSON body.
- Headers: `Authorization: Bearer $ARCADE_API_KEY`, `Content-Type: application/json`, `User-Agent: match-without-matching/1.0`.
- Key comes from env var `ARCADE_API_KEY`. Never hardcode or commit it.

Flow:
1. `categories/list` body `{}` -> pick items where `world == "jewelry"` (e.g., Rings, Pendant Necklace). **Don't hardcode categoryIds.** `categories/get` shows a category's options (e.g., metals).
2. `patterns/create` body `{ "requestId": "<unique>", "prompt": "...", "categoryId": "..." }` -> returns `{ jobId, status: "running" }`.
   - For jewelry, **do NOT send `modelId`, `referenceIds`, or `colors`.** Text prompt only. Mention desired metal in the prompt.
   - Prompt is validated against the category; a mismatch returns HTTP 400 with no job.
3. `jobs/get` body `{ "jobId": "..." }` -> poll until `status` is `succeeded` or `failed`. On success, `result` has `patternId` and `productId`. On failure, `error.message` explains (e.g., no maker could price it -> retry with a different metal/simpler prompt and a NEW requestId).
4. `products/get` body `{ "productId": "..." }` -> `title`, `selections` (e.g. material), `unitPrice { amount, currency }`.
5. `checkouts/create` body `{ "requestId": "...", "lines": [{ "productId": "...", "quantity": 1 }, ...], "dropShip": true }` -> `{ checkoutId, checkoutUrl }`. Multiple lines = one group checkout.
- Jewelry designs can't be refined/edited; to change a piece, create a new one.

## Gotchas
- Jobs are async and may be slow: **generate all pieces in parallel ahead of time and cache to JSON.** The demo must not depend on live generation.
- Price: 14k gold examples run ~$800+. Prefer sterling silver or cheaper metal options (check `categories/get`) so the group total looks realistic.
- Image models may handle dark skin tones / Nigerian styling poorly. Use precise vocabulary in prompts.

## Suggested architecture (keep it simple)
- `generate.py` (or .ts): reads `demo_data.json` (bride theme + bridesmaid style descriptions/images), uses a vision LLM to write each bridesmaid's prompt, calls Arcade in parallel, polls, saves `products.json` (prompt, productId, title, metal, price, image if available, rationale).
- Simple web front end (single page is fine) that reads `products.json` and renders the group view + detail + "Order as a group" button (calls `checkouts/create` or uses a pre-created `checkoutUrl`).
- Demo data: ~1 bride + 4 bridesmaids, using photos I have rights/consent to use.

## Timeline
- 12:45-1:15  Arcade smoke test (list categories, one create, poll, product). Demo data + theme extraction.
- 1:15-1:50   Per-bridesmaid prompt generation + parallel Arcade generation, cached to JSON.
- 1:50-2:25   Group view UI + detail view + group checkout.
- 2:25-2:45   Run happy path 3x, fix breaks, record backup screen video.
- 2:45-3:15   Slides + 2-minute demo (not code).

## Cut list if behind (in order)
1. Compositing pieces onto photos (just place piece next to photo).
2. Tap-to-detail view.
NEVER cut: group view, real Arcade-generated products, group checkout/total.

## Out of scope today
Live WhatsApp integration (show as a mock/vision slide), outfits/decor, real body tracking.
