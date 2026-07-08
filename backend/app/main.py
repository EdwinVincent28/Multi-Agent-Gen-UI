from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.routers import auth, generate 

from app.models.schemas import GenerationRequest, GenerationResponse
from app.swarm.graph import swarm_graph

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Autonomous Data Science Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(generate.router)

@app.get("/")
def read_root():
    return {"status": "Swarm Backend is Online"}