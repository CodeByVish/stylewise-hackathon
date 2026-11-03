"""Draws the README diagrams in one cloud-architecture style (white canvas, labelled groups, square service
icons, right-angled connectors, numbered steps).

  fit-engine/.venv/bin/python docs/architecture/make_diagrams.py
writes architecture.png, styled_view_flow.png and nisha_flow.png next to this file.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
S = 2
SANS = "/System/Library/Fonts/HelveticaNeue.ttc"
INK, MUTED, LINE, WHITE = "#232f3e", "#5f6b7a", "#aab7b8", "#ffffff"
KIND = {"client": "#232f3e", "web": "#8c4fff", "compute": "#ed7100", "data": "#3f8624",
        "meta": "#0866ff", "security": "#dd344c"}
GROUP = {"cloud": "#232f3e", "vercel": "#8c4fff", "render": "#ed7100", "meta": "#0866ff", "nscc": "#c925d1", "device": "#5f6b7a"}
GLYPH = {"cloud": "cloud", "vercel": "web", "render": "compute", "meta": "meta", "nscc": "hpc", "device": "client"}


def font(size, bold=False):
    return ImageFont.truetype(SANS, size * S, index=1 if bold else 0)


class Canvas:
    def __init__(self, w, h, title, subtitle):
        self.w, self.h = w, h
        self.img = Image.new("RGB", (w * S, h * S), WHITE)
        self.d = ImageDraw.Draw(self.img)
        self.text((40, 28), title, 26, bold=True)
        self.text((40, 64), subtitle, 14, color=MUTED)

    def text(self, xy, s, size=14, bold=False, color=INK, anchor="la"):
        self.d.text((xy[0] * S, xy[1] * S), s, font=font(size, bold), fill=color, anchor=anchor)

    def line(self, p, q, color=INK, dashed=False, width=2):
        (x1, y1), (x2, y2) = p, q
        if not dashed:
            self.d.line([(x1 * S, y1 * S), (x2 * S, y2 * S)], fill=color, width=width * S)
            return
        n = max(1, int(math.hypot(x2 - x1, y2 - y1) // 8))
        for i in range(0, n, 2):
            a, b = i / n, min((i + 1) / n, 1)
            self.d.line([((x1 + (x2 - x1) * a) * S, (y1 + (y2 - y1) * a) * S),
                         ((x1 + (x2 - x1) * b) * S, (y1 + (y2 - y1) * b) * S)], fill=color, width=width * S)

    def group(self, x, y, w, h, kind, label, dashed=False):
        color = GROUP[kind]
        for p, q in (((x, y), (x + w, y)), ((x + w, y), (x + w, y + h)), ((x, y + h), (x + w, y + h)), ((x, y), (x, y + h))):
            self.line(p, q, color, dashed)
        self.d.rectangle([x * S, y * S, (x + 30) * S, (y + 30) * S], fill=color)
        self.glyph(GLYPH[kind], x + 15, y + 15, 9, WHITE)
        self.text((x + 40, y + 8), label, 14, bold=True, color=color)

    def glyph(self, kind, cx, cy, r, color):
        d, k = self.d, S
        if kind == "cloud":
            for dx, dy, rr in ((-0.4, 0.15, 0.55), (0.35, 0.1, 0.6), (0, -0.25, 0.65)):
                d.ellipse([(cx + dx * r - rr * r) * k, (cy + dy * r - rr * r) * k, (cx + dx * r + rr * r) * k,
                           (cy + dy * r + rr * r) * k], fill=color)
        elif kind == "web":
            d.polygon([(cx * k, (cy - r) * k), ((cx + r) * k, (cy + 0.8 * r) * k), ((cx - r) * k, (cy + 0.8 * r) * k)], fill=color)
        elif kind == "compute":
            d.rectangle([(cx - 0.7 * r) * k, (cy - 0.7 * r) * k, (cx + 0.7 * r) * k, (cy + 0.7 * r) * k], outline=color, width=2 * k)
            for t in (-0.25, 0.25):
                d.line([(cx - r) * k, (cy + t * r) * k, (cx - 0.7 * r) * k, (cy + t * r) * k], fill=color, width=2 * k)
                d.line([(cx + 0.7 * r) * k, (cy + t * r) * k, (cx + r) * k, (cy + t * r) * k], fill=color, width=2 * k)
        elif kind == "meta":
            d.ellipse([(cx - r) * k, (cy - 0.55 * r) * k, (cx - 0.05 * r) * k, (cy + 0.55 * r) * k], outline=color, width=2 * k)
            d.ellipse([(cx + 0.05 * r) * k, (cy - 0.55 * r) * k, (cx + r) * k, (cy + 0.55 * r) * k], outline=color, width=2 * k)
        elif kind == "hpc":
            for i in range(3):
                yy = cy - 0.7 * r + i * 0.6 * r
                d.rectangle([(cx - r) * k, yy * k, (cx + r) * k, (yy + 0.4 * r) * k], outline=color, width=2 * k)
        elif kind == "data":
            d.ellipse([(cx - 0.8 * r) * k, (cy - r) * k, (cx + 0.8 * r) * k, (cy - 0.4 * r) * k], outline=color, width=2 * k)
            d.line([(cx - 0.8 * r) * k, (cy - 0.7 * r) * k, (cx - 0.8 * r) * k, (cy + 0.7 * r) * k], fill=color, width=2 * k)
            d.line([(cx + 0.8 * r) * k, (cy - 0.7 * r) * k, (cx + 0.8 * r) * k, (cy + 0.7 * r) * k], fill=color, width=2 * k)
            d.arc([(cx - 0.8 * r) * k, (cy + 0.4 * r) * k, (cx + 0.8 * r) * k, (cy + r) * k], 0, 180, fill=color, width=2 * k)
        elif kind == "security":
            d.polygon([(cx * k, (cy - r) * k), ((cx + 0.8 * r) * k, (cy - 0.5 * r) * k), ((cx + 0.6 * r) * k, (cy + 0.5 * r) * k),
                       (cx * k, (cy + r) * k), ((cx - 0.6 * r) * k, (cy + 0.5 * r) * k), ((cx - 0.8 * r) * k, (cy - 0.5 * r) * k)],
                      outline=color, width=2 * k)
        elif kind == "client":
            d.rounded_rectangle([(cx - 0.6 * r) * k, (cy - r) * k, (cx + 0.6 * r) * k, (cy + r) * k], 3 * k, outline=color, width=2 * k)
            d.line([(cx - 0.2 * r) * k, (cy + 0.7 * r) * k, (cx + 0.2 * r) * k, (cy + 0.7 * r) * k], fill=color, width=2 * k)

    def service(self, cx, y, kind, name, note=None, size=56):
        x = cx - size / 2
        self.d.rounded_rectangle([x * S, y * S, (x + size) * S, (y + size) * S], 6 * S, fill=KIND[kind])
        self.glyph(kind, cx, y + size / 2, size * 0.28, WHITE)
        self.text((cx, y + size + 8), name, 13, bold=True, anchor="ma")
        for i, line in enumerate((note or "").split("\n") if note else []):
            self.text((cx, y + size + 27 + i * 17), line, 12, color=MUTED, anchor="ma")
        lines = len(note.split("\n")) if note else 0
        return {"top": (cx, y), "icon": (cx, y + size), "bottom": (cx, y + size + 30 + lines * 17),
                "left": (x, y + size / 2), "right": (x + size, y + size / 2)}

    def badge(self, x, y, n):
        self.d.ellipse([(x - 11) * S, (y - 11) * S, (x + 11) * S, (y + 11) * S], fill=INK)
        self.text((x, y - 8), str(n), 12, bold=True, color=WHITE, anchor="ma")

    def wire(self, pts, step=None, label=None, dashed=False, color=INK, at=None, label_side=1, frac=0.5):
        for p, q in zip(pts, pts[1:]):
            self.line(p, q, color, dashed)
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        ang = math.atan2(y2 - y1, x2 - x1)
        self.d.polygon([(x2 * S, y2 * S)] + [((x2 - 11 * math.cos(ang + s)) * S, (y2 - 11 * math.sin(ang + s)) * S)
                                             for s in (0.42, -0.42)], fill=color)
        if step is None and not label:
            return
        i = at if at is not None else (len(pts) - 1) // 2
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        mx, my = ax + (bx - ax) * frac, ay + (by - ay) * frac
        if step is not None:
            self.badge(mx, my, step)
        if label:
            w = self.d.textlength(label, font=font(12)) / S
            if abs(by - ay) < abs(bx - ax):   # horizontal segment: label above
                lx, ly = mx - w / 2, my - 30 if label_side > 0 else my + 14
            else:                              # vertical segment: label to the side
                lx, ly = (mx + 16, my - 8) if label_side > 0 else (mx - 16 - w, my - 8)
            self.d.rectangle([(lx - 4) * S, (ly - 2) * S, (lx + w + 4) * S, (ly + 16) * S], fill=WHITE)
            self.text((lx, ly), label, 12, color=MUTED)

    def legend(self, x, y, items):
        self.text((x, y), "Legend", 13, bold=True)
        for i, (kind, label) in enumerate(items):
            yy = y + 24 + i * 24
            if kind == "dashed":
                self.line((x, yy + 9), (x + 22, yy + 9), dashed=True)
            elif kind == "step":
                self.badge(x + 10, yy + 9, 1)
            else:
                self.d.rounded_rectangle([x * S, yy * S, (x + 20) * S, (yy + 20) * S], 3 * S, fill=KIND[kind])
            self.text((x + 34, yy + 2), label, 12, color=MUTED)

    def save(self, name):
        self.img.resize((self.w, self.h), Image.LANCZOS).save(HERE / name, optimize=True)
        print("->", HERE / name)


# ------------------------------------------------------------------ 1. system architecture
c = Canvas(1700, 1000, "Stylewise system architecture",
           "Size-chart fit engine, measured body presets, styled views and a sizing assistant, built on Meta models")
c.group(30, 110, 180, 330, "device", "User device")
shopper = c.service(120, 175, "client", "Shopper", "browser or phone")
c.service(120, 315, "web", "Browser voice", "Whisper, Kokoro\n(on device)")

c.group(240, 110, 1430, 590, "cloud", "Public cloud")
c.group(265, 160, 320, 500, "vercel", "Vercel  ·  Next.js")
web = c.service(425, 215, "web", "Next.js app", "landing /   fitting room /try\nthree.js body viewer")
proxy = c.service(345, 430, "web", "Engine proxy", "/api/engine")
samr = c.service(505, 430, "web", "SAM route", "/api/sam")

c.group(615, 160, 700, 500, "render", "Render  ·  Docker  ·  FastAPI fit engine")
api = c.service(965, 205, "compute", "REST API", "catalogue · fit · presets · preview · scene · nisha")
fit = c.service(700, 365, "compute", "Fit engine", "ease, verdicts,\nstretch, uncertainty")
view = c.service(880, 365, "compute", "Styled views", "guide render, cache,\nsame-body ref, daily cap")
scene = c.service(1055, 365, "compute", "3D body scene", "MHR mesh, closest\npreset for measurements")
nisha = c.service(1230, 365, "security", "Nisha", "tool loop, PII scrubber,\nconsent gate")
charts = c.service(760, 545, "data", "Size charts", "27 cited garments")
presets = c.service(965, 545, "data", "Body presets", "210 MHR bodies")
cache = c.service(1170, 545, "data", "View cache", "pre-generated views")

c.group(1345, 160, 300, 500, "meta", "Meta models")
mi = c.service(1430, 215, "meta", "Muse Image", "muse-image-1.0")
mso = c.service(1565, 215, "meta", "Muse Spark Open", "open weights\nvia Baseten")
sam = c.service(1430, 430, "meta", "SAM 3.1", "segmentation")
ms = c.service(1565, 430, "meta", "Muse Spark", "Meta Model API\n(fallback)")

c.group(615, 745, 700, 170, "nscc", "NTU NSCC cluster  ·  offline, run once", dashed=True)
mhr = c.service(965, 790, "meta", "Meta MHR", "least-squares fit to size-chart girths")

c.wire([shopper["right"], (240, 203), (240, 243), web["left"]], step=1, at=1)
c.wire([web["bottom"], (425, 395), (345, 395), proxy["top"]])
c.wire([web["bottom"], (425, 395), (505, 395), samr["top"]])
c.wire([proxy["bottom"], (345, 630), (600, 630), (600, 233), api["left"]], step=2, label="HTTPS", at=2)
for svc in (fit, view, scene, nisha):
    c.wire([api["bottom"], (965, 330), (svc["top"][0], 330), svc["top"]])
for svc, data in ((fit, charts), (view, presets), (view, cache)):
    c.wire([svc["bottom"], (svc["bottom"][0], 515), (data["top"][0], 515), data["top"]], color=MUTED)
c.wire([view["right"], (935, 393), (935, 350), (1335, 350), (1335, 243), mi["left"]], step=3,
       label="guide + photo + fit notes", at=2, frac=0.62)
c.wire([nisha["right"], (1300, 393), (1300, 200), (1565, 200), mso["top"]], step=4, label="verdicts only (consent)", at=1,
       label_side=-1, frac=0.45)
c.wire([nisha["bottom"], (1230, 640), (1622, 640), (1622, 458), ms["right"]], dashed=True, label="fallback", at=1,
       frac=0.7, label_side=-1)
c.wire([samr["bottom"], (505, 680), (1430, 680), sam["bottom"]], step=5, label="product photo", at=1, frac=0.25,
       label_side=-1)
c.wire([mhr["top"], presets["bottom"]], label="210 presets", frac=0.55)
c.legend(40, 745, [("client", "Client"), ("web", "Web / edge"), ("compute", "Compute service"), ("data", "Data shipped with the engine"),
                   ("security", "Privacy-gated service"), ("meta", "Meta model"), ("dashed", "Fallback path"), ("step", "Request step")])
c.save("architecture.png")


# ------------------------------------------------------------------ 2-3. sequence diagrams
def sequence(name, title, subtitle, actors, messages, h):
    c = Canvas(1500, h, title, subtitle)
    xs = [190 + i * (1120 / (len(actors) - 1)) for i in range(len(actors))]
    top = 120
    for x, (kind, label, note) in zip(xs, actors):
        c.service(x, top, kind, label, note)
        c.line((x, top + 105), (x, h - 40), LINE, dashed=True)
    y = top + 150
    for i, (a, b, label, note, reply) in enumerate(messages, 1):
        xa, xb = xs[a], xs[b]
        if a == b:
            c.wire([(xa, y), (xa + 50, y), (xa + 50, y + 26), (xa + 4, y + 26)])
            c.badge(xa, y - 2, i)
            c.text((xa + 66, y - 2), label, 13, bold=True)
            if note:
                c.text((xa + 66, y + 17), note, 12, color=MUTED)
            y += 72
        else:
            c.wire([(xa, y), (xb, y)], dashed=reply)
            c.badge(xa + (14 if xb > xa else -14), y, i)
            mx = (xa + xb) / 2
            c.text((mx, y - 25), label, 13, bold=True, anchor="ma")
            if note:
                c.text((mx, y + 9), note, 12, color=MUTED, anchor="ma")
            y += 66
    c.save(name)


sequence("styled_view_flow.png", "How a styled view is made",
         "The measured fit decides the picture. Cached views are free; new ones count against a daily cap.",
         [("web", "Fitting room", "Next.js"), ("compute", "Fit engine", "FastAPI"), ("data", "View cache", "preview_cache"),
          ("meta", "Muse Image", "muse-image-1.0")],
         [(0, 1, "body preset, garment, size, view", None, False),
          (1, 1, "Evaluate fit", "bust, waist and hip verdicts from the size chart", False),
          (1, 2, "Look up cache key", "this body, garment, chart, photo and prompt", False),
          (2, 0, "Cached view (free)", None, True),
          (1, 1, "Render guide", "measured body + garment shell placed by measured ease", False),
          (1, 3, "guide + product photo + fit notes + body measurements", "+ same-body reference when drawing another size", False),
          (3, 1, "Faceless mannequin wearing the garment", None, True),
          (1, 0, "Styled view, stored for next time", None, True)], 860)

sequence("nisha_flow.png", "How Nisha answers",
         "Personal details never leave the server; body measurements reach the model only with consent.",
         [("client", "Shopper", "fitting room"), ("security", "Nisha service", "privacy gate"), ("meta", "Muse Spark Open", "via Baseten"),
          ("compute", "Fit engine", "tool")],
         [(0, 1, "\"Should I size up?\" + form context", None, False),
          (1, 1, "Scrub personal details", "names, emails, phones, addresses, links", False),
          (1, 2, "question + garment (+ body only with consent)", None, False),
          (2, 1, "tool call: evaluate_fit(garment, size)", None, True),
          (1, 3, "run the fit with the real body", None, False),
          (3, 1, "verdicts and caveats", None, True),
          (1, 2, "verdicts (no body numbers without consent)", None, False),
          (2, 0, "plain-words recommendation", None, True)], 830)
