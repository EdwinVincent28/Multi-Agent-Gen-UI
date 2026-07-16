import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

load_dotenv()

qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
client = QdrantClient(url=qdrant_url)
collection_name = "dashboard_memory"

embeddings = FastEmbedEmbeddings()

def initialize_qdrant():
    """Ensure the collection exists before we try to use it."""
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

initialize_qdrant()

def save_dashboard_to_memory(session_id: str, insights: str, ui_code: str):
    """Embeds the insights and saves the generated code to Qdrant."""
    vector = embeddings.embed_query(insights)
    
    client.upsert(
        collection_name=collection_name,
        points=[
            PointStruct(
                id=session_id, 
                vector=vector,
                payload={"ui_code": ui_code, "insights": insights}
            )
        ]
    )
    print(f"--- DASHBOARD {session_id} SAVED TO DOCKERIZED SEMANTIC MEMORY ---")

def retrieve_similar_dashboard(user_prompt: str) -> str | None:
    """Finds a previously generated dashboard similar to the current prompt."""
    query_vector = embeddings.embed_query(user_prompt)
    
    response = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=1 
    )
    
    hits = response.points
    
    if hits:
        best_match = hits[0]
        print(f"--- QDRANT MATCH SCORE: {best_match.score} ---")
        
        if best_match.score > 0.40: 
            print("--- RETRIEVED RELEVANT UI FROM DOCKERIZED SEMANTIC MEMORY ---")
            return best_match.payload.get("ui_code")
            
    return None