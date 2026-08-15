# Enterprise Knowledge Copilot — Project Specification

## 1. Product Vision

Build a polished SaaS-style **Enterprise Knowledge Copilot**.

The application allows one user per organization to securely connect their own:
- Google Drive
- Slack

The user selects which Google Drive folders and Slack channels should become knowledge sources. The system ingests those sources, indexes them using an advanced RAG pipeline, and provides a multi-agent AI assistant that answers questions with source citations.

### Current MVP tenancy model

- One user per organization.
- No team members, invitations, roles, RBAC, or shared workspaces yet.
- Keep the database architecture organization-aware so multi-member organizations can be added later without a major rewrite.

---

# 2. Core User Journey

The experience should be extremely simple:

1. Landing page
2. Sign up / Login
3. Organization/workspace automatically created
4. Onboarding screen
5. Connect Google Drive
6. Select Google Drive folders
7. Connect Slack
8. Select Slack channels
9. Start knowledge sync
10. See sync progress
11. Enter AI Copilot
12. Ask questions and receive grounded answers with citations

The user should NEVER have to manually enter:
- API keys
- OAuth access tokens
- refresh tokens
- folder IDs
- Slack channel IDs
- client secrets

OAuth and connector configuration are handled by the application.

Users can skip either Google Drive or Slack and connect them later from Settings.

---

# 3. Main Features

## Authentication

Implement:
- Sign up
- Login
- Logout
- Protected routes
- Session handling
- Basic profile
- Organization automatically created for each new user

Recommended authentication approach:
- NextAuth/Auth.js or another secure production-friendly auth solution
- Prefer Google login as an optional convenient login method

Do not over-engineer authentication for the MVP.

---

# 4. Workspace

Each user has one organization/workspace.

Example:

User A
→ Organization A
→ Google Drive A
→ Slack A
→ Documents A
→ Conversations A

User B
→ Organization B
→ Google Drive B
→ Slack B
→ Documents B
→ Conversations B

All knowledge and retrieval operations MUST be isolated by organization_id.

Never allow retrieval of another organization's documents.

---

# 5. Google Drive Integration

Use OAuth.

After authorization:
- fetch accessible Drive folders
- display folder hierarchy
- allow user to select folders
- store selected folder IDs
- sync files only from selected folders
- allow resync
- allow disconnect

UI should show:

Google Drive
Connected ✓

Selected folders:
- Engineering
- Product Documentation

Actions:
- Manage folders
- Sync now
- Disconnect

Do not index the entire Drive by default.

Store useful metadata:
- provider
- external file ID
- folder ID
- folder path
- file name
- MIME type
- modified time
- source URL if available
- organization_id

---

# 6. Slack Integration

Use OAuth.

After authorization:
- fetch accessible channels
- display channel list
- allow user to select channels
- store selected channel IDs
- sync messages from selected channels
- allow resync
- allow disconnect

Example:

Slack
Connected ✓

Selected channels:
- #engineering
- #backend
- #product

Actions:
- Manage channels
- Sync now
- Disconnect

Do not search/index every channel automatically.

Store useful metadata:
- workspace ID
- channel ID
- channel name
- message ID
- timestamp
- thread ID
- organization_id

---

# 7. MCP

Use a maximum of two MCP integrations:

1. Google Drive MCP
2. Slack MCP

MCP should be used meaningfully, not just added for decoration.

Use MCP for source interaction/search where appropriate.

Keep connector abstraction clean so MCP implementations can be changed later.

Do not introduce many unnecessary MCP servers.

---

# 8. Advanced RAG Pipeline

Do NOT build a basic:
document → chunks → embeddings → vector search → LLM

pipeline.

Implement a clear advanced RAG architecture:

Document ingestion
→ parsing
→ cleaning
→ semantic/structure-aware chunking
→ metadata extraction
→ embeddings
→ PostgreSQL + pgvector

Query pipeline:

User question
→ query understanding
→ query rewriting / expansion
→ hybrid retrieval
   - vector similarity
   - keyword/BM25-style retrieval
→ metadata filtering
→ result merging
→ reranking
→ contextual compression
→ relevant context
→ agent reasoning
→ grounded answer
→ citations

Important:
- Preserve source metadata through the entire pipeline.
- Every generated answer should expose citations to the underlying Google Drive file or Slack conversation when possible.
- Never fabricate citations.
- If evidence is insufficient, explicitly say so.

---

# 9. Multi-Agent Architecture

Use LangGraph.

Recommended agents:

## Supervisor Agent
Responsibilities:
- understand the user request
- determine which sources/tools are required
- route work
- coordinate agents
- stop unnecessary tool calls

