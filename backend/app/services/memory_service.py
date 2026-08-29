import os
import uuid
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from loguru import logger

load_dotenv()

qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
client = QdrantClient(url=qdrant_url)

embeddings = FastEmbedEmbeddings()

EMBEDDING_SIZE = 384

TWITCH_COLLECTION = "twitch_live_context"


def initialize_qdrant():
    """Ensure the Twitch RAG collection exists before we try to use it."""
    if not client.collection_exists(TWITCH_COLLECTION):
        client.create_collection(
            collection_name=TWITCH_COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_SIZE, distance=Distance.COSINE),
        )

initialize_qdrant()


def store_twitch_context_batch(
    session_id: str,
    channel: str,
    window_start: float,
    window_end: float,
    stats_text: str,
    chat_text: str = None,
):
    """
    Embeds and stores one time-windowed batch of Twitch context for a
    live session
    """
    points = []

    stats_vector = embeddings.embed_query(stats_text)
    points.append(
        PointStruct(
            id=str(uuid.uuid4()),
            vector=stats_vector,
            payload={
                "session_id": session_id,
                "channel": channel,
                "type": "stats",
                "window_start": window_start,
                "window_end": window_end,
                "text": stats_text,
            },
        )
    )

    if chat_text:
        chat_vector = embeddings.embed_query(chat_text)
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=chat_vector,
                payload={
                    "session_id": session_id,
                    "channel": channel,
                    "type": "chat",
                    "window_start": window_start,
                    "window_end": window_end,
                    "text": chat_text,
                },
            )
        )

    client.upsert(collection_name=TWITCH_COLLECTION, points=points)
    logger.info(
        f"--- STORED TWITCH CONTEXT BATCH for session {session_id} "
        f"({len(points)} point(s), window {window_start:.0f}-{window_end:.0f}) ---"
    )


def retrieve_twitch_context(session_id: str, question: str, limit: int = 5) -> list[dict]:
    """
    Retrieves the most relevant stored context batches for a question,
    scoped to ONE session only via a Qdrant filter
    """
    query_vector = embeddings.embed_query(question)

    response = client.query_points(
        collection_name=TWITCH_COLLECTION,
        query=query_vector,
        query_filter=Filter(
            must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))]
        ),
        limit=limit,
    )

    return [
        {
            "type": hit.payload.get("type"),
            "window_start": hit.payload.get("window_start"),
            "window_end": hit.payload.get("window_end"),
            "text": hit.payload.get("text"),
            "score": hit.score,
        }
        for hit in response.points
    ]