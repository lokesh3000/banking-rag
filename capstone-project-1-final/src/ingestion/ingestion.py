from dotenv import load_dotenv
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Adjusted import path as per your structure
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.db import get_vector_store

load_dotenv()
PG_CONNECTION = os.getenv("PG_CONNECTION_STRING")


def ingest_file(file_path: str):
    """Ingest a PDF file and save it in vector database"""

    print(f"Processing document: {file_path}")

    # 1. Load PDF
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    print("Pages:", len(docs))

    # 2. Metadata enrichment
    for doc in docs:
        doc.metadata.update({
            "source": file_path,
            "document_extension": "pdf",
            "page": doc.metadata.get("page"),
            "category": "retail_banking",  # kept from your original code
            "last_updated": os.path.getmtime(file_path)
        })

    # 3. Chunking
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=512,
        chunk_overlap=100
    )

    chunks = splitter.split_documents(docs)
    print("Total Chunks:", len(chunks))

    # 4 + 5. Embeddings + Store
    vector_store = get_vector_store(collection_name="retail_banking")

    vector_store.add_documents(chunks)

    print("Ingestion completed successfully!")


if __name__ == "__main__":
    test_file = "Retail_banking.pdf"

    if os.path.exists(test_file):
        ingest_file(test_file)
    else:
        print(f"Test file {test_file} not found.")