from fastapi import FastAPI

from api.router import router

app = FastAPI(title="LOGS AI OS Backend V0.1", version="0.1.0")
app.include_router(router)
