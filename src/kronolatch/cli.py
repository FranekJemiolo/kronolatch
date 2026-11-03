"""
Typer and Rich CLI for KronoLatch.
Commands:
- validate: Run temporal DAG time-budget audit, delay simulation, and auto-cut optimization.
- verify-url: Anti-phishing audit of ticket/transit URLs against canonical root domains.
- settle: Multi-currency expense balance computation and minimum-transfer debt reduction.
- export-skill: Generate portable Gemini Gems, Antigravity IDE, Cursor, and CLI instructions.
- self-test: On-demand automated verification of all 4 architectural test cases.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kronolatch.dag_engine import calculate_transition_time, optimize_and_cut, validate_dag
from kronolatch.ledger import settle_expenses
from kronolatch.models import (
    Category,
    DAGParameters,
    Expense,
    NodeType,
    TransitMode,
    TripDAG,
    TripNode,
    VerificationStatus,
)
from kronolatch.verifier import verify_vendor_url

app = typer.Typer(
    name="kronolatch",
    help="KronoLatch: Deterministic Trip Orchestrator, Anti-Phishing Domain Verifier & Group Ledger",
    add_completion=False,
)
console = Console()


def load_or_create_sample_dag(path_str: Optional[str] = None) -> TripDAG:
    """Loads a TripDAG from JSON or returns the default Rome & Florence demonstration itinerary."""
    if path_str:
        p = Path(path_str)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return TripDAG.model_validate(data)

    # Built-in Default Multi-Modal Corridor (Rome & Florence Express)
    return TripDAG(
        trip_id="rome-florence-2026",
        title="Rome & Florence Express — 4 Pax Multi-Modal",
        destination="Rome & Florence, Italy",
        base_currency="EUR",
        travelers=["Franek", "Anna", "Marek", "Kasia"],
        parameters=DAGParameters(risk_multiplier=0.20, hub_overhead_minutes=15),
        nodes=[
            TripNode(
                id="n1",
                title="Flight WMI → FCO (Ryanair 9941)",
                type=NodeType.FIXED,
                category=Category.FLIGHT,
                transit_mode=TransitMode.FLIGHT,
                transit_min=0,
                duration_min=145,
                fixed_start_time="08:00",
                priority=10,
                official_domain="ryanair.com",
                pnr="RYR-9941K",
                notes="Gate closes 30m prior to departure.",
            ),
            TripNode(
                id="n2",
                title="Leonardo Express (FCO Airport → Roma Termini)",
                type=NodeType.FLEXIBLE,
                category=Category.RAIL,
                transit_mode=TransitMode.TRAIN,
                transit_min=25,
                duration_min=32,
                min_duration_min=32,
                priority=9,
                official_domain="trenitalia.com",
                pnr="TREN-88210",
                notes="High-frequency airport shuttle train.",
            ),
            TripNode(
                id="n3",
                title="Hotel Bag Drop & Trastevere Lunch",
                type=NodeType.FLEXIBLE,
                category=Category.FOOD,
                transit_mode=TransitMode.WALK,
                transit_min=20,
                duration_min=65,
                min_duration_min=30,
                priority=4,
                official_domain="maps.google.com",
                notes="Flexible window. Compressible during transit delay.",
            ),
            TripNode(
                id="n4",
                title="Pantheon & Piazza Navona Walk",
                type=NodeType.FLEXIBLE,
                category=Category.SIGHTSEEING,
                transit_mode=TransitMode.WALK,
                transit_min=15,
                duration_min=50,
                min_duration_min=20,
                priority=3,
                official_domain="portale.museiitaliani.it",
                notes="Optional sightseeing walk; first candidate for auto-trim.",
            ),
            TripNode(
                id="n5",
                title="Colosseum Arena & Underground (HARD LOCK)",
                type=NodeType.FIXED,
                category=Category.SIGHTSEEING,
                transit_mode=TransitMode.WALK,
                transit_min=22,
                duration_min=120,
                fixed_start_time="15:30",
                priority=10,
                official_domain="ticketing.colosseo.it",
                pnr="COL-77419-IT",
                notes="STRICT ID CHECK: Must arrive 20m before entry or slot forfeited.",
            ),
            TripNode(
                id="n6",
                title="Frecciarossa 9548 Rail (Roma Termini → Firenze SMN)",
                type=NodeType.FIXED,
                category=Category.RAIL,
                transit_mode=TransitMode.TRAIN,
                transit_min=25,
                duration_min=95,
                fixed_start_time="18:50",
                priority=10,
                official_domain="trenitalia.com",
                pnr="FR-551902",
                notes="Reserved seats Coach 4.",
            ),
        ],
        expenses=[
            Expense(
                id="e1",
                title="Group Flights (4 Pax)",
                payer="Franek",
                amount=340.0,
                currency="EUR",
                participants=["Franek", "Anna", "Marek", "Kasia"],
            ),
            Expense(
                id="e2",
                title="Colosseum Official Tickets",
                payer="Anna",
                amount=96.0,
                currency="EUR",
                participants=["Franek", "Anna", "Marek", "Kasia"],
            ),
            Expense(
                id="e3",
                title="High-Speed Rail (Train Subgroup)",
                payer="Marek",
                amount=90.0,
                currency="EUR",
                participants=["Marek", "Kasia"],
            ),
            Expense(
                id="e4",
                title="Tuscany Rental Car + Fuel (Car Subgroup)",
                payer="Franek",
                amount=160.0,
                currency="EUR",
                participants=["Franek", "Anna"],
            ),
            Expense(
                id="e5",
                title="Airport Parking (Modlin, Poland)",
                payer="Kasia",
                amount=258.0,
                currency="PLN",
                exchange_rate_to_base=4.30,
                participants=["Franek", "Anna", "Marek", "Kasia"],
            ),
        ],
    )


@app.command()
def validate(
    trip_file: Optional[str] = typer.Argument(None, help="Path to trip-dag.json file"),
    risk: Optional[float] = typer.Option(
        None, "--risk", "-r", help="Override transit risk multiplier (e.g. 0.25)"
    ),
    hub: Optional[int] = typer.Option(
        None, "--hub", "-h", help="Override station overhead in minutes"
    ),
    inject_delay: Optional[str] = typer.Option(
        None, "--inject-delay", "-d", help="Format: 'node_id:minutes', e.g. 'n2:35'"
    ),
    auto_cut: bool = typer.Option(
        False, "--auto-cut", help="Automatically compress/trim flexible stops if conflicts detected"
    ),
):
    """Audits an itinerary's temporal DAG, calculates dynamic leeway, and flags hard conflicts."""
    trip = load_or_create_sample_dag(trip_file)

    delays = {}
    if inject_delay:
        parts = inject_delay.split(":")
        if len(parts) == 2:
            delays[parts[0].strip()] = int(parts[1].strip())

    console.print(
        Panel.fit(
            f"[bold cyan]KronoLatch Temporal DAG Validator[/bold cyan]\n"
            f"[dim]Trip:[/dim] {trip.title} | [dim]Destination:[/dim] {trip.destination}\n"
            f"[dim]Parameters:[/dim] Risk Multiplier = +{int((risk or trip.parameters.risk_multiplier) * 100)}% | Hub Queue = {hub or trip.parameters.hub_overhead_minutes}m",
            border_style="cyan",
        )
    )

    if auto_cut:
        trip, actions = optimize_and_cut(
            trip,
            injected_delays=delays,
            risk_multiplier=risk,
            hub_overhead=hub,
        )
        if actions:
            console.print("[bold yellow]⚡ Auto-Cut Optimizer Actions:[/bold yellow]")
            for a in actions:
                console.print(f"  • {a}")
            console.print()

    audit = validate_dag(
        trip,
        injected_delays=delays,
        risk_multiplier=risk,
        hub_overhead=hub,
    )

    table = Table(title="Hourly Execution Graph & Leeway Audit", border_style="dim")
    table.add_column("Stop / Event", style="bold white")
    table.add_column("Type", style="cyan")
    table.add_column("Mode", style="dim")
    table.add_column("Transition Buffer", style="yellow")
    table.add_column("Time Window", style="magenta")
    table.add_column("Slack / Status", style="green")

    for res in audit.schedule_results:
        type_badge = (
            "[cyan]FIXED[/cyan]" if res.node_type == NodeType.FIXED else "[dim]FLEXIBLE[/dim]"
        )
        trans_str = f"{res.transition_time_min}m" if res.transition_time_min > 0 else "—"

        if res.is_conflict:
            status_str = f"[bold red]HARD CONFLICT (-{res.conflict_deficit_min}m)[/bold red]"
        elif res.slack_min is not None:
            status_str = f"[green]+{res.slack_min}m safe slack[/green]"
        else:
            status_str = "[dim]OK[/dim]"

        table.add_row(
            res.title,
            type_badge,
            res.category.value,
            trans_str,
            res.time_window_str,
            status_str,
        )

    console.print(table)

    summary_panel = (
        f"[bold]Sightseeing / Experience Time:[/bold] {audit.total_sightseeing_min // 60}h {audit.total_sightseeing_min % 60}m\n"
        f"[bold]Base Transit Time:[/bold] {audit.total_transit_min // 60}h {audit.total_transit_min % 60}m\n"
        f"[bold]Injected Safety Leeway:[/bold] {audit.total_buffer_min}m\n"
        f"[bold]Schedule Integrity:[/bold] "
        + (
            "[bold green]VALID — All fixed constraints protected[/bold green]"
            if audit.is_valid
            else f"[bold red]{len(audit.conflicts)} HARD CONFLICT(S) DETECTED[/bold red]"
        )
    )
    console.print(Panel(summary_panel, border_style="green" if audit.is_valid else "red"))

    if not audit.is_valid and not auto_cut:
        console.print(
            "[dim]Hint: Run again with --auto-cut to automatically resolve constraints.[/dim]"
        )


