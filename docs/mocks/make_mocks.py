"""UI mock-ups for P1, composed from the real demo renders and product photos."""
import glob
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path("/Users/riddhimajain/NTU & Opportunities/Hackathons/stylewise-hackathon")
CACHE, PHOTOS, OUT = ROOT / "fixtures/preview_cache", ROOT / "fixtures/garment_photos", ROOT / "docs/mocks"
OUT.mkdir(exist_ok=True)
SANS = "/System/Library/Fonts/HelveticaNeue.ttc"
SERIF = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"
BG, PANEL, INK, MUTED, LINE = "#f6f5ef", "#fdfdf9", "#2c3327", "#7d8576", "#e3e2d8"
SAGE, SAGE_SOFT = "#5f6f52", "#e4e9dc"
OK, OK_BG, WARN, WARN_BG, BAD, BAD_BG = "#3f7a4a", "#e2efe1", "#9a6b12", "#f7ecd3", "#a34236", "#f6dfdb"


def f(size, serif=False, bold=False):
    return ImageFont.truetype(SERIF if serif else SANS, size, index=0 if serif else (1 if bold else 0))


def render(gid, size, view):
    return Image.open(glob.glob(str(CACHE / f"{gid}_{size}_{view}_*.png"))[0]).convert("RGB")


def fit_into(img, w, h):
    img = img.copy(); img.thumbnail((w, h)); return img