## Retrieval Agent
Responsibilities:
- query rewriting
- hybrid retrieval
- metadata filtering
- reranking
- context selection

## Research / Analysis Agent
Responsibilities:
- synthesize evidence
- compare information
- resolve conflicts
- reason across multiple documents/messages

## Answer / Citation Agent
Responsibilities:
- produce final response
- cite sources
- distinguish facts from uncertainty
- maintain concise professional formatting

Example:

User
↓
Supervisor
├── Retrieval Agent
├── Research Agent
└── Answer/Citation Agent
↓
Final grounded response

Do not create 10+ agents. Prefer a small number of meaningful agents.

---

# 10. Example Questions

The application should handle questions such as:

"What is our authentication architecture?"

"What is the leave policy?"

"Summarize our latest backend deployment discussion."

"What did the engineering team decide about Redis?"

"Compare the current authentication design with the previous architecture."

"Which documents discuss payment failures?"

"According to our documentation and Slack discussions, what is the recommended deployment process?"

For multi-source questions, combine Google Drive and Slack evidence.

---

# 11. Chat Experience

Build a premium AI chat interface.

Requirements:
- streaming responses
- markdown rendering
- code blocks
- citations
- expandable source cards
- source preview
- copy response
- regenerate
- thumbs up/down feedback
- conversation history
- rename conversation
- delete conversation
- stop generation
- retry failed requests
- loading states
- skeletons
- empty states

Citation example:

Answer text...