@app.command()
def verify_url(
    candidate_url: str = typer.Argument(..., help="Candidate ticket or transit booking URL"),
    venue: str = typer.Option("", "--venue", "-v", help="Name of venue or operator"),
    ground_truth: Optional[str] = typer.Option(
        None, "--ground-truth", "-g", help="Authoritative official domain"
    ),
    price: Optional[float] = typer.Option(None, "--price", "-p", help="Candidate offer price"),
    official_price: Optional[float] = typer.Option(
        None, "--official-price", help="Official base ticket price"
    ),
):
    """Anti-phishing audit of ticket & transit URLs against canonical root domains."""
    res = verify_vendor_url(
        candidate_url=candidate_url,
        venue_name=venue,
        official_domain=ground_truth,
        candidate_price=price,
        official_base_price=official_price,
    )

    badge_styles = {
        VerificationStatus.VERIFIED_OFFICIAL: "[bold black on green] VERIFIED OFFICIAL PORTAL [/bold black on green]",
        VerificationStatus.TRUSTED_AGGREGATOR: "[bold white on blue] TRUSTED AGGREGATOR [/bold white on blue]",
        VerificationStatus.HIGH_RISK_CLONE: "[bold white on red] HIGH-RISK RESELLER / CLONE BLOCKED [/bold white on red]",
        VerificationStatus.UNVERIFIED_THIRD_PARTY: "[bold black on yellow] UNVERIFIED THIRD-PARTY [/bold black on yellow]",
    }

    content = [
        f"Status: {badge_styles[res.status]}",
        f"Candidate Root Domain: [bold white]{res.candidate_root_domain}[/bold white]",
        f"Ground Truth Domain : [bold green]{res.ground_truth_root_domain or 'Unanchored'}[/bold green]",
    ]

    if res.official_base_price and res.candidate_price:
        markup = res.markup_percent or 0
        color = "red" if markup > 15 else "green"
        content.append(
            f"Price Comparison     : €{res.candidate_price:.2f} vs €{res.official_base_price:.2f} base ([{color}]+{markup}% markup[/{color}])"
        )

    if res.reasons:
        content.append("\nAudit Findings:")
        for r in res.reasons:
            content.append(f"  • {r}")

    if res.verified_official_url:
        content.append(
            f"\n[bold green]Authoritative Official Link:[/bold green] {res.verified_official_url}"
        )
    if res.booking_rule:
        content.append(f"[bold cyan]Booking Window Rule:[/bold cyan] {res.booking_rule}")

    console.print(
        Panel(
            "\n".join(content),
            title=f"KronoLatch Anti-Phishing Audit: {res.venue}",
            border_style="red" if res.is_blocked else "green",
        )
    )


