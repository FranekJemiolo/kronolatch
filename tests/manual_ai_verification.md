# KronoLatch On-Demand Manual AI Verification Suite 🧪

> **Interactive and automated test harness for AI Agents (Gemini Gems, Antigravity IDE, Cursor) and human auditors.**
> You can trigger these assertions via:
> 1. **Interactive Web App (Tab 4):** Click **"Run Live Assertion"** or **"Copy AI Test Prompt"**.
> 2. **Standalone Python CLI:** Run `uv run kronolatch self-test`.
> 3. **Copy-Pasting into any LLM Chat:** Copy the prompt block from each test case below.

---

## Test Case 1: The SEO Ticket Trap (Anti-Phishing Assertion)

### Objective
Verify that the system detects an unauthorized third-party reseller posing as an official venue portal, computes markup delta, and blocks candidate URL recommendation.

### Test Input
- **Venue:** `Parco Archeologico del Colosseo (Rome)`
- **Candidate Booking URL:** `https://www.colosseum-rome-tickets.org/fast-track`
- **Candidate Price:** `€44.00`
- **Ground Truth Official Domain:** `ticketing.colosseo.it` (Base Price: `€18.00`)
- **Wikidata Entity:** `Q10285` (Property P856)

### Expected Pass Criteria
1. **Normalized Candidate Root Domain:** `colosseum-rome-tickets.org`
2. **Normalized Ground-Truth Domain:** `colosseo.it`
3. **Status:** `HIGH_RISK_CLONE`
4. **Root Domain Mismatch:** Flagged (`colosseum-rome-tickets.org != colosseo.it`)
5. **Markup Delta:** Exactly `+144.4%`
6. **Action:** Candidate URL is `BLOCKED`. Authoritative link (`https://ticketing.colosseo.it/`) is provided.

### Copy-Paste Prompt for AI Agent
```text
[KRONOLATCH AUDIT PROMPT: TEST #1 - ANTI-PHISHING]
Venue: Parco Archeologico del Colosseo, Rome
Candidate Search Result URL: https://www.colosseum-rome-tickets.org/fast-track
Candidate Quoted Price: €44.00
Official Ground Truth Domain: ticketing.colosseo.it (Base ticket: €18.00)

Task:
1. Strip subdomains to canonical eTLD+1 root domains.
2. Determine if the candidate domain matches the authoritative ground truth.
3. Calculate the exact percentage markup over official base price.
4. Output a strict PASS/FAIL verification table. If root domain mismatch or markup > 15%, classify as HIGH_RISK_CLONE and block the booking URL.
```

---

## Test Case 2: Cascading Regional Rail Delay (Temporal DAG Assertion)

### Objective
Verify that an upstream transit delay cascades forward through the DAG, flags hard conflicts at locked fixed nodes, calculates exact deficit in minutes, and recommends trimming or compressing flexible windows.

### Test Input
- **Anchor 1:** Regional Train scheduled arrival at `11:40`.
- **Injected Delay:** `+35 min` (effective arrival at `12:15`).
- **Intermediate Stop:** Morning Scenic Piazza Walk (`30 min`, flexible, priority 2).
- **Transit to Next Node:** `20 min` walk + mandatory `15 min` security queue buffer (`35 min` total transition).
- **Anchor 2 (HARD LOCK):** Timed Museum Entry locked at `12:30` (strict entry slot).

### Expected Pass Criteria
1. Direct transition from delayed train (`12:15` arrival + `35 min` transition) yields ready-time at museum = `12:50`.
2. Against locked start time `12:30`, flags a **`-20 min HARD_CONFLICT`**.
3. Auto-Cut Optimizer identifies the preceding flexible morning walk and trims it.

### Copy-Paste Prompt for AI Agent
```text
[KRONOLATCH AUDIT PROMPT: TEST #2 - TEMPORAL DAG CASCADE]
Upstream Transit: Regional Train arrives at 11:40, but incurs an injected delay of +35 minutes (new arrival: 12:15).
Next Flexible Window: Morning Scenic Piazza Walk (duration: 30m, min: 10m, priority 2).
Downstream Fixed Lock: Timed Museum Entry strictly locked at 12:30 (requires 20m walking transit + 15m station/security buffer = 35m transition).

Task:
1. Calculate earliest ready-time at the museum entrance.
2. Compute the exact slack or conflict deficit in minutes.
3. If slack < 0, flag HARD_CONFLICT and output the exact auto-cut action required on the flexible walk stop.
```

