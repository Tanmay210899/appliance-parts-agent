# PartSelect Agentic Chatbot

An intelligent chatbot for finding and installing dishwasher and refrigerator parts using hybrid retrieval (SQL + Vector Search) orchestrated by an LLM planner agent.


## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER QUERY                              │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                  LLM PLANNER AGENT                              │
│                  (Gemini 2.5 Flash)                             │
│  • Analyzes user intent                                         │
│  • Function calling to orchestrate tools                        │
│  • Multi-step reasoning                                         │
└─────────┬────────────────────────────────────────┬──────────────┘
          ↓                                        ↓
┌─────────────────────────────┐  ┌────────────────────────────────┐
│    SQL TOOL (PostgreSQL)     │  │  VECTOR TOOL (Qdrant)          │
│  • 13,867 parts              │  │  • Semantic search             │
│  • Exact filters:            │  │  • SBERT embeddings (384-dim)  │
│    - part_id, brand          │  │  • Collections:                │
│    - price, availability     │  │    - parts (13,867)            │
│    - install_difficulty      │  │    - repairs (21)              │
└─────────────────────────────┘  └────────────────────────────────┘
          ↓                                        ↓
┌─────────────────────────────────────────────────────────────────┐
│                   VALIDATION LAYER                  │
│  • Checks for hallucinations                                    │
│  • Verifies data grounding                                      │
│  • Retry mechanism                            │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
                   FINAL RESPONSE
```

**Key Design Principles:**
- **Hybrid Retrieval**: LLM decides when to use SQL, Vector Search, or both
- **Grounded Responses**: All answers backed by retrieved data
- **Context Awareness**: Tracks conversation history for follow-ups
- **Validation**: Optional quality check to prevent hallucinations


##  Tech Stack

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Framework** | FastAPI 0.109.0 | REST endpoints, async support |
| **LLM** | Google Gemini 2.5 Flash | Function calling, reasoning |
| **Embeddings** | SBERT (all-MiniLM-L6-v2) | 384-dim vectors, local |
| **Vector DB** | Qdrant 1.7.4 | Semantic search, filtering |
| **SQL DB** | PostgreSQL 17+ | Structured data, exact queries |
| **Server** | Uvicorn 0.27.0 | ASGI server |

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | Next.js 14.2.35 | React app with SSR |
| **Language** | TypeScript | Type safety |
| **Styling** | Tailwind CSS | Utility-first CSS |
| **HTTP Client** | Axios | API communication |

### Data
- **13,867 parts** scraped from PartSelect (dishwashers + refrigerators)
- **21 repair guides** for common issues
- **16 fields per part** (price, brand, symptoms, videos, etc.)


## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 17+
- Docker (for Qdrant)
- Google API Key for Gemini

### 1. Clone & Setup Environment
```bash
git clone <repo>
cd partselect-chatbot

# Backend setup
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd frontend
npm install
cd ..
```

### 2. Configure Environment
```bash
cp .env.example .env
```

Edit `.env`:
```bash
GOOGLE_API_KEY=your_gemini_api_key_here
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_DB=partselect
```

### 3. Start Databases
```bash
# PostgreSQL (if not running)
brew services start postgresql  # macOS
sudo service postgresql start   # Linux

# Qdrant (Docker)
docker run -p 6333:6333 qdrant/qdrant
```

### 4. Load Data
```bash
# Create database and load parts
createdb partselect
python backend/scripts/01_setup_postgres.py

# Create vector embeddings (takes ~5 minutes)
python backend/scripts/02_setup_qdrant.py
```

### 5. Run the Application
```bash
# Terminal 1: Backend
source .venv/bin/activate
python -m uvicorn backend.app.main:app --port 8000 --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

Visit **http://localhost:3000**



## Performance & Usage

### Response Times
| Query Type | Time | Details |
|------------|------|---------|
| **Simple lookup** | 2-3s | Direct part ID query |
| **Semantic search** | 3-5s | Vector search + retrieval |
| **With validation** | 5-8s | +2-3s for validation check |
| **Complex (multi-tool)** | 4-6s | Multiple function calls |

### API Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Create session
curl -X POST http://localhost:8000/api/session/new

