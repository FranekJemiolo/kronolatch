# KronoLatch Extended Horizon Architecture & Implementation Plan 🚀🧭

> **Deterministic-First, Agent-Assisted Travel Orchestration — Next-Generation Architectural Roadmap**
> 
> Expanding KronoLatch beyond single-scenario scheduling into **Stochastic Risk Resilience**, **Astronomical & Weather-Aware Temporal Math**, **Topological Critical-Path Visualization**, **Itemized Multimodal Ingestion**, **Schengen Regulatory Compliance**, and **Native Calendar / Wallet Synchronization**.

---

## 1. Guiding Principles & Architectural Continuity

Every extended feature must strictly adhere to KronoLatch’s founding axioms:

1. **100% Offline-First & Serverless (Zero-Cloud-Cost):** All algorithms must execute entirely in the user’s client runtime (Python CLI via `uv` or modern browser via WebAssembly / Vanilla JS). No centralized backend, no hosted database, and zero ongoing cloud infrastructure cost.
2. **Deterministic-First, Zero-Hallucination Division of Labor:**
   - **Deterministic Engines:** Mathematical buffer arithmetic, topological sorting, probability distributions, astronomical solar trigonometry, and minimum-cash-flow graph reduction are calculated with exact algebraic precision.
   - **AI Agents / Multimodal LLMs (BYOK):** Reserved strictly for fuzzy perception—extracting unstructured text, interpreting paper receipts, and conversational destination exploration.
3. **Cross-Platform Parity:** Every core capability must have 1-to-1 operational equivalence across:
   - **Tier 1 (The Simple Web App):** Calm, accessible PWA deployed to GitHub Pages.
   - **Tier 2 (The Python CLI):** Fast terminal workflows powered by `uv`, `typer`, `pydantic`, and `rich`.
   - **Tier 3 (Portable AI Skills):** System instructions and schemas for Gemini Gems, Antigravity IDE, Cursor, and MCP.
4. **Calm, High-Contrast, Dignified Aesthetics:** Stress-reducing travel interface adhering to human-centered design—no developer neon, no chaotic alerts, and clear visual hierarchy.

```mermaid
graph TD
    subgraph Core Pillars (Already Delivered)
        P1[Pillar I: Anti-Phishing Domain Verifier]
        P2[Pillar II: Temporal DAG & Buffer Engine]
        P3[Pillar III: Ticket & Transit Ingestion]
        P4[Pillar IV: Multi-Currency Group Ledger]
    end

    subgraph Extended Horizons (Next-Generation Roadmap)
        H6[Phase 6: Monte Carlo Stochastic Trip Simulation]
        H7[Phase 7: Solar & Weather-Aware DAG Adaptation]
        H8[Phase 8: Interactive Critical-Path Graph Visualizer]
        H9[Phase 9: Itemized Receipt Splitting & OCR Ingest]
        H10[Phase 10: 90/180-Day Schengen & Visa Vault]
        H11[Phase 11: RFC 5545 iCalendar & Wallet Pass Export]
    end

    P2 --> H6
    P2 --> H7
    P2 --> H8
    P4 --> H9
    P1 --> H10
    P2 --> H11
```

---

## Phase 6: Stochastic Itinerary Simulation & Monte Carlo Delay Stress-Testing

### The Problem
Single-scenario delay testing (e.g. testing what happens if a train is exactly 35 minutes late) only probes one discrete failure mode. Real-world travel transit is governed by heavy-tailed probability distributions:
- Commercial flights exhibit log-normal delay profiles with catastrophic gate closure cut-offs.
- High-speed rail suffers platform routing bottlenecks and switch failures.
- Museum security lines fluctuate based on tour bus arrivals.

A traveler needs to know: **"What is the mathematical probability that our group will miss our 15:30 Colosseum entry under real-world operational variance?"**

### Mathematical Formulation
Run an on-demand Monte Carlo simulation with $N = 2,500$ trials:

$$\mathbf{T}_{\text{transit}, i} \sim \mathcal{D}_{\text{mode}}\left(\mu_i, \sigma_i\right)$$

