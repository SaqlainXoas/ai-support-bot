#data/ingest.py

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

def ingest_documents():
    # Load PDFs
    loader = DirectoryLoader("data/knowledge", glob="**/*.pdf", loader_cls=PyPDFLoader)
    docs = loader.load()
    
    # Split into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(docs)
    
    # Create SQLAlchemy engine
    connection_string = os.getenv("DB_URL", "postgresql://admin:admin@localhost:5432/support_db")
    engine = create_engine(connection_string)
    
    # Store in pgVector
    PGVector.from_documents(
        documents=chunks,
        embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
        collection_name="support_knowledge",
        connection=engine  
    )

if __name__ == "__main__":
    ingest_documents()