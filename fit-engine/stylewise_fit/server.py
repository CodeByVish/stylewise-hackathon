"""HTTP wrapper around fit.evaluate. Run: uvicorn stylewise_fit.server:app --port 8000"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from pydantic import BaseModel

from .catalogue import catalogue, garment_input
from .preview import PHOTOS
from .fit import evaluate
from .nisha import NishaReply, NishaRequest, chat, muse_configured
from .schemas import CONTRACT_VERSION, BodyInput, FitReport, FitRequest, Preferences

app = FastAPI(title="Stylewise fit engine", version=__version__)
# Next.js dev server calls this directly; tighten origins before deploying
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"],
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health() -> dict:
    return {"ok": True, "engine_version": __version__, "contract_version": CONTRACT_VERSION,
            "muse": muse_configured()}


class OutfitPiece(BaseModel):
    garment_id: str
    size: str


class OutfitRequest(BaseModel):
    body: BodyInput
    items: list[OutfitPiece]
    preferences: Preferences = Preferences()


class PieceResult(BaseModel):
    garment_id: str
    size: str
    report: FitReport | None = None
    error: str | None = None  # e.g. no sourced measurements for this item


# Keep questionable examples available to engine tests, but out of the demo catalogue.
# The legacy green kurta uses a men's photo with a women's chart; the ivory set's
# guide depicts a different cut. Items without photos cannot be previewed faithfully.
HIDDEN = {"green-kurta", "ivory-set", "ivory-kurta", "gold-trousers", "navy-bottom",
          "black-satin-dress", "uniqlo-crew-tee", "uniqlo-dress-E487286", "reference-dress"}


@app.get("/catalogue")
def list_catalogue() -> list[dict]:
    """Catalogue items and whether they have sourced garment cm (only those can be fitted)."""
    return [{"garment_id": gid, "name": g["name"], "category": g["category"], "fabric": g["fabric"],
             "sizes": list(g["sizes"]), "fittable": bool(g["sizes"]), "for": g.get("for", "unisex"),
             "photo": (PHOTOS / f"{gid}.jpg").exists()}
            for gid, g in catalogue().items() if gid not in HIDDEN]


@app.post("/fit/outfit", response_model=list[PieceResult])
def fit_outfit(req: OutfitRequest) -> list[PieceResult]:
    """One FitReport per piece of a combination, all against the same body."""
    out = []
    for p in req.items:
        try:
            g = garment_input(p.garment_id, p.size)
        except ValueError as e:
            out.append(PieceResult(garment_id=p.garment_id, size=p.size, error=str(e)))
            continue
        report = evaluate(FitRequest(body=req.body, garment=g, preferences=req.preferences))
        out.append(PieceResult(garment_id=p.garment_id, size=p.size, report=report))
    return out


@app.post("/nisha/chat", response_model=NishaReply)
def nisha_chat(req: NishaRequest) -> NishaReply:
    # sync def: FastAPI runs it in a thread, so the blocking Muse call does not stall the loop
    return chat(req)


@app.post("/fit/evaluate", response_model=FitReport)
def fit_evaluate(req: FitRequest) -> FitReport:
    # invalid requests get FastAPI's 422 with pydantic's field errors
    return evaluate(req)


class PreviewRequest(BaseModel):
    body: BodyInput  # a preset body (silhouette + usual size + sex + height)
    garment_id: str
    size: str
    style: str = "mannequin"  # or "illustration"
    view: str = "front"  # front, side or back
    preferences: Preferences = Preferences()
    pair_garment_id: str | None = None  # style a top with a bottom (or vice versa) in the picture
    pair_size: str | None = None


@app.post("/preview/photo")
def preview_photo(req: PreviewRequest) -> dict:
    """A visual impression (faceless mannequin by default) next to the measured FitReport.
    The picture never decides fit: the report does."""
    from fastapi import HTTPException
    import base64

    from .preview import CAPTION, fit_notes, preview

    if req.body.source != "preset" or req.body.preset is None:
        raise HTTPException(status_code=422, detail="Preview needs a preset body (silhouette + usual size).")
    try:
        garment = garment_input(req.garment_id, req.size)
        report = evaluate(FitRequest(body=req.body, garment=garment, preferences=req.preferences))
        p = req.body.preset
        png = preview(p.shape, p.usual_size, p.sex, req.body.height_cm, req.garment_id, req.size, req.style,
                      fit_notes(report), req.view,
                      (req.pair_garment_id, req.pair_size) if req.pair_garment_id and req.pair_size else None)  # the picture is told the measured fit, region by region
    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:  # no key (503) or the image model refused / failed (502)
        raise HTTPException(status_code=503 if "no Meta API key" in str(error) else 502, detail=str(error)) from error
    return {"image": "data:image/png;base64," + base64.b64encode(png).decode(), "style": req.style, "view": req.view,
            "caption": CAPTION, "report": report.model_dump()}


@app.post("/viewer/scene")
def viewer_scene(req: OutfitRequest):
    from fastapi import HTTPException, Response
    from .viewer import scene_bytes
    if len(req.items) > 4:
        raise HTTPException(status_code=422, detail="Use at most four outfit pieces")
    try:
        glb = scene_bytes(req.model_dump_json())
        return Response(glb, media_type="model/gltf-binary")
    except (ValueError, KeyError, FileNotFoundError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