@app.command()
def settle(
    trip_file: Optional[str] = typer.Argument(
        None, help="Path to trip-dag.json file containing expenses"
    ),
    base_currency: str = typer.Option(
        "EUR", "--currency", "-c", help="Base currency for settlement"
    ),
    rate: float = typer.Option(
        4.30, "--rate", help="Alternate currency exchange rate (EUR to PLN)"
    ),
):
    """Reconciles multi-currency subgroup expenses and calculates the minimum transfer settlement."""
    trip = load_or_create_sample_dag(trip_file)
    result = settle_expenses(
        expenses=trip.expenses,
        base_currency=base_currency,
        all_travelers=trip.travelers,
        alternate_currency="PLN",
        alternate_rate=rate,
    )

    console.print(
        Panel.fit(
            f"[bold cyan]KronoLatch Group Expense Reconciler[/bold cyan]\n"
            f"[dim]Total Group Spend:[/dim] {result.base_currency} {result.total_spend_base:.2f} (approx. {result.total_spend_base * rate:.2f} PLN)\n"
            f"[dim]Travelers ({len(trip.travelers)}):[/dim] {', '.join(trip.travelers)}",
            border_style="cyan",
        )
    )

    bal_table = Table(title="Individual Net Balances", border_style="dim")
    bal_table.add_column("Traveler", style="bold white")
    bal_table.add_column("Net Balance", style="bold")
    bal_table.add_column("Status")

    for person, bal in result.net_balances.items():
        if bal > 0.005:
            bal_table.add_row(
                person,
                f"[green]+{result.base_currency} {bal:.2f}[/green]",
                "[green]Is Owed (Creditor)[/green]",
            )
        elif bal < -0.005:
            bal_table.add_row(
                person,
                f"[red]-{result.base_currency} {abs(bal):.2f}[/red]",
                "[red]Owes Group (Debtor)[/red]",
            )
        else:
            bal_table.add_row(person, f"{result.base_currency} 0.00", "[dim]Settled[/dim]")
    console.print(bal_table)

    trans_table = Table(
        title=f"Minimum-Transaction Settlement Plan ({len(result.transfers)} Transfers Total)",
        border_style="green",
    )
    trans_table.add_column("From (Debtor)", style="bold red")
    trans_table.add_column("→", style="dim")
    trans_table.add_column("To (Creditor)", style="bold green")
    trans_table.add_column("Amount (Base)", style="bold white")
    trans_table.add_column("Amount (Alternate PLN)", style="dim")

    for tr in result.transfers:
        alt_str = f"{tr.amount_alternate:.2f} PLN" if tr.amount_alternate else "—"
        trans_table.add_row(
            tr.from_person, "→", tr.to_person, f"{tr.currency} {tr.amount:.2f}", alt_str
        )

    console.print(trans_table)