Sources:
[Architecture Document]
[Slack: #engineering — Mar 12]
[API Security Guidelines]

Clicking a source should open a useful preview or external source when possible.

---

# 12. UI / UX Direction

This is a major requirement.

The product should look like a **premium modern AI SaaS application**, not a generic CRUD dashboard.

Visual references can be inspired by the quality level of:
- Linear
- Vercel
- Notion
- Raycast
- modern AI products

Do NOT blindly copy any product.

## Design goals

- premium
- minimal
- modern
- highly polished
- professional
- clean typography
- excellent spacing
- strong visual hierarchy
- intuitive navigation
- subtle depth
- excellent empty states
- excellent loading states
- responsive on desktop, tablet, and mobile

Avoid:
- excessive gradients
- excessive glassmorphism
- giant animations
- visual clutter
- unnecessary cards everywhere
- childish colors
- generic bootstrap-style dashboards

---

# 13. Animations and Transitions

Use animations intentionally.

Recommended:
- page transitions
- sidebar transitions
- modal entrance/exit
- dropdown animations
- hover states
- button micro-interactions
- source card expansion
- chat message appearance
- streaming indicator
- connection success animation
- sync progress animation
- skeleton loading
- toast transitions

Use Framer Motion / Motion where appropriate.

Animations should feel:
- fast
- smooth
- subtle
- purposeful

Respect `prefers-reduced-motion`.

Do not animate everything.

---

# 14. Responsive Design

The application MUST be responsive.

Desktop:
- full sidebar
- chat workspace
- source panel

Tablet:
- collapsible sidebar
- adaptive layouts

Mobile:
- bottom/sheet navigation where appropriate
- responsive chat
- readable citations
- touch-friendly controls
- responsive source cards
- no horizontal overflow

Test common widths:
- 320px
- 375px
- 390px
- 768px
- 1024px
- 1280px
- 1440px+

---

# 15. Recommended Pages

## Public

/
 /login
 /signup

## Onboarding

/onboarding
/onboarding/connect
/onboarding/sources
/onboarding/sync

## Application

/app
/app/chat
/app/chat/[conversationId]
/app/sources
/app/sources/google-drive
/app/sources/slack
/app/settings
/app/profile

---

# 16. Dashboard

Dashboard should quickly show:

- connected sources
- sync status
- number of indexed documents
- number of indexed Slack messages
- recent conversations
- suggested questions
- system status

Example:

Knowledge Base
12,481 chunks

Google Drive
3 folders connected

Slack
4 channels connected

Last synced
5 minutes ago

Suggested:
"Explain our authentication architecture"

---

# 17. Source Management

Create a dedicated Sources page.

Google Drive card:
- connection status
- selected folders
- document count
- last sync
- sync now
- manage
- disconnect

Slack card:
- connection status
- selected channels
- message count
- last sync
- sync now
- manage
- disconnect

Include:
- search
- filters
- source status
- sync errors
- retry

---

# 18. Sync System

Sync should not block the UI.

When user clicks Sync:

UI:
"Sync started"

Backend:
- enqueue/background job
- fetch source data
- parse
- chunk
- embed
- store
- update progress

Frontend:
- show progress
- polling or WebSocket/SSE updates
- success/error states

Example:

Syncing Google Drive...

42%
124 / 294 files

Current:
Authentication Architecture.pdf

---

# 19. Backend Architecture

Use Python + FastAPI.

Suggested modules:

backend/
  app/
    main.py
    api/
    core/
    auth/
    agents/
    rag/
    ingestion/
    connectors/
    mcp/
    models/
    schemas/
    services/
    workers/
    utils/

Keep responsibilities separated.

Do not put the whole backend into one file.

---

# 20. Frontend Architecture

Use Next.js + TypeScript.

Suggested structure:

frontend/
  app/
  components/
    ui/
    chat/
    sources/
    onboarding/
    dashboard/
  lib/
  hooks/
  services/
  types/

Use reusable components.

Avoid huge page components.

---

# 21. Database

Use PostgreSQL + pgvector.

Core tables:

users
organizations
connections
knowledge_sources
documents
document_chunks
conversations
messages
sync_jobs

Potential structure:

organizations
- id
- name
- created_at

users
- id
- organization_id
- email
- name
- created_at

connections
- id
- organization_id
- provider
- encrypted_credentials
- status
- created_at
- updated_at

knowledge_sources
- id
- organization_id
- connection_id
- provider
- external_id
- name
- type
- enabled

documents
- id
- organization_id
- source_id
- external_id
- title
- content
- metadata
- checksum
- updated_at

document_chunks
- id
- document_id
- organization_id
- content
- embedding
- metadata

conversations
- id
- organization_id
- title
- created_at

messages
- id
- conversation_id
- role
- content
- citations
- created_at

sync_jobs
- id
- organization_id
- source_id
- status
- progress
- error
- started_at
- completed_at

Always scope data access by organization_id.

---

# 22. Security

Treat OAuth credentials as sensitive.

Requirements:
- never expose access tokens to frontend
- encrypt stored OAuth credentials
- use secure HTTP-only cookies/session handling
- validate OAuth state
- validate redirect URLs
- enforce organization isolation
- validate all API inputs
- do not log tokens
- do not expose secrets in error messages

Use environment variables for application secrets.

---

# 23. Error Handling

The UI should never show raw backend exceptions.

Examples:

Instead of:
"401 invalid_grant exception..."

Show:

"Google Drive connection expired.
Reconnect Google Drive to continue."

For sync:

"Some files could not be processed.
View details"

Provide:
- retry
- reconnect
- dismiss
- useful explanation

---

# 24. Observability

For development, log:
- agent execution
- retrieval count
- retrieval latency
- reranking latency
- LLM latency
- token usage if available
- sync status
- connector errors

Do not log secrets or OAuth credentials.

---

# 25. Development Strategy

Build incrementally.

Phase 1:
- project setup
- authentication
- organization creation
- premium UI shell

Phase 2:
- Google OAuth
- Drive folder selection
- Drive ingestion

Phase 3:
- Slack OAuth
- channel selection
- Slack ingestion

Phase 4:
- embeddings
- pgvector
- hybrid retrieval
- reranking

Phase 5:
- LangGraph multi-agent workflow
- citations
- streaming chat

Phase 6:
- MCP integration

Phase 7:
- polished animations
- responsive design
- error states
- loading states
- performance improvements

Do not attempt everything simultaneously.

---

# 26. Quality Bar

The finished product should feel like a real product that could be demoed to a hiring manager.

Prioritize:
1. UX quality
2. correctness
3. security
4. clean architecture
5. advanced RAG quality
6. agent orchestration
7. connector reliability
8. responsive design
9. animations
10. documentation

Avoid fake features.

If a feature is not fully implemented, label it clearly rather than pretending it works.

---

# 27. Important Engineering Rule

Do not over-engineer.

This is a portfolio MVP.

Do NOT add:
- microservices
- Kubernetes
- Kafka
- complex RBAC
- billing
- team management
- multi-organization admin panels
- 10+ agents
- unnecessary databases

Use a clean modular monolith first.

Recommended:
Next.js
+
FastAPI
+
PostgreSQL/pgvector
+
Redis only if background jobs require it
+
LangGraph
+
MCP

---

# 28. Definition of Done

The MVP is successful when a new user can:

1. Sign up
2. Automatically get an organization
3. Enter onboarding
4. Connect Google Drive with OAuth
5. Select specific folders
6. Connect Slack with OAuth
7. Select specific channels
8. Start synchronization
9. See sync progress
10. Ask questions
11. Get a grounded multi-agent answer
12. See citations
13. Open source references
14. Continue previous conversations
15. Manage connected sources
16. Disconnect/reconnect sources
17. Use the application comfortably on mobile and desktop

The final application should be visually polished enough for a portfolio demo and technically strong enough to discuss in a 2-year-experience AI/full-stack interview.