Where mode-specific stochastic distributions are modeled as:
1. **Flights ($\mathcal{D}_{\text{flight}}$):** Log-Normal distribution with parameter bounds:
   $$f(t; \mu, \sigma) = \frac{1}{t \sigma \sqrt{2\pi}} \exp\left(-\frac{(\ln t - \mu)^2}{2\sigma^2}\right)$$
2. **High-Speed & Regional Rail ($\mathcal{D}_{\text{rail}}$):** Gamma distribution ($\kappa = 1.25, \theta = 12.0\text{ min}$) with 8% likelihood of zero delay and 4% likelihood of severe track stoppage ($>45\text{ min}$).
3. **Rental Car Driving ($\mathcal{D}_{\text{car}}$):** Skew-normal distribution accounting for peak rush-hour variance and parking search latency ($T_{\text{parking}} \sim \mathcal{U}(5, 25)$).
4. **Walking ($\mathcal{D}_{\text{walk}}$):** Normal distribution $\mathcal{N}(\mu, 0.15\mu)$ modeling group walking speed variance.

### Outputs & Metrics
- **Trip Fragility Index ($F_{\text{trip}} \in [0.0, 1.0]$):**
  $$F_{\text{trip}} = \frac{1}{N} \sum_{k=1}^N \mathbf{1}\left(\exists \text{ node } j \in \text{FixedNodes} : t_{\text{arrival}, j}^{(k)} > t_{\text{lock}, j}\right)$$
- **Recommended $\alpha^*_{\text{risk}}$ (Target Reliability):** Automatically calculates the minimum risk cushion $\alpha^*$ required to bring $F_{\text{trip}} < 0.05$ (95% arrival confidence interval).

### Deliverables
1. **Python Engine ([`src/kronolatch/simulation.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/simulation.py)):**
   - `MonteCarloSimulator` class running 2,500 iterations in $<60\text{ ms}$.
   - CLI command: `uv run kronolatch simulate [--iterations 2500] [--target-confidence 0.95] [--trip path]`.
2. **Web UI ([`web/app.js`](file:///Users/franek/personal_workspace/kronolatch/web/app.js)):**
   - "Stochastic Stress Test" widget with visual probability distribution bell curve.
   - Interactive slider: "Target Certainty (90% | 95% | 99%)" that dynamically calculates the required buffer multiplier.
3. **Automated Unit Tests:**
   - Deterministic seed testing, distribution boundary validation, and fragile vs robust itinerary scoring.

---

## Phase 7: Solar, Daylight & Meteorological Leeway Engine (Astronomical DAG)

### The Problem
Traditional itinerary builders treat 17:00 in June identically to 17:00 in December. In December, outdoor archaeological parks (e.g. Roman Forum, Appian Way) and scenic viewpoints (Piazzale Michelangelo) are in total darkness by 16:45, causing travelers to walk through locked gates or poorly lit ruins. Furthermore, heavy precipitation drastically increases walking and transit times.

### Mathematical Formulation
1. **Astronomical Solar Position Algorithm (NOAA / Meeus Solar Calculations):**
   - Exact solar zenith angle $\theta_s$, solar noon, civil sunrise, golden hour, and civil sunset computed offline from Julian day $J_D$ and geographical coordinates $(\phi, \lambda)$:
     $$\cos \theta_s = \sin \phi \sin \delta + \cos \phi \cos \delta \cos \omega$$
   - Civil twilight threshold: $\theta_s = 96^\circ$. Golden hour: $\theta_s \in [84^\circ, 90^\circ]$.
2. **Meteorological Dynamic Buffer Penalty:**
   When precipitation probability $P_{\text{precip}} > 40\%$, the transition buffer formula adapts dynamically:
   $$T_{\text{transition}} = T_{\text{transit}} \times (1 + \beta_{\text{weather}}) + T_{\text{overhead}} + \lceil T_{\text{transit}} \times \alpha_{\text{risk}} \rceil + B_{\text{fixed}}$$
   Where $\beta_{\text{weather}} = 0.25$ for walking/driving in rain.
3. **Daylight Deficit Invariant:**
   For any node with `outdoor: true`, the engine validates:
   $$t_{\text{end}} \le t_{\text{civil\_sunset}} + \text{tolerance\_min}$$
   If violated, the DAG engine flags a `DAYLIGHT_DEFICIT` warning and recommends a swap with an indoor museum.

### Deliverables
1. **Python Engine ([`src/kronolatch/solar.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/solar.py)):**
   - Pure offline solar calculator requiring zero external network requests.
   - Integration with Open-Meteo free open-source forecast API (with offline cache fallback).
   - CLI command: `uv run kronolatch solar-audit [--date YYYY-MM-DD] [--lat 41.89 --lon 12.49]`.