# Chat
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me Whirlpool door bins under $50"}'
```

### Usage Tips
- **Validation**: Enabled by default (max_retries=2) - disable for faster responses
- **Sessions**: 30-minute timeout, conversation history tracked
- **Rate Limits**: Depends on Gemini API quota
- **Concurrency**: Async support, can handle multiple requests



## Design Decisions

### 1. **Hybrid Retrieval Architecture**
**Decision:** Use both SQL and Vector Search, not just one.

**Why?**
- SQL excels at exact filters (price < $50, brand = "Whirlpool")
- Vector search handles natural language ("dishwasher not draining")
- Combining both gives best of both worlds

**Alternative Considered:** Pure vector search with metadata filtering
- **Rejected:** Harder to maintain, less flexible for complex queries

---

### 2. **LLM as Orchestrator (Agentic Pattern)**
**Decision:** Let LLM decide which tools to call via function calling.

**Why?**
- User queries are unpredictable ("cheap Whirlpool parts" = semantic + filters)
- LLM can chain multiple tools (lookup part → find replacements)
- More flexible than hardcoded routing rules

**Alternative Considered:** Rule-based routing (regex, keywords)
- **Rejected:** Brittle, requires constant maintenance

---

### 3. **Gemini 2.5 Flash**
**Decision:** Use Google Gemini 2.5 Flash for the LLM planner.

**Why?**
- Fast (~2s response time)
- Excellent function calling support
- Cost-effective ($0.075/1M input tokens vs GPT-4's $5/1M)
- Good at structured JSON outputs

**Alternative Considered:** GPT-4, Claude 3.5

---

### 4. **Validation Layer**
**Decision:** Add optional ValidatorAgent to check responses.

**Why?**
- Prevents hallucinations (LLM making up part numbers)
- Verifies data grounding (response matches retrieved data)
- Configurable (can disable for speed)

**Trade-off:** Adds 2-3 seconds but improves accuracy.

---

### 5. **What Gets Embedded vs. Stored in SQL**
**Decision:** Embed only natural language text, store structured data in SQL/payload.

**Why?**
- Embeddings capture semantic meaning ("not draining" ≈ "water pooling")
- Structured data (price, brand) needs exact matching
- Hybrid approach reduces embedding size (13,867 parts × 384 dims = 5MB)

**Embedded fields:**
- Part name, description, symptoms, user stories (chunked to 600 chars)

**SQL/Payload fields:**
- Price, brand, availability, URLs, install_time, difficulty

---

### 6. **SBERT (Local)**
**Decision:** Use SBERT `all-MiniLM-L6-v2` locally.

**Why?**
- FREE (no API costs)
- Fast (14,000 sentences/sec)
- Privacy (no data sent to third parties)
- Good quality (384 dimensions sufficient for product search)

**Trade-off:** Slightly lower quality than OpenAI's ada-002 (1536 dims), but as good for this use case

---

### 7. **Next.js Frontend (Not React SPA)**
**Decision:** Use Next.js with SSR instead of plain React.

**Why?**
- Built-in routing and API routes
- TypeScript support out of the box

---

## Database Schema

### PostgreSQL - `parts` table (13,867 rows)
```sql
- part_id (PK)
- part_name, mpn_id, brand
- part_price, availability
- install_difficulty, install_time
- symptoms, product_types, replace_parts
- product_description, installation_story
- install_video_url, product_url
- appliance_type (dishwasher/refrigerator)
```

### Qdrant - `partselect_parts` collection
- **Vectors:** 384-dim SBERT embeddings
- **Payload:** All fields from SQL (for filtering)
- **Indexes:** part_id, brand, price, appliance_type, availability

---

##  Deployment

### Backend (Railway, Render, or Fly.io)
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend (Vercel)
```bash
cd frontend
npm run build
vercel deploy
```

### Database Options
- **PostgreSQL:** Local
- **Qdrant:** self-hosted Docker

---

##  FAQ
**Q: Why not use LangChain?**  
A: We use the native Google Gemini SDK for cleaner code and better control. LangChain adds abstraction overhead.

**Q: Can I use OpenAI instead of Gemini?**  
A: Yes! Swap out the LLM client in `backend/app/llm_client.py`. The function calling logic will need minor adjustments.

**Q: How do I add more appliances?**  
A: Scrape new data, add to CSV, re-run setup scripts. Update the system prompt to include new appliance types.

---
