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

### 3. Add your documents (optional)

Put your `.md`, `.txt` or `.pdf` files into the `docs/` folder.

**Just want to try it out?** Skip this step. If `docs/` is missing or empty, the chatbot automatically uses the bundled example documents in [`example_docs/`](example_docs/) (a fictional Raspberry Pi 5 object-detection project, written in German). Example questions:

- *Warum wurde das Hailo AI HAT statt des Google Coral gewählt?*
- *Wie wird die Kamera an den Raspberry Pi angeschlossen?*
- *Was tun, wenn die Bildrate unter 15 FPS liegt?*
- *Welches Netzteil wird benötigt und warum?*

> When you switch from the example docs to your own documents, delete the `db/` folder so everything is re-indexed.

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

Open **http://127.0.0.1:8000/docs** for the interactive Swagger UI, or call the endpoint directly
For the interactive Swagger UI as an example expand the "POST /ask" in default and on the right "Try it out". Edit the string in question and execute:

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
| `EXAMPLE_DOCS_DIR` | `./example_docs` | Fallback used when `DOCS_DIR` is missing or empty |
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
├── example_docs/       # bundled sample documents for a quick test
├── docs/               # your source documents (not tracked in git)
└── db/                 # persisted ChromaDB (generated, not tracked in git)
```

---

## 🗺️ Possible Next Steps

- Simple web frontend (e.g. React) for the chat
- Containerize with Docker
- Automatic re-indexing when files in `docs/` change
- Conversation memory for follow-up questions

---

## 🙏 Acknowledgements

The retrieval core (document loading, ChromaDB indexing and the retrieval middleware) is based on the freeCodeCamp tutorial
[Build a Private RAG Q&A AI Agent for Your Documents Using LangChain](https://www.freecodecamp.org/news/build-a-private-rag-qa-ai-agent-for-your-documents-using-langchain/).

Parts of the code, the README and the example documents were created with the help of [Claude](https://claude.ai) (Anthropic).

My own additions on top of it:
- REST API with FastAPI, including Pydantic request/response models
- Agent and vector store initialised once at server start via FastAPI's lifespan handler