def rr(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


def pill(d, x, y, text, font, fg, bg, outline=None, pad=(14, 7)):
    w = d.textlength(text, font=font)
    rr(d, (x, y, x + w + 2 * pad[0], y + font.size + 2 * pad[1]), (font.size + 2 * pad[1]) // 2, bg, outline)
    d.text((x + pad[0], y + pad[1] - 1), text, font=font, fill=fg)
    return x + w + 2 * pad[0]


def thumb(canvas, path, box, selected=False, label=None):
    d = ImageDraw.Draw(canvas)
    x0, y0, x1, y1 = box
    rr(d, box, 12, "#efede6", SAGE if selected else LINE, 3 if selected else 1)
    im = Image.open(path).convert("RGB"); im.thumbnail((x1 - x0 - 12, y1 - y0 - (34 if label else 12)))
    canvas.paste(im, (x0 + (x1 - x0 - im.width) // 2, y0 + 6))
    if label:
        d.text((x0 + 8, y1 - 24), label, font=f(13), fill=INK if selected else MUTED)


def silhouette(d, cx, top, kind, colour):
    w = {"hourglass": (14, 8, 15), "triangle": (11, 10, 17), "inverted": (17, 11, 11), "rectangle": (13, 12, 13), "oval": (13, 16, 14)}[kind]
    d.ellipse((cx - 6, top, cx + 6, top + 12), fill=colour)
    s, wa, h = w
    d.polygon([(cx - s, top + 16), (cx + s, top + 16), (cx + wa, top + 34), (cx + h, top + 50), (cx - h, top + 50), (cx - wa, top + 34)], fill=colour)
    d.rectangle((cx - 9, top + 50, cx - 3, top + 66), fill=colour); d.rectangle((cx + 3, top + 50, cx + 9, top + 66), fill=colour)


def verdict_rows(d, x, y, rows, width):
    for name, value, kind, note in rows:
        col = {"ok": OK, "warn": WARN, "bad": BAD}[kind]
        d.text((x, y), name, font=f(15), fill=INK)
        d.text((x + width - d.textlength(value, font=f(15, bold=True)), y), value, font=f(15, bold=True), fill=col)
        d.text((x, y + 21), note, font=f(13), fill=MUTED)
        # tape: centre = body, marker = garment room
        rr(d, (x, y + 42, x + width, y + 48), 3, "#ecebe3")
        rr(d, (x + width // 2 - 1, y + 38, x + width // 2 + 1, y + 52), 1, MUTED)
        rr(d, (x + width // 2, y + 42, x + width // 2 + {"ok": 34, "warn": 70, "bad": -60}[kind], y + 48), 3, col) if kind != "bad" else \
            rr(d, (x + width // 2 - 60, y + 42, x + width // 2, y + 48), 3, col)
        y += 68
    return y


def header(d, W):
    d.rectangle((0, 0, W, 64), fill=PANEL); d.line((0, 64, W, 64), fill=LINE)
    d.text((32, 16), "stylewise", font=f(28, serif=True), fill=INK)
    x = 210
    for i, t in enumerate(["Try on", "My fit", "Wardrobe"]):
        if i == 0:
            x = pill(d, x, 16, t, f(15), "#fff", SAGE) + 10
        else:
            d.text((x + 8, 23), t, font=f(15), fill=MUTED); x += d.textlength(t, font=f(15)) + 34
    pill(d, W - 300, 15, "Ask Nisha", f(15), SAGE, SAGE_SOFT)
    pill(d, W - 150, 15, "Bag · 1", f(15), INK, "#fff", LINE)


# ---------------------------------------------------------------- 1. desktop try-on
def desktop():
    W, H = 1440, 940
    c = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(c)
    header(d, W)
    # left: you
    rr(d, (24, 88, 300, 916), 18, PANEL, LINE)
    d.text((44, 108), "1 · YOU", font=f(13, bold=True), fill=MUTED)
    d.text((44, 130), "Your shape", font=f(22, serif=True), fill=INK)
    for i, (k, n) in enumerate([("hourglass", "Balance"), ("triangle", "Anchor"), ("inverted", "Summit"), ("rectangle", "Column"), ("oval", "Orbit")]):
        x, y = 44 + (i % 3) * 82, 172 + (i // 3) * 112
        sel = k == "rectangle"
        rr(d, (x, y, x + 74, y + 102), 12, SAGE_SOFT if sel else "#f3f2ea", SAGE if sel else LINE, 2 if sel else 1)
        silhouette(d, x + 37, y + 10, k, SAGE if sel else "#b5bcab")
        d.text((x + 37 - d.textlength(n, font=f(12)) / 2, y + 82), n, font=f(12), fill=INK if sel else MUTED)
    d.text((44, 408), "Straight and even, bust to hip.", font=f(13), fill=MUTED)
    d.text((44, 446), "Usual size", font=f(14), fill=INK)
    x = 44
    for z in ["XS", "S", "M", "L", "XL"]:
        x = pill(d, x, 470, z, f(14), "#fff" if z == "M" else INK, SAGE if z == "M" else "#fff", LINE, (11, 7)) + 6
    d.text((44, 524), "Height", font=f(14), fill=INK)
    x = 44
    for z in ["155", "165", "175 cm"]:
        x = pill(d, x, 548, z, f(14), "#fff" if z == "165" else INK, SAGE if z == "165" else "#fff", LINE, (11, 7)) + 6
    d.line((44, 610, 280, 610), fill=LINE)
    d.text((44, 626), "2 · PREFERENCES", font=f(13, bold=True), fill=MUTED)
    d.text((44, 650), "Regular fit · No closure preference", font=f(14), fill=INK)
    d.line((44, 692, 280, 692), fill=LINE)
    d.text((44, 710), "YOUR BODY MODEL", font=f(13, bold=True), fill=MUTED)
    d.text((44, 734), "Built from your shape and size.", font=f(13), fill=MUTED)
    d.text((44, 754), "Measured, not a photo of you.", font=f(13), fill=MUTED)
    pill(d, 44, 786, "View 3D body model", f(14), SAGE, SAGE_SOFT)

    # centre: stage
    rr(d, (320, 88, 1040, 916), 18, "#ecebe5", LINE)
    stage = Image.new("RGB", (720, 640), "#e9e8e2")
    fig = fit_into(render("zesica-black-midi-dress", "M", "front"), 560, 620)
    stage.paste(fig, ((720 - fig.width) // 2, 10))
    c.paste(stage, (320, 120))
    d.text((348, 104), "Black bodycon midi dress · size M", font=f(22, serif=True), fill=INK)
    x = 348
    for v in ["Front", "Side", "Back"]:
        x = pill(d, x, 140, v, f(13), "#fff" if v == "Front" else INK, SAGE if v == "Front" else "#fff", LINE, (12, 6)) + 6
    # angle thumbnails
    for i, v in enumerate(["front", "side", "back"]):
        im = fit_into(render("zesica-black-midi-dress", "M", v), 70, 100)
        bx = (958, 150 + i * 116, 1024, 256 + i * 116)
        rr(d, bx, 10, "#fff", SAGE if v == "front" else LINE, 2 if v == "front" else 1)
        c.paste(im, (bx[0] + (66 - im.width) // 2, bx[1] + 3))
    # carousel
    d.line((340, 770, 1020, 770), fill=LINE)
    x = 348
    for t in ["Dresses", "Tops", "Sets", "Men"]:
        x = pill(d, x, 782, t, f(13), "#fff" if t == "Dresses" else INK, SAGE if t == "Dresses" else "#fff", LINE, (12, 5)) + 6
    items = ["zesica-black-midi-dress", "emerald-wrap-dress", "parthvi-anarkali-set", "cream-silk-blouse", "blush-shell-top", "charcoal-skirt"]
    for i, g in enumerate(items):
        thumb(c, PHOTOS / f"{g}.jpg", (348 + i * 112, 818, 448 + i * 112, 904), selected=i == 0)

    # right: product + fit
    rr(d, (1060, 88, 1416, 916), 18, PANEL, LINE)
    d.text((1084, 108), "ZESICA · Amazon", font=f(13), fill=MUTED)
    d.text((1084, 128), "Black bodycon midi dress", font=f(22, serif=True), fill=INK)
    d.text((1084, 160), "S$30.94  ·  91% polyester, 9% elastane", font=f(14), fill=MUTED)
    rr(d, (1084, 196, 1392, 262), 14, WARN_BG)
    d.text((1102, 206), "Snug at the waist in M", font=f(18, bold=True), fill=WARN)
    d.text((1102, 234), "L is the best fit for your shape", font=f(14), fill=INK)
    d.text((1084, 284), "Size", font=f(14), fill=INK)
    x = 1084
    for z, kind in [("S", "bad"), ("M", "warn"), ("L", "ok"), ("XL", None)]:
        col, bg = {"bad": (BAD, BAD_BG), "warn": (WARN, WARN_BG), "ok": (OK, OK_BG), None: (MUTED, "#f1f0ea")}[kind]
        sel = z == "M"
        rr(d, (x, 308, x + 64, 352), 12, bg, INK if sel else None, 2 if sel else 1)
        d.text((x + 32 - d.textlength(z, font=f(17, bold=True)) / 2, 318), z, font=f(17, bold=True), fill=col)
        x += 72
    pill(d, 1236, 360, "Best fit: L", f(12, bold=True), OK, OK_BG, None, (10, 4))
    d.text((1084, 402), "HOW SIZE M SITS ON YOU", font=f(12, bold=True), fill=MUTED)
    verdict_rows(d, 1084, 426, [("Bust", "0.6 cm tight", "warn", "Fabric stretches: just fits"),
                                ("Waist", "5.6 cm tight", "warn", "Pulls at the waist"),
                                ("Hips", "+5.8 cm room", "ok", "Comfortable")], 308)
    rr(d, (1084, 646, 1392, 694), 24, INK)
    d.text((1238 - d.textlength("Add L to bag", font=f(16, bold=True)) / 2, 659), "Add L to bag", font=f(16, bold=True), fill="#fff")
    rr(d, (1084, 706, 1392, 754), 24, SAGE_SOFT)
    d.text((1238 - d.textlength("Ask Nisha: should I size up?", font=f(15)) / 2, 721), "Ask Nisha: should I size up?", font=f(15), fill=SAGE)
    d.text((1084, 776), "How we know", font=f(14, bold=True), fill=INK)
    for i, t in enumerate(["Brand size chart (cm), ZESICA SG Regular", "Your shape + usual size measured body",
                           "Picture drawn from the fit, not a promise"]):
        d.text((1084, 800 + i * 22), "·  " + t, font=f(13), fill=MUTED)
    c.save(OUT / "01_try_on_desktop.png")


# ---------------------------------------------------------------- 2. compare sizes
def compare():
    W, H = 1440, 820
    c = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(c)
    header(d, W)
    d.text((48, 92), "Compare sizes on your shape", font=f(30, serif=True), fill=INK)
    d.text((48, 134), "Black bodycon midi dress · The Column, usual size M, 165 cm", font=f(15), fill=MUTED)
    cards = [("S", "Too tight at the waist", "13 cm too small at the waist", BAD, BAD_BG),
             ("M", "Snug at the waist", "Bust just fits · waist 5.6 cm tight", WARN, WARN_BG),
             ("L", "Best fit", "Bust +7 · waist +2 · hips roomy +13.5", OK, OK_BG)]
    for i, (z, title, note, col, bg) in enumerate(cards):
        x0 = 48 + i * 456
        best = z == "L"
        rr(d, (x0, 172, x0 + 432, 796), 20, PANEL, OK if best else LINE, 3 if best else 1)
        fig = fit_into(render("zesica-black-midi-dress", z, "front"), 400, 470)
        c.paste(fig, (x0 + (432 - fig.width) // 2, 186))
        rr(d, (x0 + 20, 668, x0 + 412, 776), 14, bg)
        d.text((x0 + 38, 680), f"Size {z}", font=f(14), fill=MUTED)
        d.text((x0 + 38, 700), title, font=f(22, serif=True), fill=col)
        d.text((x0 + 38, 736), note, font=f(14), fill=INK)
        if best:
            pill(d, x0 + 330, 190, "Best fit", f(13, bold=True), OK, OK_BG, None, (10, 5))
    c.save(OUT / "02_compare_sizes.png")


# ---------------------------------------------------------------- 3. mobile
def phone(content_fn):
    W, H = 390, 844
    p = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(p)
    d.text((22, 14), "9:41", font=f(15, bold=True), fill=INK)
    d.text((22, 46), "stylewise", font=f(24, serif=True), fill=INK)
    pill(d, 290, 46, "Bag · 1", f(13), INK, "#fff", LINE, (10, 5))
    content_fn(p, d)
    frame = Image.new("RGB", (W + 24, H + 24), "#1d1f1b")
    mask = Image.new("L", (W, H), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, W, H), 44, fill=255)
    frame.paste(p, (12, 12), mask)
    fm = Image.new("L", frame.size, 0); ImageDraw.Draw(fm).rounded_rectangle((0, 0, *frame.size), 54, fill=255)
    out = Image.new("RGBA", frame.size, (0, 0, 0, 0)); out.paste(frame, (0, 0), fm)
    return out


def m_tryon(p, d):
    fig = fit_into(render("emerald-wrap-dress", "M", "front"), 340, 420)
    p.paste(fig, ((390 - fig.width) // 2, 88))
    x = 22
    for v in ["Front", "Side", "Back"]:
        x = pill(d, x, 96, v, f(12), "#fff" if v == "Front" else INK, SAGE if v == "Front" else "#fff", LINE, (10, 4)) + 4
    d.text((22, 520), "Emerald wrap dress · M", font=f(20, serif=True), fill=INK)
    rr(d, (22, 556, 368, 600), 12, WARN_BG)
    d.text((36, 568), "Close at the waist · roomy at hips", font=f(15, bold=True), fill=WARN)
    x = 22
    for z, col, bg in [("XS", BAD, BAD_BG), ("S", BAD, BAD_BG), ("M", WARN, WARN_BG), ("L", WARN, WARN_BG), ("XL", BAD, BAD_BG)]:
        rr(d, (x, 614, x + 60, 654), 10, bg, INK if z == "M" else None, 2)
        d.text((x + 30 - d.textlength(z, font=f(15, bold=True)) / 2, 624), z, font=f(15, bold=True), fill=col); x += 69
    for i, g in enumerate(["emerald-wrap-dress", "zesica-black-midi-dress", "parthvi-anarkali-set", "cream-silk-blouse"]):
        img = Image.open(PHOTOS / f"{g}.jpg").convert("RGB"); img.thumbnail((76, 76))
        bx = 22 + i * 88
        rr(d, (bx, 668, bx + 80, 748), 10, "#efede6", SAGE if i == 0 else LINE, 2 if i == 0 else 1)
        p.paste(img, (bx + (80 - img.width) // 2, 670))
    rr(d, (22, 764, 230, 810), 23, INK); d.text((56, 777), "Add M to bag", font=f(15, bold=True), fill="#fff")
    rr(d, (240, 764, 368, 810), 23, SAGE_SOFT); d.text((262, 777), "Nisha", font=f(15), fill=SAGE)


def m_nisha(p, d):
    fig = fit_into(render("emerald-wrap-dress", "M", "side"), 340, 330).filter(ImageFilter.GaussianBlur(1.5))
    p.paste(fig, ((390 - fig.width) // 2, 84))
    rr(d, (0, 400, 390, 844), 28, PANEL); d.line((0, 400, 390, 400), fill=LINE)
    rr(d, (175, 410, 215, 414), 2, LINE)
    d.text((22, 428), "Nisha", font=f(20, serif=True), fill=INK)
    d.text((22, 456), "Your sizing assistant", font=f(13), fill=MUTED)
    rr(d, (100, 490, 368, 534), 16, SAGE); d.text((116, 503), "Should I size up for the waist?", font=f(14), fill="#fff")
    rr(d, (22, 548, 330, 684), 16, "#efeee7")
    for i, t in enumerate(["M is 1.5 cm close at the waist, but", "the wrap tie adjusts, and the hips", "have 13 cm of room. L would hang", "loose at the hips (+18 cm). Stay with M."]):
        d.text((38, 562 + i * 28), t, font=f(14), fill=INK)
    for i, t in enumerate(["Compare S and M", "Will it shrink?"]):
        pill(d, 22 + i * 168, 702, t, f(13), SAGE, SAGE_SOFT, None, (12, 6))
    rr(d, (22, 764, 368, 810), 23, "#fff", LINE); d.text((40, 778), "Ask about this dress…", font=f(14), fill=MUTED)


def mobile():
    a, b = phone(m_tryon), phone(m_nisha)
    c = Image.new("RGB", (a.width * 2 + 120, a.height + 80), BG)
    c.paste(a, (40, 40), a); c.paste(b, (a.width + 80, 40), b)
    c.save(OUT / "03_mobile.png")




# ---------------------------------------------------------------- 4. landing + onboarding (illustrated)
CLAY, BLUSH, SAND = "#c98b6b", "#efd9cf", "#e9dcc4"


def hanger(d, cx, top, s, col):
    d.arc((cx - 7 * s, top, cx + 7 * s, top + 14 * s), 180, 90, fill=col, width=max(2, s))
    d.line((cx, top + 14 * s, cx, top + 20 * s), fill=col, width=max(2, s))
    d.line((cx, top + 20 * s, cx - 40 * s, top + 44 * s), fill=col, width=max(3, s + 1))
    d.line((cx, top + 20 * s, cx + 40 * s, top + 44 * s), fill=col, width=max(3, s + 1))
    d.line((cx - 40 * s, top + 44 * s, cx + 40 * s, top + 44 * s), fill=col, width=max(3, s + 1))


def tape(d, x, y, w, col=SAGE):
    rr(d, (x, y, x + w, y + 34), 8, "#f4e7b8", col, 2)
    for i in range(0, w - 10, 12):
        h = 14 if (i // 12) % 5 == 0 else 8
        d.line((x + 8 + i, y + 2, x + 8 + i, y + 2 + h), fill=col, width=2)
    d.text((x + 10, y + 16), "84  86  88  90  92" if w > 120 else "cm", font=f(11), fill=col)


def tag(d, x, y, text, col, bg):
    d.polygon([(x, y + 22), (x + 22, y), (x + 92, y), (x + 92, y + 44), (x + 22, y + 44)], fill=bg, outline=col)
    d.ellipse((x + 16, y + 18, x + 26, y + 28), outline=col, width=2)
    d.text((x + 38, y + 10), text, font=f(20, bold=True), fill=col)


def curtain(d, x, y, w, h):
    d.line((x - 10, y, x + w + 10, y), fill=INK, width=4)
    for i in range(6):
        cx = x + i * w / 6
        d.rectangle((cx, y + 4, cx + w / 6 - 3, y + h), fill=CLAY if i % 2 == 0 else "#b97a5c")
    d.ellipse((x - 16, y - 6, x - 4, y + 6), fill=INK); d.ellipse((x + w + 4, y - 6, x + w + 16, y + 6), fill=INK)


def bag(d, x, y, s=1.0, col=INK):
    rr(d, (x, y + 22 * s, x + 70 * s, y + 96 * s), 10, SAND, col, 2)
    d.arc((x + 16 * s, y, x + 54 * s, y + 44 * s), 180, 360, fill=col, width=3)


def mannequin_icon(d, cx, y, col):
    d.ellipse((cx - 11, y, cx + 11, y + 24), fill=col)
    d.polygon([(cx - 22, y + 30), (cx + 22, y + 30), (cx + 14, y + 58), (cx + 20, y + 84), (cx - 20, y + 84), (cx - 14, y + 58)], fill=col)
    d.line((cx, y + 84, cx, y + 104), fill=col, width=4); d.line((cx - 16, y + 104, cx + 16, y + 104), fill=col, width=4)


def landing():
    W, H = 1440, 1180
    c = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(c)
    header(d, W)
    # hero
    d.text((80, 130), "FIND YOUR SIZE BEFORE YOU BUY", font=f(14, bold=True), fill=SAGE)
    d.text((80, 160), "See how every size", font=f(60, serif=True), fill=INK)
    d.text((80, 228), "sits on your shape.", font=f(60, serif=True), fill=SAGE)
    for i, t in enumerate(["Real brand size charts, a body built from your shape,", "and an honest answer for every size. No model faces."]):
        d.text((80, 318 + i * 28), t, font=f(19), fill=MUTED)
    rr(d, (80, 400, 300, 456), 28, INK); d.text((112, 416), "Start fitting", font=f(19, bold=True), fill="#fff")
    rr(d, (316, 400, 520, 456), 28, "#fff", LINE); d.text((346, 416), "See how it works", font=f(17), fill=INK)
    # hero illustration: fitting room
    rr(d, (780, 104, 1360, 560), 30, "#efe9de")
    curtain(d, 820, 150, 150, 340)
    fig = fit_into(render("emerald-wrap-dress", "M", "front"), 260, 380)
    fm = Image.new("L", fig.size, 0); ImageDraw.Draw(fm).rounded_rectangle((0, 0, *fig.size), 24, fill=255)
    rr(d, (995, 140, 1005 + fig.width, 150 + fig.height), 26, "#fff")
    c.paste(fig, (1000, 145), fm)
    hanger(d, 1290, 170, 1, INK)
    tag(d, 1250, 420, "M", OK, OK_BG)
    tape(d, 850, 505, 220)
    bag(d, 1270, 300, 0.9)
    rr(d, (1010, 470, 1230, 520), 14, "#fff", LINE)
    d.text((1026, 478), "Size M", font=f(12), fill=MUTED); d.text((1026, 494), "Close at the waist, roomy at hips", font=f(13, bold=True), fill=WARN)
    # USP strip
    rr(d, (80, 600, 1360, 760), 24, PANEL, LINE)
    usp = [("Measured, not guessed", "Brand charts in cm against a body", "built from your shape and size."),
           ("Every size has a verdict", "Snug, fits or roomy, region by region,", "and a best fit for you."),
           ("Your shape, no model faces", "Every shape, XS to 3XL, men and women,", "on a calm faceless mannequin.")]
    for i, (t, a, b) in enumerate(usp):
        x = 112 + i * 420
        if i == 0: tape(d, x, 640, 72)
        if i == 1: tag(d, x - 6, 634, "L", SAGE, SAGE_SOFT)
        if i == 2: mannequin_icon(d, x + 30, 626, "#b5bcab")
        d.text((x + 104, 640), t, font=f(20, serif=True), fill=INK)
        d.text((x + 104, 674), a, font=f(14), fill=MUTED); d.text((x + 104, 694), b, font=f(14), fill=MUTED)
    # onboarding
    d.text((80, 800), "How it works", font=f(32, serif=True), fill=INK)
    steps = [("1", "Pick your shape", "Five silhouettes, your usual size and height.", "shape"),
             ("2", "Pick a garment", "From the shop: dresses, tops, sets, menswear.", "garment"),
             ("3", "See every size", "Front, side and back, with a verdict for each size.", "sizes")]
    for i, (n, t, sub, kind) in enumerate(steps):
        x0 = 80 + i * 436
        rr(d, (x0, 852, x0 + 412, 1150), 24, PANEL, LINE)
        rr(d, (x0 + 20, 872, x0 + 392, 1040), 18, ["#eef0e8", "#f3ebe2", "#eaf0ea"][i])
        if kind == "shape":
            for j, k in enumerate(["hourglass", "triangle", "rectangle", "inverted", "oval"]):
                silhouette(d, x0 + 70 + j * 68, 920, k, SAGE if k == "rectangle" else "#b5bcab")
        if kind == "garment":
            hanger(d, x0 + 206, 882, 1, INK)
            for j, g in enumerate(["zesica-black-midi-dress", "emerald-wrap-dress", "parthvi-anarkali-set"]):
                im = Image.open(PHOTOS / f"{g}.jpg").convert("RGB"); im.thumbnail((84, 84))
                c.paste(im, (x0 + 76 + j * 96, 944))
        if kind == "sizes":
            for j, (z, col, bg) in enumerate([("S", BAD, BAD_BG), ("M", WARN, WARN_BG), ("L", OK, OK_BG)]):
                tag(d, x0 + 46 + j * 112, 930, z, col, bg)
            d.text((x0 + 230, 990), "Best fit: L", font=f(14, bold=True), fill=OK)
        rr(d, (x0 + 24, 1060, x0 + 56, 1092), 16, SAGE); d.text((x0 + 35, 1066), n, font=f(16, bold=True), fill="#fff")
        d.text((x0 + 70, 1062), t, font=f(22, serif=True), fill=INK)
        d.text((x0 + 24, 1106), sub, font=f(14), fill=MUTED)
    c.save(OUT / "04_landing_onboarding.png")


desktop(); compare(); mobile(); landing()
print("ok", sorted(p.name for p in OUT.iterdir()))
