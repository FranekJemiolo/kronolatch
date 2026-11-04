# KronoLatch Enhancement Implementation Plan 🚀

> **Targeting Three Next-Horizon Enhancements:**
> 1. **In-Browser & CLI Ticket/PDF Ingestion (Zero-Cloud)** — ✅ **COMPLETED & VERIFIED**
> 2. **Live Public Rail Delay Telemetry & Domino Evaluation (Open Transit Feeds)** — ✅ **COMPLETED & VERIFIED**
> 3. **Peer-to-Peer (P2P) Offline Group Sync & QR Code State Transfer** — ✅ **COMPLETED & VERIFIED**

---

## Architecture Principles
1. **100% Offline-First & Serverless:** Zero reliance on centralized backend databases or paid cloud infrastructure.
2. **Zero-Hallucination Determinism:** Parsing and math are deterministic; LLMs (optional BYOK) are only tapped when unstructured fuzzy vision extraction is requested.
3. **Cross-Platform Parity:** Every core capability is exposed both in the Python CLI (`uv run kronolatch`) and the client-side PWA on GitHub Pages.

---

## Phase 1: Client-Side & Local Ticket Ingestion (PDF & E-Ticket Parsing) — ✅ COMPLETE

### Goal
Enable travelers to drop PDF tickets (e.g. Trenitalia, PKP, Italo, airline boarding passes) or paste raw booking confirmation texts directly into the Web UI and Python CLI. Automatically extract booking references (PNR), transport numbers, departure/arrival timestamps, carriage/seat numbers, and instantiate locked `FIXED` itinerary nodes with mode-specific buffer rules.

### Components & Deliverables
1. **Python CLI ([`src/kronolatch/ingest.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/ingest.py)):**
   - Added `pypdf>=4.0.0` to `pyproject.toml` dependencies.
   - Implemented `TicketIngestor` supporting PDF text extraction and regex pattern matching for:
     - European Rail (Trenitalia, Italo, PKP, Deutsche Bahn, SNCF): PNR, Train Number, Origin/Destination stations, Departure/Arrival times, Carriage, Seat.
     - Airline Boarding Passes / E-Tickets (IATA format, Flight Number, 6-char alphanumeric PNR, Terminal, Gate, Boarding/Departure times).
   - Added CLI command `uv run kronolatch ingest-ticket <file_or_text> [--trip <path>] [--out <path>]` to parse and append the new node to a trip DAG.
2. **Web UI ([`web/app.js`](file:///Users/franek/personal_workspace/kronolatch/web/app.js) & [`web/index.html`](file:///Users/franek/personal_workspace/kronolatch/web/index.html)):**
   - Implemented zero-dependency client-side PDF text extraction in `web/app.js` and client-side dropzone.
   - Drag-and-drop or file upload zone in Tab 1: "Ingest Ticket (PDF / Text)".
   - Instant visual preview card with extracted PNR, carriage, seat, departure, and arrival time.
   - One-click button "Add to Schedule" creating locked `FIXED` node with automatic mode buffer (+120m for flight, +15m for rail).
3. **Automated Tests:**
   - [`tests/test_ingest.py`](file:///Users/franek/personal_workspace/kronolatch/tests/test_ingest.py): Rail text, flight boarding pass, dynamic PDF generation and parsing, and trip insertion. (4/4 passing).

---

## Phase 2: Live Rail Delay & Transit Telemetry (Open Transit Feeds) — ✅ COMPLETE

### Goal
Allow travelers to query real-time train delays using public open-data transit APIs (e.g., Trenitalia ViaggiaTreno public API endpoints requiring no API key) or custom live feed endpoints. Injected live delays feed directly into the Temporal DAG engine to dynamically detect downstream collisions and recommend stop trimming.

### Components & Deliverables
1. **Python Module ([`src/kronolatch/live_transit.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/live_transit.py)):**
   - Implemented `LiveTransitClient` with:
     - Public Trenitalia ViaggiaTreno API integration (query station & train progress, delay in minutes).
     - Graceful offline fallback / simulation mode when offline or outside Italy.
     - Integration with `DAGValidator` to check all rail legs in a `TripDAG` against live delays.
   - Added CLI command `uv run kronolatch live-delay <train_number>` and option `--live-delays` on `uv run kronolatch validate`.
2. **Web UI ([`web/app.js`](file:///Users/franek/personal_workspace/kronolatch/web/app.js) & [`web/index.html`](file:///Users/franek/personal_workspace/kronolatch/web/index.html)):**
   - Added "Check Live Rail Feeds" button next to delay controls.
   - Queries live delay asynchronously, displays real-time minutes delayed, automatically syncs with the delay slider, and triggers the auto-trim recommendation if a conflict arises.
3. **Automated Tests:**
   - [`tests/test_live_transit.py`](file:///Users/franek/personal_workspace/kronolatch/tests/test_live_transit.py): Train number extraction, fallback simulation, DAG rail leg detection, and live delay domino conflict cascade. (4/4 passing).

---

## Phase 3: Peer-to-Peer (P2P) Offline Group Sync & QR Code State Transfer — ✅ COMPLETE

### Goal
Solve on-the-ground group synchronization without central accounts, cloud databases, or mobile internet. Group members can exchange new expenses, node additions, or debt settlements directly peer-to-peer using high-density QR code visual sync and portable compressed tokens.

### Components & Deliverables
1. **Python CLI ([`src/kronolatch/sync.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/sync.py)):**
   - Implemented compressed payload generator & parser (using `zlib` / `base64`) for trip deltas (expenses and nodes).
   - Supported `uv run kronolatch share --type [all|expenses|itinerary] [--sender <name>]` to generate a shareable token.
   - Supported `uv run kronolatch sync <token_or_file>` to merge incoming expenses without duplicating existing records.
2. **Web UI ([`web/app.js`](file:///Users/franek/personal_workspace/kronolatch/web/app.js) & [`web/index.html`](file:///Users/franek/personal_workspace/kronolatch/web/index.html)):**
   - Added "P2P Offline Sync" modal dialog `#syncModal`.
   - Generates compressed high-density QR code using zero-cloud canvas rendering (`drawQrCodeCanvas`).
   - Provided "Receive Companion Updates" with automatic conflict-free merging of expenses and stops into `localStorage`.
   - Visual diff prompt: "Found N new expense(s) and N new stop(s). Existing items will not be duplicated."
3. **Automated Tests:**
   - [`tests/test_sync.py`](file:///Users/franek/personal_workspace/kronolatch/tests/test_sync.py): Token compression, decompression, validation, and idempotent merging of expense records. (4/4 passing).

---

## Phase 4: Integration, Documentation & Verification — ✅ COMPLETE

### Verification Evidence
1. `uv run pytest`: **28 / 28 unit tests passing (100%)**.
2. `uv run kronolatch self-test`: **4 / 4 architectural tests passing (100%)**.
3. `uv run ruff check .` & `uv run ruff format --check .`: **0 errors, fully compliant**.
4. Documentation updated in [`README.md`](file:///Users/franek/personal_workspace/kronolatch/README.md) and [`docs/VISION.md`](file:///Users/franek/personal_workspace/kronolatch/docs/VISION.md).
5. Live deployment automated via GitHub Actions on [https://franekjemiolo.github.io/kronolatch/](https://franekjemiolo.github.io/kronolatch/).
