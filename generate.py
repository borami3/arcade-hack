"""Generate one Arcade jewelry piece per bridesmaid in parallel and cache to products.json.

Usage:
  python generate.py              # generate everyone
  python generate.py litzy sarah  # regenerate only these, keep the rest from products.json
"""
import base64
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic
import arcade

FALLBACK_METAL = "925 Sterling Silver"


# ── Vision LLM: Claude writes the jewelry prompt ─────────────────────────────

def write_prompt_with_claude(theme, bm):
    """Send the bridesmaid's outfit photo + style answers to Claude,
    get back a specific Arcade-ready jewelry prompt."""
    client = anthropic.Anthropic()

    # Build image content block if photo exists
    photo_path = bm.get("outfit_photo") or bm.get("photo", "")
    content = []

    if photo_path and Path(photo_path).exists():
        img_bytes = Path(photo_path).read_bytes()
        ext = Path(photo_path).suffix.lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "webp": "image/webp"}.get(ext, "image/jpeg")
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime,
                "data": base64.standard_b64encode(img_bytes).decode(),
            },
        })
        photo_context = "Look at this photo of her outfit and personal style."
    else:
        photo_context = "No photo provided — rely on the text answers only."

    content.append({
        "type": "text",
        "text": f"""{photo_context}

Wedding theme
─────────────
Name: {theme['name']}
Summary: {theme['summary']}
Metal: {theme['metal']}
Motifs: {', '.join(theme['motifs'])}
Formality: {theme['formality']}

Her style answers
─────────────────
Name: {bm['name']}
Metal preference: {bm.get('metal_pref', 'gold')}
Scale: {bm.get('size_pref', 'medium')}
Vibe in one word: {bm.get('vibe', '')}
Style tags: {', '.join(bm.get('style_tags', []))}

Task
────
Write ONE jewelry prompt (60–90 words) for an Arcade jewelry maker.
Rules:
- Keep the wedding motifs (olive leaves, vines, garden blossoms) and metal tone fixed.
- Vary the piece TYPE, scale, shape, and surface detail to match her personal style.
- Mention {theme['metal']} as the metal.
- Be specific: name exact shapes, textures, finishes.
- Do NOT mention the bride's name or the wedding name.
- Return only the prompt — no explanation, no title, no bullet points.""",
    })

    msg = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=200,
        messages=[{"role": "user", "content": content}],
    )
    return msg.content[0].text.strip()


def write_rationale_with_claude(theme, bm, prompt, title):
    """One sentence explaining why this piece fits her specifically."""
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=80,
        messages=[{
            "role": "user",
            "content": (
                f"In one sentence (max 20 words), explain why '{title}' suits {bm['name']} "
                f"({bm.get('vibe','')}, {bm.get('size_pref','')}, "
                f"{', '.join(bm.get('style_tags',[]))}) "
                f"for a {theme['name']} wedding. Be warm and specific. No filler."
            ),
        }],
    )
    return msg.content[0].text.strip()


# ── Arcade generation ─────────────────────────────────────────────────────────

def build_fallback_prompt(theme, bm, metal=None, simple=False):
    """Fallback used if Claude vision fails."""
    metal = metal or theme["metal"]
    if simple:
        return f"{metal} {bm['category'].lower()} featuring {theme['motifs'][0]}, elegant and simple."
    return (
        f"{bm.get('piece', bm['category'])}. Made in {metal}. "
        f"Garden wedding bridesmaid jewelry inspired by {', '.join(theme['motifs'])}; "
        f"{theme['formality']} style."
    )


def find_category(categories, desired):
    if desired in categories:
        return categories[desired]
    d = desired.lower()
    for name, cat in categories.items():
        if d in name.lower() or name.lower() in d:
            return cat
    return categories.get("Pendant Necklace") or next(iter(categories.values()))