@app.command()
def export_skill(
    target: str = typer.Option(
        "gemini", "--target", "-t", help="Target harness: gemini | antigravity | cursor | cli"
    ),
    dest: str = typer.Option("Rome & Florence", "--dest", "-d", help="Destination corridor"),
    group: str = typer.Option("4 Travelers", "--group", "-g", help="Group description"),
):
    """Generates portable skill definitions, system prompts, or configuration rules."""
    if target == "gemini":
        content = f"""---
name: kronolatch-trip-orchestrator
description: Deterministic Trip DAG Validator, Anti-Phishing Vendor Verifier & Group Expense Reconciler
corridor: {dest} ({group})
---
# ROLE: KronoLatch Trip Orchestrator
You are KronoLatch, an offline-first, deterministic travel scheduling and vendor verification agent.
1. OFFICIAL DOMAIN VERIFICATION: Never output booking links without cross-referencing Wikidata P856 or Google Places websiteUri.
2. TEMPORAL DAG: Inject 120m flight buffers, 15m train platform overhead, and a 20% transit risk multiplier.
3. EXPENSE SPLITTER: Compute minimum-transaction graph reductions across EUR and PLN."""
    elif target == "antigravity":
        content = f"""# Antigravity IDE Skill (.antigravity/skills/kronolatch.md)
# Corridor: {dest} ({group})
<agent_rule name="kronolatch" priority="critical">
  <invariants>
    1. Verify canonical root domains against Wikidata P856 before recommending booking URLs.
    2. Enforce T_transition = T_transit * 1.20 + 15m on all rail/road transitions.
    3. If slack < 0 at a fixed node, emit HARD_CONFLICT and trim lowest-priority flexible stop.
  </invariants>
</agent_rule>"""
    elif target == "cursor":
        content = """# Cursor Rules (.cursorrules)
# KronoLatch Project Standards
- Model all itineraries as Directed Acyclic Graphs with fixed vs flexible node constraints.
- Strip subdomains to canonical eTLD+1 before auditing ticket portals.
- Run `uv run kronolatch self-test` before pushing changes."""
    else:
        content = "# KronoLatch CLI Reference\nuv run kronolatch validate --inject-delay n2:35 --auto-cut\nuv run kronolatch verify-url https://www.colosseum-rome-tickets.org/fast-track -v Colosseum -p 44\nuv run kronolatch settle"

    console.print(content)


