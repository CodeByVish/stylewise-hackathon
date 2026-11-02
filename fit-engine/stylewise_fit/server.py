"""HTTP wrapper around fit.evaluate. Run: uvicorn stylewise_fit.server:app --port 8000"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .fit import evaluate
from .schemas import CONTRACT_VERSION, FitReport, FitRequest

app = FastAPI(title="Stylewise fit engine", version=__version__)
# Next.js dev server calls this directly; tighten origins before deploying
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"],
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health() -> dict:
    return {"ok": True, "engine_version": __version__, "contract_version": CONTRACT_VERSION}


@app.post("/fit/evaluate", response_model=FitReport)
def fit_evaluate(req: FitRequest) -> FitReport:
    # invalid requests get FastAPI's 422 with pydantic's field errors
    return evaluate(req)
