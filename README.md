# 🧠 MyDrift

![MyDrift UI Preview](image/preview.png)

**MyDrift** is a conversation-centric personal memory system that combines a **Streamlit** frontend with a **FastAPI** backend, enabling you to import conversation records and perform natural language queries with ease.

---

## ✅ Prerequisites

- [Ollama](https://ollama.com/)
- [Docker](https://www.docker.com/)

---

## 🚀 Getting Started

### 1. (Optional) Install Pre-commit Hooks

Install code formatting and linting tools:

```bash
pre-commit install
```

### 2. Build Docker Images

```bash
make build
```

### 3. Start All Services

```bash
make up
```

This launches:
- 🚀 **FastAPI** backend – chat query & data upload APIs
- 💻 **Streamlit** frontend – chat interface, data viewer, and import tool
- 📦 **Qdrant** – vector indexing and search

---

## 🧩 Features Overview

### 💬 Chat Interface

- Ask questions using natural language
- Streamed response display
- Basic chat history support

### 📤 Data Import

- Upload multiple Messenger JSON files
- Backend indexing with real-time progress

### 📚 Memory Data Viewer

- Paginated browsing of conversation chunks
- View start/end timestamps, senders, and full text

---

## 📂 JSON Format Requirements

Each uploaded JSON file should follow this structure (example from [Facebook Messenger Export](https://www.facebook.com/help/messenger-app/713635396288741)):

```json
{
  "start_timestamp": 1690000000000,
  "end_timestamp": 1690000123456,
  "senders": ["Alice", "Bob"],
  "text": "This is the content of a conversation."
}
```

---

## 📎 Common Commands

| Command      | Description                        |
|--------------|------------------------------------|
| `make build` | Build all Docker images            |
| `make up`    | Start the full stack via Docker    |

---

## 📌 Future Plans

- [ ] Import support for note formats like Markdown

---

## 👨‍💻 Author

This is a personal side project – contributions and feedback are welcome!