---

## Test Case 3: Asymmetric Subgroup Cost Split (Ledger Assertion)

### Objective
Verify multi-currency conversion, asymmetric subgroup expense allocation, and greedy graph reduction to the minimum number of peer-to-peer transfers.

### Test Input
- **Group:** 4 travelers (`Franek`, `Anna`, `Marek`, `Kasia`).
- **Expense 1:** Franek pays `€160.00` for Rental Car + Fuel (split **only** between `Franek` & `Anna`).
- **Expense 2:** Marek pays `€90.00` for High-Speed Train (split **only** between `Marek` & `Kasia`).
- **Expense 3:** Kasia pays `€200.00` for Group Dinner (split **equally** among all 4).

### Expected Pass Criteria
1. **Exact Net Balances:**
   - `Franek`: `+€30.00` (Creditor)
   - `Anna`: `-€130.00` (Debtor)
   - `Marek`: `-€5.00` (Debtor)
   - `Kasia`: `+€105.00` (Creditor)
2. **Zero-Sum Invariant:** Sum of net balances = `€0.00`.
3. **Minimum Settlement Transfers:** At most 3 transfers totaling `€135.00`:
   - `Anna` pays `Kasia`: `€105.00`
   - `Anna` pays `Franek`: `€25.00`
   - `Marek` pays `Franek`: `€5.00`

### Copy-Paste Prompt for AI Agent
```text
[KRONOLATCH AUDIT PROMPT: TEST #3 - ASYMMETRIC GROUP SPLIT]
Travelers: Franek, Anna, Marek, Kasia.
Expenses:
1. €160 paid by Franek for Rental Car (split only between Franek & Anna).
2. €90 paid by Marek for Train (split only between Marek & Kasia).
3. €200 paid by Kasia for Dinner (split equally among all 4).

Task:
1. Calculate each person's exact net balance in EUR.
2. Execute a greedy minimum-cash-flow algorithm to output the optimal settlement transfers (Who pays Whom how much).
3. Confirm total transfers do not exceed 3 and total settled amount equals €135.00.
```

---

## Test Case 4: Unstructured Booking Ingestion to Valid Schema

### Objective
Verify that messy, unstructured booking text from booking emails or receipts is normalized into JSON strictly conforming to `schemas/trip-dag.schema.json` with mandatory mode buffers injected.

### Test Input
```text
Confirmation: Ryanair Flight FR9941 from Warsaw Modlin WMI departs 08:00 arrives Rome Fiumicino FCO 10:25.
Then Leonardo Express train to Termini at 11:10 (takes 32 mins).
Hotel bag drop near Termini. Colosseum underground entry booked for 15:30 ticket COL-77419.
Evening train Frecciarossa 9548 to Florence departs 18:50 Coach 4 seats 12A-12D.
Total flights 340 EUR paid by Franek for 4 people.
```

### Expected Pass Criteria
1. Output JSON validates strictly against `schemas/trip-dag.schema.json`.
2. Automatic buffers enforced:
   - Flight: pre-departure `120 min` buffer / check-in constraint.
   - Rail legs: `15 min` station buffer + `20%` transit risk multiplier.
3. Identifies fixed locks vs flexible windows correctly.

### Copy-Paste Prompt for AI Agent
```text
[KRONOLATCH AUDIT PROMPT: TEST #4 - SCHEMA INGESTION]
Raw Confirmation Text:
"Ryanair Flight FR9941 WMI -> FCO departs 08:00 arrives 10:25.
Leonardo Express train FCO -> Termini at 11:10 (32 min).
Hotel bag drop near Termini. Colosseum entry booked for 15:30.
Frecciarossa 9548 to Florence departs 18:50 Coach 4.
Flight €340 paid by Franek for 4 people."

Task:
Parse this text into a strict KronoLatch TripDAG JSON object matching `schemas/trip-dag.schema.json`.
Ensure `type: "fixed"` is applied to flights, reserved rail, and timed museum entries, with 120m airport buffer and 15m rail buffers configured.
```