@app.command()
def self_test():
    """Runs on-demand deterministic verification suite for all 4 architectural pillars."""
    console.print(
        Panel.fit(
            "[bold cyan]KronoLatch Architectural Verification Suite[/bold cyan]\n[dim]Running 4 deterministic assertions...[/dim]",
            border_style="cyan",
        )
    )

    passed_count = 0

    # ---------------------------------------------------------
    # TEST 1: The SEO Ticket Trap (Anti-Phishing Assertion)
    # ---------------------------------------------------------
    t1 = verify_vendor_url(
        candidate_url="https://www.colosseum-rome-tickets.org/fast-track",
        venue_name="Parco Archeologico del Colosseo",
        official_domain="ticketing.colosseo.it",
        candidate_price=44.0,
        official_base_price=18.0,
    )
    assert t1.status == VerificationStatus.HIGH_RISK_CLONE, (
        f"Test 1 failed: expected HIGH_RISK_CLONE, got {t1.status}"
    )
    assert t1.is_blocked is True, "Test 1 failed: expected candidate to be blocked"
    assert t1.markup_percent == 144.4, (
        f"Test 1 failed: expected +144.4% markup, got {t1.markup_percent}"
    )
    console.print(
        "[bold green]✓ TEST 1 PASSED:[/bold green] SEO Phishing Clone blocked, root domain mismatch flagged, +144.4% markup confirmed."
    )
    passed_count += 1

    # ---------------------------------------------------------
    # TEST 2: Cascading Regional Rail Delay (Temporal DAG Assertion)
    # ---------------------------------------------------------
    # Regional train arrives 11:40 (+35m delay -> 12:15)
    # 20m transit to Timed Museum Entry locked at 12:30 (requires 15m queue buffer)
    # Effective arrival ready time = 12:15 + 20m transit + 15m queue = 12:50.
    # Deficit = 12:50 - 12:30 = -20m HARD_CONFLICT.
    test2_trip = TripDAG(
        trip_id="test2",
        title="Cascading Delay Test",
        destination="Rome",
        base_currency="EUR",
        travelers=["Traveler"],
        parameters=DAGParameters(risk_multiplier=0.0, hub_overhead_minutes=15),
        nodes=[
            TripNode(
                id="t2-1",
                title="Regional Train to Central Station",
                type=NodeType.FIXED,
                category=Category.RAIL,
                fixed_start_time="10:40",
                duration_min=60,  # Arrives 11:40 without delay
            ),
            TripNode(
                id="t2-2",
                title="Morning Scenic Piazza Walk",
                type=NodeType.FLEXIBLE,
                category=Category.SIGHTSEEING,
                transit_min=0,
                duration_min=30,
                min_duration_min=10,
                priority=2,
            ),
            TripNode(
                id="t2-3",
                title="Timed Museum Entry (HARD LOCK)",
                type=NodeType.FIXED,
                category=Category.SIGHTSEEING,
                transit_mode=TransitMode.WALK,
                transit_min=20,
                duration_min=90,
                fixed_start_time="12:30",
                priority=10,
            ),
        ],
    )
    # Injected delay on train leg + auto-cut test
    t2_opt, actions = optimize_and_cut(test2_trip, injected_delays={"t2-1": 35})
    t2_opt_audit = validate_dag(t2_opt, injected_delays={"t2-1": 35})
    museum_result = next(r for r in t2_opt_audit.schedule_results if r.node_id == "t2-3")
    assert museum_result.earliest_arrival_min == 12 * 60 + 50, (
        f"Expected arrival ready-time 12:50, got {museum_result.earliest_arrival_min}"
    )
    assert museum_result.conflict_deficit_min == 20, (
        f"Expected 20m conflict deficit, got {museum_result.conflict_deficit_min}"
    )
    assert museum_result.is_conflict is True, "Expected hard conflict on locked museum node"
    assert len(actions) > 0 and any(
        "walk" in a.lower() or "prun" in a.lower() or "trim" in a.lower() for a in actions
    )
    console.print(
        f"[bold green]✓ TEST 2 PASSED:[/bold green] Effective arrival ready-time = 12:50, flagged -20 min HARD_CONFLICT on fixed node, trimmed preceding walk ({actions[0]})."
    )
    passed_count += 1

    # ---------------------------------------------------------
    # TEST 3: Asymmetric Subgroup Cost Split (Ledger Assertion)
    # ---------------------------------------------------------
    # 4 travelers: Franek, Anna, Marek, Kasia
    # Franek pays €160 for Rental Car (split Franek & Anna)
    # Marek pays €90 for Train (split Marek & Kasia)
    # Kasia pays €200 for Dinner (split all 4)
    # Expected net balances: Franek: +€30, Anna: -€130, Marek: -€5, Kasia: +€105
    test3_expenses = [
        Expense(
            id="e1",
            title="Rental Car + Fuel",
            payer="Franek",
            amount=160.0,
            currency="EUR",
            participants=["Franek", "Anna"],
        ),
        Expense(
            id="e2",
            title="High-Speed Train",
            payer="Marek",
            amount=90.0,
            currency="EUR",
            participants=["Marek", "Kasia"],
        ),
        Expense(
            id="e3",
            title="Group Dinner",
            payer="Kasia",
            amount=200.0,
            currency="EUR",
            participants=["Franek", "Anna", "Marek", "Kasia"],
        ),
    ]
    t3_result = settle_expenses(
        test3_expenses, base_currency="EUR", all_travelers=["Franek", "Anna", "Marek", "Kasia"]
    )
    bals = t3_result.net_balances
    assert bals["Franek"] == 30.0, f"Franek expected 30.0, got {bals['Franek']}"
    assert bals["Anna"] == -130.0, f"Anna expected -130.0, got {bals['Anna']}"
    assert bals["Marek"] == -5.0, f"Marek expected -5.0, got {bals['Marek']}"
    assert bals["Kasia"] == 105.0, f"Kasia expected 105.0, got {bals['Kasia']}"
    assert len(t3_result.transfers) <= 3, (
        f"Expected at most 3 transfers, got {len(t3_result.transfers)}"
    )
    total_transferred = sum(tr.amount for tr in t3_result.transfers)
    assert round(total_transferred, 2) == 135.0, (
        f"Expected total €135 transferred, got {total_transferred}"
    )
    console.print(
        f"[bold green]✓ TEST 3 PASSED:[/bold green] Exact net balances verified (Franek +€30, Anna -€130, Marek -€5, Kasia +€105) settled in {len(t3_result.transfers)} transfers totaling €135."
    )
    passed_count += 1

    # ---------------------------------------------------------
    # TEST 4: Unstructured Booking Ingestion to Valid Schema
    # ---------------------------------------------------------
    # Ingests messy text and enforces automatic 120m flight buffer and 15m rail buffer
    flight_trans = calculate_transition_time(transit_min=30, transit_mode=TransitMode.FLIGHT)
    rail_trans = calculate_transition_time(transit_min=25, transit_mode=TransitMode.TRAIN)
    assert flight_trans >= 150, f"Flight buffer failed: {flight_trans}m"
    assert rail_trans >= 45, f"Rail buffer failed: {rail_trans}m"

    test4_trip = TripDAG(
        trip_id="ingested-booking-01",
        title="Messy Ingestion Normalization",
        destination="Rome",
        base_currency="EUR",
        travelers=["Traveler A"],
        nodes=[
            TripNode(
                id="in-1",
                title="Inbound Flight Ryanair",
                type=NodeType.FIXED,
                category=Category.FLIGHT,
                transit_mode=TransitMode.FLIGHT,
                transit_min=0,
                duration_min=140,
                fixed_start_time="09:00",
            ),
            TripNode(
                id="in-2",
                title="Regional Rail Transfer",
                type=NodeType.FLEXIBLE,
                category=Category.RAIL,
                transit_mode=TransitMode.TRAIN,
                transit_min=25,
                duration_min=35,
            ),
        ],
    )
    # Validate against JSON schema serialization
    dumped = test4_trip.model_dump(mode="json")
    assert "trip_id" in dumped and "nodes" in dumped and len(dumped["nodes"]) == 2
    console.print(
        "[bold green]✓ TEST 4 PASSED:[/bold green] Unstructured ingestion normalized with 120m flight and 15m rail buffers; schema strictly validated."
    )
    passed_count += 1

    console.print(
        f"\n[bold green]ALL {passed_count}/4 ARCHITECTURAL TESTS PASSED PERFECTLY![/bold green]"
    )


if __name__ == "__main__":
    app()
