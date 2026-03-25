# Dodge AI — Order to Cash Graph System

A context graph system with an LLM-powered query interface for SAP Order-to-Cash data.

**Live Demo:** https://dodgeassignment.vercel.app  
**Backend API:** https://dodge-ai-assignment-production.up.railway.app

---

## Architecture

### Tech Stack
| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | FastAPI + Python | Lightweight, async, auto docs |
| Database | SQLite | Zero setup, LLM generates SQL against it |
| Graph | NetworkX | In-memory graph built from SQLite at startup |
| LLM | Groq (llama-3.3-70b) | Free tier, fast inference |
| Frontend | React + Vite | Fast build tooling |
| Graph UI | Cytoscape.js | Purpose-built for network graphs |
| Backend hosting | Railway | Supports Python, free tier |
| Frontend hosting | Vercel | Best for React/Vite, free |

### Data Flow
```
JSONL files → SQLite (ingest.py) → NetworkX graph (graph.py)
                                          ↓
User question → Guardrail check → LLM generates SQL
                                          ↓
                              Execute SQL on SQLite
                                          ↓
                          LLM formats natural language answer
                                          ↓
                        Highlight referenced nodes in graph
```

---

## Graph Modelling

### Nodes (8 entity types)
- **SalesOrder** — customer purchase orders
- **SalesOrderItem** — line items within orders
- **BillingDocument** — invoices raised against orders
- **JournalEntry** — accounting entries linked to billing
- **Payment** — payments received
- **Customer** — business partners
- **Product** — materials/products sold
- **Plant** — warehouses and fulfillment centers

### Edges (relationships)
- Customer → SalesOrder (PLACED_ORDER)
- SalesOrder → SalesOrderItem (HAS_ITEM)
- SalesOrderItem → Product (IS_PRODUCT)
- SalesOrderItem → Plant (FULFILLED_BY)
- Customer → BillingDocument (HAS_BILLING)
- BillingDocument → JournalEntry (HAS_JOURNAL_ENTRY)
- BillingDocument → Payment (PAID_BY)

---

## LLM Prompting Strategy

Two-stage LLM pipeline:

**Stage 1 — SQL Generation**
- System prompt includes full DB schema with table names, columns, and relationships
- LLM instructed to return only valid SQLite SQL, no markdown
- Model: llama-3.3-70b-versatile via Groq

**Stage 2 — Answer Formatting**
- LLM receives the original question + SQL query + raw results
- Instructed to answer in 2-4 sentences strictly based on data
- No hallucination — if results are empty, says so

---

## Guardrails

Two-layer guardrail system:

1. **Keyword filter** — checks if question contains domain-relevant terms (order, billing, payment, delivery, customer, etc.) before sending to LLM. Rejects off-topic queries instantly without spending API calls.

2. **Schema-grounded SQL** — LLM only has access to the dataset schema. Cannot query or reference data outside the provided tables. If question cannot be answered, returns `SELECT 'NOT_APPLICABLE'`.

Example rejected queries:
- "Write me a poem" → rejected by keyword filter
- "What is the capital of France?" → rejected by keyword filter
- "What is the meaning of life?" → rejected by keyword filter

---

## Running Locally

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# Add GROQ_API_KEY to .env
python ingest.py
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Dataset

SAP Order-to-Cash synthetic dataset with 13 entity types:
- 100 sales orders, 167 order items
- 80 billing documents, 123 journal entries
- 120 payments, 86 deliveries
- 8 customers, 44 plants, 69 products
