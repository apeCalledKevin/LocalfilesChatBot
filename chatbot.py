# vector database chromadb, langchain framework for building llm applications

from pathlib import Path
from typing import Any

from pypdf import PdfReader

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager

# All paths are relative to this file, so the app works no matter which folder it is started from
BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs" # Source docs folder
EXAMPLE_DOCS_DIR = BASE_DIR / "example_docs" # Fallback if DOCS_DIR is missing or empty (lets you test right after cloning)
DB_DIR = BASE_DIR / "db" # Persisted Chroma DB folder
SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf"}
CHAT_MODEL = "qwen3.5:4b" # Ollama chat model
EMBED_MODEL = "nomic-embed-text" # Ollama embedding model
RETRIEVAL_K = 5 # Chunks retrieved per query. Increase if answers feel incomplete
CHUNK_SIZE = 1000 # Max chars per chunk. Try 500 for tighter answers, 2000 for more context
CHUNK_OVERLAP = 200 # Chars shared between chunks. Prevents key ideas from being split.
SYSTEM_PROMPT = (
    "Du bist ein Assistent für technische Dokumentation. "
    "Beantworte die Frage ausschließlich anhand des folgenden Kontexts. "
    "Wenn die Antwort nicht im Kontext steht, sag ehrlich, dass du es nicht weißt. "
    "Antworte auf Deutsch und knapp."
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # runs once at server start
    vector_store = get_vectorstore()
    app.state.agent = build_agent(vector_store)
    yield

app = FastAPI(lifespan=lifespan)

def resolve_docs_dir():
    # Use DOCS_DIR if it contains supported files, otherwise fall back to the bundled example docs
    if DOCS_DIR.is_dir() and any(p.suffix.lower() in SUPPORTED_SUFFIXES for p in DOCS_DIR.rglob("*")):
        return DOCS_DIR
    print(f"No documents found in {DOCS_DIR}, using example documents from {EXAMPLE_DOCS_DIR}.")
    return EXAMPLE_DOCS_DIR


def load_documents():
    docs = []
    docs_dir = resolve_docs_dir()

    # Walk all files under the docs folder
    for path in docs_dir.rglob("*"):
        # Source shown to the user, e.g. "docs/ESP.md" (relative to the project folder)
        source = path.relative_to(BASE_DIR).as_posix()

        # Load markdown/text files
        if path.suffix.lower() in {".md", ".txt"}:
            docs.append(Document(
                page_content=path.read_text(encoding="utf-8", errors="ignore"),
                metadata={"source": source}
            ))

        # Extract text from PDFs
        elif path.suffix.lower() == ".pdf":
            text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
            docs.append(Document(
                page_content=text,
                metadata={"source": source}
            ))

    # Fail early with a clear message instead of a cryptic Chroma error on empty input
    if not any(doc.page_content.strip() for doc in docs):
        raise RuntimeError(
            f"No readable .md, .txt or .pdf documents found in {docs_dir}. "
            f"Add files to {DOCS_DIR} or check that {EXAMPLE_DOCS_DIR} exists."
        )

    return docs


def get_vectorstore():
    # Embeddings for indexing/search
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)

    # Reuse existing DB if present
    # Delete ./db to force a re-index after adding/changing documents OR after changing CHUNK_SIZE, CHUNK_OVERLAP, or EMBED_MODEL.
    if DB_DIR.exists():
        print(f"Reusing existing data {DB_DIR} for embeddings...")
        return Chroma(persist_directory=str(DB_DIR), embedding_function=embeddings)

    docs = load_documents()
    print(f"Loaded {len(docs)} documents. Splitting...")

    # Split docs into chunks
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    ).split_documents(docs)
    print(f"Created {len(chunks)} chunks. Building vectorstore...")

    # Build and persist Chroma DB
    vs = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(DB_DIR),
    )
    print(f"Vectorstore built with {len(chunks)} chunks.")
    return vs


# Agent has the standard messages field, plus an extra context field where we'll store retrieved documents
# State = { "messages": [], "context": [] }
class State(AgentState):
    context: list[Document]


class RetrieveDocumentsMiddleware(AgentMiddleware[State]):
    state_schema = State

    def __init__(self, vector_store):
        self.vector_store = vector_store

    def before_model(self, state: State) -> dict[str, Any] | None:
        # Latest user message
        msg = state["messages"][-1]
        # Query text
        query = str(msg.content)
        
        # Retrieve top matching chunks
        docs = self.vector_store.similarity_search(query, k=RETRIEVAL_K)
        print(f"Found {len(docs)} chunks. Adding to context and sending it to the model...")

        # Format retrieved context
        context = "\n\n".join(
            f"Source: {doc.metadata.get('source', 'unknown')}\n{doc.page_content}"
            for doc in docs
        )

        # Prepend a system message with the context.
        # The user's original message stays intact in the history.
        system_message = SystemMessage(
            content=f"{SYSTEM_PROMPT}\n\nContext:\n{context}"
        )

        # State = {"messages": [system_msg], "context": docs}
        return {
            "messages": [system_message],
            "context": docs,
        } 


def build_agent(vector_store):
    model = ChatOllama(model=CHAT_MODEL, temperature=0)

    # Agent with retrieval middleware
    return create_agent(
        model=model,
        tools=[], # No tools yet as retrieval happens in middleware
        middleware=[RetrieveDocumentsMiddleware(vector_store)],
        state_schema=State, # Use this schema for state. 
    )

class Question(BaseModel):              # erwartete Eingabe: {"frage": "..."}
    question: str

class Answer(BaseModel):
    question: str
    answer: str
    docs: list[str]

@app.post("/ask", response_model=Answer)
def ask(f: Question):
    agent = app.state.agent
    result = agent.invoke({
        "messages": [{"role": "user", "content": f.question}],
        "context": [],
    });

    # Unique source files list
    seen = set()
    for doc in result.get("context", []):
        source = doc.metadata.get("source", "unknown")
        if source not in seen:
            #print("-", source)
            seen.add(source)
    
    return Answer(question=f.question, answer=result['messages'][-1].content, docs=seen)

def main():
    # Build retrieval backend and agent
    vector_store = get_vectorstore()
    agent = build_agent(vector_store)

    print("\nReady! Ask questions about your documents.\n")

    while True:
        # Read user input
        question = input("You: ").strip()
        if not question or question.lower() == "exit":
            break

        # Run the agent
        # State = { "messages": [user msg], "context": [] }
        result = agent.invoke({
            "messages": [{"role": "user", "content": question}],
            "context": [],
        })

        # After the agent finishes
        # State = { "messages": [user msg, system msg, ai answer], "context": [doc1, doc2, ...] }
        # Print answer from agent
        print(f"\nAnswer: {result['messages'][-1].content}\n")

        # Print unique source files
        print("Sources:")
        seen = set()
        for doc in result.get("context", []):
            source = doc.metadata.get("source", "unknown")
            if source not in seen:
                print("-", source)
                seen.add(source)
        print()
        


if __name__ == "__main__":
    main()