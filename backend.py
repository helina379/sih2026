from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Flash Flood Prediction System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/api")
def api_root():
    return {"message": "Flash Flood Prediction API"}

@app.get("/api/predict")
def predict(lat: float, lon: float):
    return {
        "latitude": lat,
        "longitude": lon,
        "risk": "HIGH",
        "risk_score": 82,
        "rainfall": 78,
        "river_level": 4.8,
        "soil_moisture": 82
    }

# Serve built frontend if present
if os.path.isdir("dist"):
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")
