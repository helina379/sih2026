from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Flash Flood Prediction System"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/")
def home():
    return {
        "message": "Flash Flood Prediction API"
    }


@app.get("/predict")
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


