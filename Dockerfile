# Stylewise fit engine (FastAPI). Built from the repo root because the engine reads fixtures/ and
# fit-engine/scripts at runtime. No torch, no GPU: presets are pre-fitted meshes.
FROM python:3.12-slim
WORKDIR /app
# live try-ons for visitors, capped per day (set PREVIEW_CACHE_ONLY=1 instead to serve only cached looks)
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PREVIEW_DAILY_LIMIT=15
COPY fit-engine/pyproject.toml fit-engine/pyproject.toml
COPY fit-engine/stylewise_fit fit-engine/stylewise_fit
RUN pip install --no-cache-dir "./fit-engine[api]"
COPY fit-engine/scripts fit-engine/scripts
COPY fit-engine/experiments/results fit-engine/experiments/results
COPY fixtures fixtures
# reinstall so the installed package resolves data next to the copied tree
RUN pip install --no-cache-dir --no-deps -e ./fit-engine
EXPOSE 8000
CMD ["sh", "-c", "uvicorn stylewise_fit.server:app --app-dir fit-engine --host 0.0.0.0 --port ${PORT:-8000}"]