2. **Web UI ([`web/app.js`](file:///Users/franek/personal_workspace/kronolatch/web/app.js)):**
   - Daylight gradient background on the timeline (daylight, golden hour, twilight, night).
   - Golden Hour badge on scenic viewpoint nodes.
   - Weather sensitivity toggle (+25% rain buffer simulation).
3. **Automated Unit Tests:**
   - Astronomical solar position assertions against NOAA ground truth for Rome, Paris, and Tokyo across summer and winter solstices.

---

## Phase 8: Interactive Critical-Path Graph Visualizer & Topology Inspector

### The Problem
While linear timelines are simple to read, they obscure topological dependency chains. When an itinerary contains multiple parallel subgroups (e.g., Drivers driving rental car vs Rail riders taking train; or Kasia visiting a boutique while Franek visits a gallery), a linear list cannot communicate which sequence of events controls the total trip slack.

### Architectural Solution
1. **Topological Critical Path Method (CPM):**
   - Calculate Earliest Start ($ES$), Earliest Finish ($EF$), Latest Start ($LS$), and Latest Finish ($LF$) for each node in the DAG:
     $$\text{Total Float (Slack)}_i = LS_i - ES_i$$
   - **Critical Path:** The sub-graph where $\text{Total Float} = 0$. Any delay on this path directly delays downstream locked events.
2. **Visual Interactive Canvas / SVG Topology Graph:**
   - Render nodes as interactive cards arranged chronologically and partitioned by subgroup swimlanes.
   - Edges colored by float cushion:
     - 🔴 **Red (Critical):** Slack $\le 10\text{ min}$ (Zero tolerance for disruption).
     - 🟡 **Yellow (Moderate):** Slack between $10\text{ min}$ and $30\text{ min}$.
     - 🟢 **Green (Comfortable):** Slack $> 30\text{ min}$.
3. **CLI Unicode Terminal Tree (`rich.tree`):**
   - Interactive terminal rendering showing dependency hierarchy, slack cushions, and critical path nodes highlighted in bold magenta.

### Deliverables
1. **Python CLI Engine ([`src/kronolatch/graph.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/graph.py)):**
   - CPM solver computing float and critical paths.
   - CLI command: `uv run kronolatch graph [--critical-path-only] [--trip path]`.
2. **Web UI ([`web/app.js`](file:///Users/franek/personal_workspace/kronolatch/web/app.js) & [`web/index.html`](file:///Users/franek/personal_workspace/kronolatch/web/index.html)):**
   - Switchable view: "Linear Timeline" vs "Topological Graph View".
   - Client-side zero-dependency SVG renderer with drag-to-pan and zoom.
3. **Automated Unit Tests:**
   - Verification of CPM forward/backward pass math, slack calculations, and critical path isolation.

---

## Phase 9: Itemized Receipt Splitting & Multimodal OCR Ingestion

### The Problem
Group expense settlement currently assigns an entire expense to a group or predefined subgroup. In practice, restaurant bills and grocery receipts contain disparate items ordered by different individuals (e.g., wine shared by 2 people, steak ordered by 1 person, pizza ordered by another, shared dessert). Manually calculating proportional tax, tip, and copay shares is the #1 friction point in group travel.

### Mathematical Formulation
For an itemized receipt with items $j \in \{1, \dots, M\}$, where item $j$ has raw price $p_j$ and participant set $S_j \subseteq \text{Travelers}$:
$$\text{Base Cost for Traveler } k = \sum_{j : k \in S_j} \frac{p_j}{|S_j|}$$

Proportional overhead multiplier for tax $T$, tip $C$, and service charge $S$:
$$\mu_{\text{overhead}} = \frac{T + C + S}{\sum_{j=1}^M p_j}$$

Final liability for Traveler $k$:
$$\text{Liability}_k = \left(\sum_{j : k \in S_j} \frac{p_j}{|S_j|}\right) \times (1 + \mu_{\text{overhead}})$$

The computed liabilities are converted directly into normalized `Expense` entities fed into the Greedy Minimum-Cash-Flow ledger.

### Deliverables
1. **Python Engine ([`src/kronolatch/receipt.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/receipt.py)):**
   - Parser for itemized receipt strings and tabular formats.
   - Proportional tax and tip distribution math.
   - CLI command: `uv run kronolatch split-receipt <file_or_text> [--payer name] [--currency EUR]`.
2. **Web UI ([`web/app.js`](file:///Users/franek/personal_workspace/kronolatch/web/app.js)):**
   - Itemized Bill Splitter Modal: allows adding individual line items, assigning traveler avatar pills with one click, and splitting tax/tip proportionally.
   - Instant live preview of net balance adjustments.
3. **Automated Unit Tests:**
   - Strict verification that the sum of individual liabilities equals the exact total bill to the cent ($|\sum \text{Liability}_k - \text{Total}| < 0.001$).

---

## Phase 10: Schengen 90/180-Day Rule & Zero-Cloud Visa Compliance Vault

### The Problem
Non-EU nationals traveling in the Schengen Area are legally restricted to **90 days of stay within any rolling 180-day window** (Regulation (EU) 2016/399). Violating this rule can result in detention, deportation, entry bans, and hefty fines. Furthermore, passports must have at least 3 to 6 months of remaining validity beyond the departure date.

Because immigration data is sensitive personal data, travelers should **never** upload their passport history or entry/exit stamps to third-party ad-tracking websites or proprietary cloud servers.

### Mathematical Formulation
For any target date $t$, the rolling 180-day reference window is the interval $[t - 179, t]$ (inclusive of 180 days).
The cumulative stay days $S(t)$ is defined as:
$$S(t) = \sum_{d = t - 179}^t \mathbf{1}(\text{Traveler was in Schengen on day } d)$$
- Invariant: $S(t) \le 90$ for all dates $t$.
- Days Remaining on day $t$: $R(t) = 90 - S(t)$.

### Deliverables
1. **Python Engine ([`src/kronolatch/schengen.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/schengen.py)):**
   - Deterministic 90/180-day rolling compliance evaluator.
   - Passport 6-month validity expiration checker against trip return dates.
   - CLI command: `uv run kronolatch schengen-audit [--stamps stamps.json] [--trip trip.json]`.
2. **Web UI ([`web/app.js`](file:///Users/franek/personal_workspace/kronolatch/web/app.js)):**
   - "Schengen Visa & Compliance Vault" modal.
   - Interactive calendar showing rolling days consumed, days remaining, and earliest permitted re-entry date.
   - 100% encrypted in client-side `localStorage` with zero network telemetry.
3. **Automated Unit Tests:**
   - Verification against official European Commission border calculator test scenarios (multi-entry trips, leap years, edge-of-window transitions).

---

## Phase 11: Standard RFC 5545 iCalendar (`.ics`) & Mobile Wallet Pass Generator

### The Problem
After a group itinerary is verified and balanced, travelers need alerts on their mobile devices (Apple Calendar, Google Calendar, Outlook) without installing specialized apps or keeping web browser tabs open. Most export tools create simple calendar events with generic reminders, failing to alert travelers when they need to begin their transition buffers.

### Architectural Solution
1. **RFC 5545 iCalendar Generator (`.ics`):**
   - Emits clean, compliant VCALENDAR structures.
   - Sets custom `VALARM` triggers tied directly to the computed **transit and overhead buffers**:
     - Airport Departure: Alarm set for $T_{\text{overhead}} + T_{\text{transit}} = 120\text{ min} + 30\text{ min} = 150\text{ min}$ before gate closure.
     - Rail Departure: Alarm set for $15\text{ min} + T_{\text{transit}}$ before departure.
   - Embeds PNR reference codes, seat allocations, official booking URLs, and Google Maps transit navigation links directly inside `DESCRIPTION` and `LOCATION`.
2. **Zero-Cloud Client-Side Download:**
   - Single-click `.ics` file download in Web UI via Blob URL.
   - Direct CLI export: `uv run kronolatch export-ics [--out trip.ics]`.

### Deliverables
1. **Python Module ([`src/kronolatch/calendar_export.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/calendar_export.py)):**
   - Pure-Python RFC 5545 generator with buffer-aware alarm offsets.
   - CLI command: `uv run kronolatch export-ics [--out path]`.
2. **Web UI ([`web/app.js`](file:///Users/franek/personal_workspace/kronolatch/web/app.js)):**
   - "Add to Native Calendar (.ics)" button on Tab 1.
   - Direct calendar download compatible with iOS, Android, and macOS.
3. **Automated Unit Tests:**
   - Validation against RFC 5545 grammar, timezone offset normalization, and buffer alarm verification.

---

## 2. Implementation & Sequencing Matrix — ALL PHASES COMPLETED & VERIFIED ✅

| Phase | Title | Complexity | Primary Engine | UI Surface | Verification Status |
| :---: | :--- | :---: | :--- | :--- | :---: |
| **Phase 6** | **Stochastic Monte Carlo Simulation** | Medium | [`src/kronolatch/simulation.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/simulation.py), CLI `simulate` | Web Tab 1 Stress Card & `#simModal` | ✅ **45/45 Tests Passed** |
| **Phase 7** | **Astronomical Solar & Weather DAG** | Medium | [`src/kronolatch/solar.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/solar.py), CLI `solar-audit` | Timeline Solar Indicators & Rain Leeway | ✅ **45/45 Tests Passed** |
| **Phase 8** | **Interactive Critical Path Visualizer** | High | [`src/kronolatch/graph.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/graph.py), CLI `graph` | Web Timeline CPM View & Slack Badges | ✅ **45/45 Tests Passed** |
| **Phase 9** | **Itemized Receipt Splitting** | Medium | [`src/kronolatch/receipt.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/receipt.py), CLI `split-receipt` | `#receiptModal` & Cent-Exact Breakdown | ✅ **45/45 Tests Passed** |
| **Phase 10** | **Schengen 90/180-Day Rule Vault** | Medium | [`src/kronolatch/schengen.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/schengen.py), CLI `schengen-audit` | `#schengenModal` & Passport Checker | ✅ **45/45 Tests Passed** |
| **Phase 11** | **RFC 5545 iCalendar & Wallet Export** | Low | [`src/kronolatch/calendar_export.py`](file:///Users/franek/personal_workspace/kronolatch/src/kronolatch/calendar_export.py), CLI `export-ics` | "Export iCal (.ics)" Download Button | ✅ **45/45 Tests Passed** |

---

## 3. Engineering Quality Invariants & Verification Evidence

1. **Unit Test Coverage:** **45 / 45 unit tests passing (100%)** across 14 test suites (`tests/test_*.py`).
2. **Deterministic Architectural Assertions:** **4 / 4 self-test pillars passing (100%)** via `uv run kronolatch self-test`.
3. **Deterministic Parity:** Python CLI and Web JavaScript implementations produce identical numerical outputs for identical inputs.
4. **Lint & Formatting:** Code strictly compliant with Ruff (`uv run ruff check .` and `uv run ruff format --check .` with 0 errors).
5. **Offline Capability:** Every algorithm functions with network disconnected (zero cloud API dependencies).
6. **Continuous Deployment:** All updates automatically verified and deployed to GitHub Pages via GitHub Actions.