def generate_one(theme, bm, categories):
    log = lambda m: print(f"[{bm['name']}] {m}", flush=True)
    cat = find_category(categories, bm["category"])

    # Step 1: Claude writes the prompt from her photo + answers
    log("asking Claude to write prompt from photo + style answers…")
    try:
        vision_prompt = write_prompt_with_claude(theme, bm)
        log(f"Claude prompt: {vision_prompt[:80]}…")
    except Exception as e:
        log(f"Claude failed ({e}), falling back to template prompt")
        vision_prompt = None

    # Step 2: build attempt list — vision prompt first, then fallbacks
    attempts = []
    if vision_prompt:
        attempts.append(vision_prompt)
    attempts += [
        build_fallback_prompt(theme, bm),
        build_fallback_prompt(theme, bm, simple=True),
        build_fallback_prompt(theme, bm, metal=FALLBACK_METAL, simple=True),
    ]

    # Step 3: try each prompt against Arcade until one succeeds
    for i, prompt in enumerate(attempts, 1):
        log(f"Arcade attempt {i}: {prompt[:72]}…")
        try:
            job = arcade.create_pattern(prompt, cat["categoryId"])
            job = arcade.wait_for_job(job["jobId"], log=log)
        except (arcade.ArcadeError, TimeoutError) as e:
            log(f"error: {e}")
            continue
        if job["status"] != "succeeded":
            log(f"failed: {(job.get('error') or {}).get('message')}")
            continue

        p = arcade.get_product(job["result"]["productId"])
        log(f"OK  {p['title']}  ${p['unitPrice']['amount']}")

        # Step 4: Claude writes a one-sentence rationale
        title = p["title"]
        try:
            rationale = write_rationale_with_claude(theme, bm, title, title)
        except Exception:
            rationale = bm.get("rationale", "")

        return {
            "id":          bm["id"],
            "name":        bm["name"],
            "photo":       bm.get("photo", ""),
            "style_tags":  bm["style_tags"],
            "rationale":   rationale,
            "category":    bm["category"],
            "prompt":      prompt,
            "productId":   p["productId"],
            "patternId":   p.get("patternId"),
            "title":       title,
            "material":    p.get("selectionLabel") or p.get("selections", {}).get("material"),
            "maker":       (p.get("maker") or {}).get("name"),
            "imageUrl":    p.get("imageUrl"),
            "description": p.get("description", ""),
            "price":       float(p["unitPrice"]["amount"]),
            "currency":    p["unitPrice"]["currency"],
        }

    log("GAVE UP after all attempts")
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    arcade.load_env()
    data  = json.load(open("demo_data.json"))
    theme = data["bride"]["theme"]
    only  = set(sys.argv[1:])

    existing = {}
    if only and os.path.exists("products.json"):
        existing = {p["id"]: p for p in json.load(open("products.json"))["bridesmaids"] if p}

    categories = arcade.jewelry_categories()
    todo = [bm for bm in data["bridesmaids"] if not only or bm["id"] in only]

    print(f"Generating {len(todo)} pieces (Claude vision → Arcade)…\n")
    with ThreadPoolExecutor(max_workers=len(todo)) as pool:
        results = list(pool.map(lambda bm: generate_one(theme, bm, categories), todo))

    for r in results:
        if r:
            existing[r["id"]] = r

    pieces   = [existing[bm["id"]] for bm in data["bridesmaids"] if bm["id"] in existing]
    checkout = arcade.create_checkout([p["productId"] for p in pieces]) if pieces else {}

    out = {
        "wedding":     data["wedding"],
        "bride":       data["bride"]["name"],
        "theme":       theme,
        "bridesmaids": pieces,
        "total":       round(sum(p["price"] for p in pieces), 2),
        "currency":    pieces[0]["currency"] if pieces else "USD",
        "checkoutId":  checkout.get("checkoutId"),
        "checkoutUrl": checkout.get("checkoutUrl"),
    }
    json.dump(out, open("products.json", "w"), indent=2)
    print(f"\nSaved {len(pieces)}/{len(data['bridesmaids'])} pieces  "
          f"total ${out['total']}  checkout: {out['checkoutUrl']}")


if __name__ == "__main__":
    main()
