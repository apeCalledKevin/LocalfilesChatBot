# 📚 Local RAG Chatbot for Technical Documentation

A fully local question-answering assistant for your own documents, built with **LangChain**, **Ollama** and **ChromaDB**, and served through a **FastAPI** REST endpoint.

Drop Markdown, text or PDF files into a folder, ask questions in natural language and get answers grounded in those documents, together with the source files they came from. No cloud API, no API key, no costs: everything runs on your own machine.

---

## ✨ Features

- **Retrieval-Augmented Generation (RAG):** answers are based only on your documents, not on the model's general knowledge
- **Runs 100 % locally** via Ollama (chat model + embedding model)
- **Supports `.md`, `.txt` and `.pdf`** files
- **Persistent vector store** (ChromaDB): documents are indexed once and reused on later starts
- **Two interfaces:**
  - interactive **CLI** that also lists the source files used for each answer
  - **REST API** with FastAPI, including automatic Swagger documentation
- **Middleware-based retrieval** using the LangChain v1 agent API

---

## 🏗️ Architecture

```
            ┌──────────────┐
 docs/ ───► │  Load & split │  RecursiveCharacterTextSplitter
            └──────┬───────┘
                   ▼
            ┌──────────────┐
            │   Embedding   │  nomic-embed-text (Ollama)
            └──────┬───────┘
                   ▼
            ┌──────────────┐
            │   ChromaDB    │  persisted in ./db
            └──────┬───────┘
                   │  similarity search (top-k chunks)
                   ▼
 Question ► ┌─────────────────────────────┐
            │ RetrieveDocumentsMiddleware │  injects the chunks as a
            │ (before_model hook)         │  system message with context
            └──────┬──────────────────────┘
                   ▼
            ┌──────────────┐
            │   Chat LLM    │  qwen3.5:4b (Ollama)
            └──────┬───────┘
                   ▼
                Answer (+ sources)
```

**How a request works:**

1. **Indexing (on first start):** all files in `docs/` are loaded, split into overlapping chunks, converted into vectors and stored in ChromaDB.
2. **Retrieval:** for each question, the most similar chunks are found via vector similarity search.
3. **Augmentation:** a custom `AgentMiddleware` hooks in *before* the model call and adds the retrieved chunks to the prompt as a system message.
4. **Generation:** the local LLM answers based only on that context. If the answer isn't in the documents, it is instructed to say so.

Doing retrieval in middleware instead of as an agent tool means it **always** runs exactly once per question, so behaviour is predictable even with small local models that are unreliable at tool calling.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| LLM framework | LangChain v1 (`create_agent`, `AgentMiddleware`) |
| Local models | Ollama: `qwen3.5:4b` (chat), `nomic-embed-text` (embeddings) |
| Vector database | ChromaDB (`langchain-chroma`) |
| Document parsing | `pypdf`, plain-text loading |
| API | FastAPI, Pydantic, Uvicorn |
| Language | Python 3.12 |

---

## 🚀 Getting Started

### 1. Install Ollama and pull the models

Install Ollama from [ollama.com](https://ollama.com), then:

```bash
ollama pull qwen3.5:4b
ollama pull nomic-embed-text
```

Make sure Ollama is running (tray icon on Windows).

### 2. Install the Python dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Add your documents

Put your `.md`, `.txt` or `.pdf` files into the `docs/` folder.

### 4a. Run as CLI

```bash
python chatbot.py
```

```
Ready! Ask questions about your documents.

You: Why was the Hailo AI HAT chosen instead of the Google Coral?

Answer: ...

Sources:
- docs/Object_detection.md
```

Type `exit` or press Enter on an empty line to quit.

### 4b. Run as REST API

```bash
uvicorn chatbot:app --reload
```

Open **http://127.0.0.1:8000/docs** for the interactive Swagger UI, or call the endpoint directly:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How is the camera connected to the Raspberry Pi?"}'
```

Response:

```json
{
  "question": "How is the camera connected to the Raspberry Pi?",
  "answer": "..."
}
```

The vector store and the agent are created **once at server start** via FastAPI's lifespan handler, not on every request.

---

## ⚙️ Configuration

All settings are constants at the top of `chatbot.py`:

| Setting | Default | Description |
|---|---|---|
| `DOCS_DIR` | `./docs` | Folder with source documents |
| `DB_DIR` | `./db` | Folder for the persisted ChromaDB |
| `CHAT_MODEL` | `qwen3.5:4b` | Ollama chat model |
| `EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `RETRIEVAL_K` | `5` | Number of chunks retrieved per question |
| `CHUNK_SIZE` | `1000` | Max characters per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |

> ⚠️ **Re-indexing:** the database in `./db` is reused on every start. Delete the `db/` folder after adding or changing documents, or after changing `CHUNK_SIZE`, `CHUNK_OVERLAP` or `EMBED_MODEL`.

---

## 📂 Project Structure

```
.
├── chatbot.py          # indexing, RAG agent, CLI and FastAPI app
├── requirements.txt
├── docs/               # your source documents (not tracked in git)
└── db/                 # persisted ChromaDB (generated, not tracked in git)
```

---

## 🗺️ Possible Next Steps

- Return the source documents in the API response as well
- Simple web frontend (e.g. React) for the chat
- Containerize with Docker
- Automatic re-indexing when files in `docs/` change
- Conversation memory for follow-up questions
