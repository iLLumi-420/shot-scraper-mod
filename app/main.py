from fastapi import FastAPI
from app.routers import screenshot


app = FastAPI(root_path="/api")

app.include_router(screenshot.router, prefix="/screenshot")


    



