# server/database.py
from sqlalchemy import create_engine
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
import os

def get_sync_engine():
    """Get a synchronous SQLAlchemy engine"""
    DB_URL = os.getenv("DB_URL", "postgresql://admin:admin@localhost:5432/support_db")
    return create_engine(DB_URL)

def get_vector_store():
    """Get a synchronous PGVector instance"""
    engine = get_sync_engine()
    return PGVector(
        connection=engine,
        embeddings=OpenAIEmbeddings(model="text-embedding-3-small"),
        collection_name="support_knowledge"
    )