# KronoLatch Enhancement Implementation Plan 🚀

> **Targeting Three Next-Horizon Enhancements:**
> 1. **In-Browser & CLI Ticket/PDF Ingestion (Zero-Cloud)**
> 2. **Live Public Rail Delay Telemetry & Domino Evaluation (Open Transit Feeds)**
> 3. **Peer-to-Peer (P2P) Offline Group Sync & QR Code State Transfer**

---

## Architecture Principles
1. **100% Offline-First & Serverless:** Zero reliance on centralized backend databases or paid cloud infrastructure.
2. **Zero-Hallucination Determinism:** Parsing and math are deterministic; LLMs (optional BYOK) are only tapped when unstructured fuzzy vision extraction is requested.
3. **Cross-Platform Parity:** Every core capability is exposed both in the Python CLI (`uv run kronolatch`) and the client-side PWA on GitHub Pages.

---

## Phase 1: Client-Side & Local Ticket Ingestion (PDF & E-Ticket Parsing)

### Goal
Enable travelers to drop PDF tickets (e.g. Trenitalia, PKP, Italo, airline boarding passes) or paste raw booking confirmation texts directly into the Web UI and Python CLI. Automatically extract booking references (PNR), transport numbers, departure/arrival timestamps, carriage/seat numbers, and instantiate locked `FIXED` itinerary nodes with mode-specific buffer rules.

### Components & Deliverables
1. **Python CLI (`src/kronolatch/ingest.py`):**
   - Add `pypdf>=4.0.0` to `pyproject.toml` dependencies.
   - Implement `TicketIngestor` supporting PDF text extraction and regex pattern matching for:
     - European Rail (Trenitalia, Italo, PKP, Deutsche Bahn, SNCF): PNR, Train Number, Origin/Destination stations, Departure/Arrival times, Carriage, Seat.
     - Airline Boarding Passes / E-Tickets (IATA format, Flight Number, 6-char alphanumeric PNR, Terminal, Gate, Boarding/Departure times).
   - Add CLI command `uv run kronolatch ingest-ticket <file_or_text> [--trip-file <path>]` to parse and append the new node to a trip DAG.
2. **Web UI ([`web/app.js`](file:///Users/franek/personal_workspace/kronolatch/web/app.js) & [`web/index.html`](file:///Users/franek/personal_workspace/kronolatch/web/index.html)):**
   - Implement zero-dependency client-side PDF text extraction in `web/app.js` (using standard stream parsing / binary text extraction) and client-side dropzone.
   - Drag-and-drop or file upload zone in Tab 1 (Schedule) and Tab 4 (Studio): "Drop Ticket PDF or E-Ticket".
   - Instant visual preview card with extracted PNR, carriage, seat, departure, and arrival time.
   - One-click button "Add to Itinerary as Locked Node" with automatic mode buffer (+120m for flight, +15m for rail).
3. **Automated Tests:**
   - [`tests/test_ingest.py`](file:///Users/franek/personal_workspace/kronolatch/tests/test_ingest.py): Verify rail and airline ticket parsing against realistic mock tickets, verifying PNR extraction and node creation.

---

## Phase 2: Live Rail Delay & Transit Telemetry (Open Transit Feeds)

### Goal
Allow travelers to query real-time train delays using public open-data transit APIs (e.g., Trenitalia ViaggiaTreno public API endpoints requiring no API key) or custom live feed endpoints. Injected live delays feed directly into the Temporal DAG engine to dynamically detect downstream collisions and recommend stop trimming.

### Components & Deliverables
1. **Python Module (`src/kronolatch/live_transit.py`):**
   - Implement `LiveTransitClient` with:
     - Public Trenitalia ViaggiaTreno API integration (e.g., query station & train progress, delay in minutes).
     - Graceful offline fallback / simulation mode when offline or outside Italy.
     - Integration with `DAGValidator` to check all rail legs in a `TripDAG` against live delays.
   - CLI command `uv run kronolatch live-delay <train_number>` and option `--live-delays` on `uv run kronolatch validate`.
2. **Web UI ([`web/app.js`](file:///Users/franek/personal_workspace/kronolatch/web/app.js) & [`web/index.html`](file:///Users/franek/personal_workspace/kronolatch/web/index.html)):**
   - Add a "Live Transit Status" badge and "Check Live Delay" action next to rail transit nodes (e.g., Leonardo Express, Frecciarossa).
   - Queries live delay asynchronously, displays real-time minutes delayed, automatically syncs with the delay slider, and triggers the auto-trim recommendation if a conflict arises.
3. **Automated Tests:**
   - [`tests/test_live_transit.py`](file:///Users/franek/personal_workspace/kronolatch/tests/test_live_transit.py): Mock HTTP tests testing successful delay parsing, train not found, network timeouts, and DAG delay injection.

---

## Phase 3: Peer-to-Peer (P2P) Offline Group Sync & QR Code State Transfer

### Goal
Solve on-the-ground group synchronization without central accounts, cloud databases, or mobile internet. Group members can exchange new expenses, node additions, or debt settlements directly peer-to-peer using high-density QR code visual sync and portable compressed tokens.

### Components & Deliverables
1. **Python CLI (`src/kronolatch/sync.py`):**
   - Implement compressed payload generator & parser (using `zlib` / `base64`) for trip deltas (expenses and nodes).
   - Support `uv run kronolatch share --type [all|expenses|itinerary] [--compact]` to generate a shareable token or terminal QR code.
   - Support `uv run kronolatch sync <token_or_file>` to merge incoming expenses without duplicating existing records.
2. **Web UI ([`web/app.js`](file:///Users/franek/personal_workspace/kronolatch/web/app.js) & [`web/index.html`](file:///Users/franek/personal_workspace/kronolatch/web/index.html)):**
   - Add a "Sync & Share Offline" modal dialog.
   - Generate compressed high-density QR code using zero-cloud canvas rendering.
   - Provide a "Scan / Paste Group Sync Code" feature with automatic conflict-free merging of expenses and stops into `localStorage`.
   - Visual diff prompt: "Received 2 new expenses from Anna (€45.00 for Gelato & Lunch). Merge into group ledger?"
3. **Automated Tests:**
   - [`tests/test_sync.py`](file:///Users/franek/personal_workspace/kronolatch/tests/test_sync.py): Test token compression, decompression, validation, and idempotent merging of expense records.

---

## Phase 4: Integration, Documentation & Verification

### Tasks
1. Run `uv run pytest` (target: 100% pass rate across all new test suites).
2. Run `uv run kronolatch self-test` (ensure all architectural tests remain green).
3. Run `uv run ruff check .` and `uv run ruff format .` (clean formatting).
4. Update [`README.md`](file:///Users/franek/personal_workspace/kronolatch/README.md) and [`docs/VISION.md`](file:///Users/franek/personal_workspace/kronolatch/docs/VISION.md) with documentation for the 3 new features and new CLI commands.
5. Commit and push each phase cleanly to `origin/main` to trigger automated GitHub Actions CI & Pages deployment.
