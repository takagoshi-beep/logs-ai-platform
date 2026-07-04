import sys
from pathlib import Path

# `capability/` lives at the repository root, but this app is run with
# `backend/` as the working directory (see README: `cd backend && uvicorn
# main:app`). Append the repo root to sys.path (not insert at position 0)
# so top-level packages like `capability` become importable without
# shadowing backend/'s own same-named packages (business, services, etc.).
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import router
from api.capability_router import router as capability_router

app = FastAPI(title="LOGS AI OS Backend V0.1", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(capability_router)