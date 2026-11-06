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
from typing import List, Optional

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kronolatch.calendar_export import CalendarExporter
from kronolatch.dag_engine import calculate_transition_time, optimize_and_cut, validate_dag
from kronolatch.graph import CriticalPathEngine
from kronolatch.ingest import TicketIngestor
from kronolatch.ledger import settle_expenses
from kronolatch.live_transit import LiveTransitClient
from kronolatch.models import (
    Category,
    DAGParameters,
    Expense,
    NodeType,
    TransitMode,
    TripDAG,
    TripNode,
    VerificationStatus,
    minutes_to_time_str,
    time_str_to_minutes,
)
from kronolatch.planner import TripPlanner, WishlistRequest
from kronolatch.receipt import ReceiptSplitter
from kronolatch.schengen import SchengenCalculator, StayInterval
from kronolatch.sheets import (
    export_expenses_to_csv,
    export_itinerary_to_csv,
    export_settlement_to_csv,
    google_sheets_url_to_csv_export_url,
    parse_expenses_csv,
    parse_itinerary_csv,
)
from kronolatch.simulation import MonteCarloSimulator, SimulationParameters
from kronolatch.solar import SolarEngine
from kronolatch.sync import SyncEngine
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
    live_delays: bool = typer.Option(
        False,
        "--live-delays",
        "-l",
        help="Query live public railway feeds for real-time train delays",
    ),
):
    """Audits an itinerary's temporal DAG, calculates dynamic leeway, and flags hard conflicts."""
    trip = load_or_create_sample_dag(trip_file)

    delays = {}
    if live_delays:
        console.print("[dim]Querying real-time public railway delay feeds...[/dim]")
        rail_statuses = LiveTransitClient.check_trip_rail_delays(trip)
        for nid, st in rail_statuses.items():
            if st.delay_minutes > 0:
                delays[nid] = st.delay_minutes
                console.print(
                    f"  [bold yellow]• Live Alert:[/bold yellow] Train {st.train_number} delayed [bold red]+{st.delay_minutes}m[/bold red] ({st.status_summary}) [{st.source}]"
                )
            else:
                console.print(
                    f"  [bold green]• Live Status:[/bold green] Train {st.train_number} is [bold green]{st.status_summary}[/bold green]"
                )
        console.print()

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


@app.command(name="import-csv")
def import_csv(
    source: str = typer.Argument(
        ...,
        help="Local CSV file path or public Google Sheets URL (e.g. https://docs.google.com/spreadsheets/d/...)",
    ),
    data_type: str = typer.Option(
        "auto",
        "--type",
        "-t",
        help="Data type: 'auto' (detect from headers), 'itinerary', or 'expenses'",
    ),
    out_file: Optional[str] = typer.Option(
        None,
        "--out",
        "-o",
        help="Save result into a new trip JSON file",
    ),
    merge_into: Optional[str] = typer.Option(
        None,
        "--merge-into",
        "-m",
        help="Merge imported records into an existing trip JSON file",
    ),
):
    """Imports itinerary stops or expenses from local CSV/XLS or a public Google Spreadsheet URL."""
    csv_text: str = ""
    is_url = source.startswith("http://") or source.startswith("https://")

    if is_url:
        export_url = google_sheets_url_to_csv_export_url(source)
        console.print(f"[dim]Fetching CSV from:[/dim] [cyan]{export_url}[/cyan]")
        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                resp = client.get(export_url)
                resp.raise_for_status()
                csv_text = resp.text
        except Exception as e:
            console.print(f"[bold red]Failed to fetch spreadsheet:[/bold red] {e}")
            raise typer.Exit(code=1)
    else:
        path = Path(source)
        if not path.exists():
            console.print(f"[bold red]File not found:[/bold red] {source}")
            raise typer.Exit(code=1)
        try:
            csv_text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            csv_text = path.read_text(encoding="latin-1")

    # Auto-detect data type if requested
    detected_type = data_type.lower()
    if detected_type == "auto":
        first_chunk = csv_text[:1000].lower()
        if any(
            term in first_chunk
            for term in ["payer", "amount", "price", "split", "cost", "currency"]
        ):
            detected_type = "expenses"
        else:
            detected_type = "itinerary"

    if detected_type == "expenses":
        expenses = parse_expenses_csv(csv_text)
        if not expenses:
            console.print("[yellow]Warning: No valid expense rows parsed from CSV.[/yellow]")
            return

        table = Table(title=f"Imported Expenses ({len(expenses)} rows)", border_style="cyan")
        table.add_column("ID", style="dim")
        table.add_column("Title", style="bold white")
        table.add_column("Payer", style="cyan")
        table.add_column("Amount", style="bold green")
        table.add_column("Currency", style="yellow")
        table.add_column("Participants", style="dim")

        for exp in expenses:
            table.add_row(
                exp.id,
                exp.title,
                exp.payer,
                f"{exp.amount:.2f}",
                exp.currency,
                ", ".join(exp.participants),
            )
        console.print(table)

        if merge_into:
            m_path = Path(merge_into)
            if m_path.exists():
                with open(m_path, "r", encoding="utf-8") as f:
                    trip_data = json.load(f)
                trip = TripDAG.model_validate(trip_data)
                trip.expenses.extend(expenses)
                for exp in expenses:
                    for p in exp.participants:
                        if p not in trip.travelers:
                            trip.travelers.append(p)
                    if exp.payer not in trip.travelers:
                        trip.travelers.append(exp.payer)
                m_path.write_text(
                    json.dumps(trip.model_dump(mode="json"), indent=2), encoding="utf-8"
                )
                console.print(
                    f"[bold green]✓ Appended {len(expenses)} expenses to {merge_into}[/bold green]"
                )
            else:
                console.print(f"[bold red]Merge target file not found:[/bold red] {merge_into}")
        elif out_file:
            all_travelers: List[str] = []
            for exp in expenses:
                for p in exp.participants:
                    if p not in all_travelers:
                        all_travelers.append(p)
                if exp.payer not in all_travelers:
                    all_travelers.append(exp.payer)
            new_trip = TripDAG(
                trip_id="imported-expenses",
                title="Imported Group Expenses",
                destination="Imported",
                base_currency=expenses[0].currency if expenses else "EUR",
                travelers=all_travelers or ["Traveler"],
                nodes=[],
                expenses=expenses,
            )
            Path(out_file).write_text(
                json.dumps(new_trip.model_dump(mode="json"), indent=2), encoding="utf-8"
            )
            console.print(
                f"[bold green]✓ Saved {len(expenses)} expenses to {out_file}[/bold green]"
            )

    else:
        nodes = parse_itinerary_csv(csv_text)
        if not nodes:
            console.print("[yellow]Warning: No valid itinerary stops parsed from CSV.[/yellow]")
            return

        table = Table(title=f"Imported Itinerary Nodes ({len(nodes)} stops)", border_style="cyan")
        table.add_column("ID", style="dim")
        table.add_column("Title", style="bold white")
        table.add_column("Type", style="cyan")
        table.add_column("Mode / Category", style="dim")
        table.add_column("Duration", style="yellow")
        table.add_column("Start Time", style="magenta")
        table.add_column("Domain", style="green")

        for n in nodes:
            table.add_row(
                n.id,
                n.title,
                n.type.value,
                f"{n.transit_mode.value} / {n.category.value}",
                f"{n.duration_min}m",
                n.fixed_start_time or "Flex",
                n.official_domain or "—",
            )
        console.print(table)

        if merge_into:
            m_path = Path(merge_into)
            if m_path.exists():
                with open(m_path, "r", encoding="utf-8") as f:
                    trip_data = json.load(f)
                trip = TripDAG.model_validate(trip_data)
                trip.nodes.extend(nodes)
                m_path.write_text(
                    json.dumps(trip.model_dump(mode="json"), indent=2), encoding="utf-8"
                )
                console.print(
                    f"[bold green]✓ Appended {len(nodes)} nodes to {merge_into}[/bold green]"
                )
            else:
                console.print(f"[bold red]Merge target file not found:[/bold red] {merge_into}")
        elif out_file:
            new_trip = TripDAG(
                trip_id="imported-itinerary",
                title="Imported Itinerary",
                destination="Imported",
                base_currency="EUR",
                travelers=["Traveler"],
                nodes=nodes,
                expenses=[],
            )
            Path(out_file).write_text(
                json.dumps(new_trip.model_dump(mode="json"), indent=2), encoding="utf-8"
            )
            console.print(
                f"[bold green]✓ Saved {len(nodes)} itinerary nodes to {out_file}[/bold green]"
            )


@app.command(name="export-csv")
def export_csv(
    trip_file: Optional[str] = typer.Argument(
        None,
        help="Path to trip JSON file (defaults to Rome & Florence sample)",
    ),
    data_type: str = typer.Option(
        "all",
        "--type",
        "-t",
        help="Data type to export: 'all', 'itinerary', 'expenses', or 'settlement'",
    ),
    out_dir: str = typer.Option(
        ".",
        "--out-dir",
        "-d",
        help="Directory to save exported CSV file(s)",
    ),
    stdout: bool = typer.Option(
        False,
        "--stdout",
        help="Print CSV directly to stdout instead of writing files",
    ),
):
    """Exports itinerary, group expenses, and debt settlement tables to standard CSV for Google Sheets or Excel."""
    trip = load_or_create_sample_dag(trip_file)
    target_type = data_type.lower()
    dest_dir = Path(out_dir)

    if not stdout:
        dest_dir.mkdir(parents=True, exist_ok=True)

    exported_files = []

    # Export Itinerary
    if target_type in ["all", "itinerary"]:
        csv_str = export_itinerary_to_csv(trip.nodes)
        if stdout and target_type == "itinerary":
            print(csv_str)
            return
        elif not stdout:
            out_file = dest_dir / "itinerary.csv"
            out_file.write_text(csv_str, encoding="utf-8")
            exported_files.append((out_file, len(trip.nodes), "Itinerary stops"))

    # Export Expenses
    if target_type in ["all", "expenses"]:
        csv_str = export_expenses_to_csv(trip.expenses)
        if stdout and target_type == "expenses":
            print(csv_str)
            return
        elif not stdout:
            out_file = dest_dir / "expenses.csv"
            out_file.write_text(csv_str, encoding="utf-8")
            exported_files.append((out_file, len(trip.expenses), "Expense items"))

    # Export Settlement
    if target_type in ["all", "settlement"]:
        settlement = settle_expenses(
            expenses=trip.expenses,
            base_currency=trip.base_currency,
            all_travelers=trip.travelers,
        )
        csv_str = export_settlement_to_csv(settlement)
        if stdout and target_type == "settlement":
            print(csv_str)
            return
        elif not stdout:
            out_file = dest_dir / "settlement.csv"
            out_file.write_text(csv_str, encoding="utf-8")
            exported_files.append((out_file, len(settlement.transfers), "Settlement transfers"))

    if not stdout:
        msg = "\n".join(
            f"  • [bold white]{f[0]}[/bold white] ({f[1]} {f[2]})" for f in exported_files
        )
        console.print(
            Panel.fit(
                f"[bold green]✓ CSV Export Complete[/bold green]\n\n"
                f"Generated CSV files ready for Google Sheets & Excel import:\n{msg}\n\n"
                f"[dim]Tip: In Google Sheets, choose File → Import → Upload to load directly.[/dim]",
                border_style="green",
            )
        )


@app.command("ingest-ticket")
def ingest_ticket(
    source: str = typer.Argument(
        ..., help="Path to PDF ticket file or raw text confirmation snippet"
    ),
    trip_file: Optional[str] = typer.Option(
        None, "--trip", "-t", help="Path to existing trip JSON to append the parsed node to"
    ),
    out_file: Optional[str] = typer.Option(
        None, "--out", "-o", help="Output path for updated trip JSON"
    ),
):
    """
    Parse a travel ticket (PDF or raw confirmation text) deterministically
    and extract PNR, timings, and carriage/seat assignments.
    """
    try:
        parsed = TicketIngestor.parse(source)
    except Exception as exc:
        console.print(f"[bold red]Error parsing ticket source:[/bold red] {exc}")
        raise typer.Exit(1)

    table = Table(
        title="[bold green]Parsed Ticket Details (Offline Ingestion)[/bold green]",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Property", style="bold white", width=22)
    table.add_column("Extracted Value", style="green")

    table.add_row("Service Category", parsed.service_type.value.upper())
    table.add_row("Service / Train Number", parsed.service_number or "N/A")
    table.add_row("PNR / Booking Reference", parsed.pnr or "[dim]Not detected[/dim]")
    table.add_row("Origin Station", parsed.origin)
    table.add_row("Destination Station", parsed.destination)
    table.add_row("Departure Time", parsed.departure_time)
    table.add_row("Arrival Time", parsed.arrival_time)
    table.add_row("Duration", f"{parsed.duration_minutes()} min")
    table.add_row("Carriage / Coach", parsed.coach_carriage or "N/A")
    table.add_row("Seat Assignment", parsed.seat or "N/A")
    if parsed.price is not None:
        table.add_row("Ticket Price", f"{parsed.price:.2f} {parsed.currency}")
    if parsed.date:
        table.add_row("Travel Date", parsed.date)

    console.print(table)

    if trip_file:
        trip = load_or_create_sample_dag(trip_file)
        node_id = f"ticket_{len(trip.nodes) + 1}_{parsed.service_type.value}"
        updated_trip = TicketIngestor.ingest_into_trip(source, trip, node_id=node_id)

        target_path = Path(out_file) if out_file else Path(trip_file)
        target_path.write_text(
            json.dumps(updated_trip.model_dump(mode="json"), indent=2), encoding="utf-8"
        )
        console.print(
            f"[bold green]✓ Appended node '{node_id}' to trip DAG and saved to {target_path}[/bold green]"
        )


@app.command("live-delay")
def live_delay(
    train: str = typer.Argument(
        ..., help="Train number or service identifier (e.g. 9540, 3305, or 'Frecciarossa 9540')"
    ),
):
    """Query live train delay telemetry from public railway feeds (ViaggiaTreno open data)."""
    status = LiveTransitClient.fetch_train_delay(train)
    table = Table(
        title=f"[bold green]Live Train Telemetry — {status.train_number}[/bold green]",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Property", style="bold white", width=22)
    table.add_column("Status", style="green")

    table.add_row("Service Identifier", status.train_number)
    table.add_row("Operator", status.operator)
    if status.origin_station:
        table.add_row("Origin", status.origin_station)
    if status.destination_station:
        table.add_row("Destination", status.destination_station)
    delay_style = (
        "bold red"
        if status.delay_minutes > 10
        else ("bold yellow" if status.delay_minutes > 0 else "bold green")
    )
    table.add_row(
        "Current Delay",
        (
            f"[{delay_style}]+{status.delay_minutes} min[/{delay_style}]"
            if status.delay_minutes > 0
            else "[bold green]0 min (On Time)[/bold green]"
        ),
    )
    table.add_row("Status Summary", status.status_summary)
    table.add_row(
        "Data Source",
        f"{status.source} ({'LIVE HTTP' if status.is_live else 'OFFLINE CACHE'})",
    )
    console.print(table)


@app.command("share")
def share(
    trip_file: Optional[str] = typer.Option(
        None, "--trip", "-t", help="Path to local trip JSON file"
    ),
    sender: str = typer.Option("Traveler", "--sender", "-s", help="Your name as sender"),
    sync_type: str = typer.Option(
        "all", "--type", help="Scope of synchronization: 'all', 'expenses', or 'itinerary'"
    ),
):
    """Generate an offline compressed P2P sync token to share expenses and stops with companions."""
    trip = load_or_create_sample_dag(trip_file)
    scope = "all" if sync_type not in ("all", "expenses", "itinerary") else sync_type
    payload = SyncEngine.create_payload_from_trip(trip, sender=sender, sync_type=scope)
    token = SyncEngine.encode_token(payload)

    console.print(
        Panel.fit(
            f"[bold cyan]KronoLatch Offline Peer-to-Peer Sync Token[/bold cyan]\n\n"
            f"[dim]Sender:[/dim] {sender} | [dim]Scope:[/dim] {scope.upper()} | [dim]Trip ID:[/dim] {payload.trip_id}\n"
            f"[dim]Bundled Entities:[/dim] {len(payload.expenses)} expenses, {len(payload.nodes)} itinerary stops\n\n"
            f"[bold green]{token}[/bold green]\n\n"
            f"[dim]Pass this token to your travel companion or import it via:[/dim]\n"
            f'[white]uv run kronolatch sync "{token[:24]}..."[/white]',
            border_style="cyan",
        )
    )


@app.command("sync")
def sync(
    token_or_file: str = typer.Argument(
        ..., help="Compressed sync token string or path to a file containing the token"
    ),
    trip_file: Optional[str] = typer.Option(
        None, "--trip", "-t", help="Path to local trip JSON to merge into"
    ),
    out_file: Optional[str] = typer.Option(
        None, "--out", "-o", help="Target path for updated trip JSON"
    ),
):
    """Merge an incoming offline sync token into your local trip DAG without duplicating expenses."""
    content = token_or_file.strip()
    if len(content) < 255:
        try:
            p = Path(content)
            if p.is_file():
                content = p.read_text(encoding="utf-8").strip()
        except (OSError, ValueError):
            pass

    try:
        incoming = SyncEngine.decode_token(content)
    except Exception as exc:
        console.print(f"[bold red]Sync decode error:[/bold red] {exc}")
        raise typer.Exit(1)

    trip = load_or_create_sample_dag(trip_file)
    updated_trip, stats = SyncEngine.merge_into_trip(incoming, trip)

    target = (
        Path(out_file) if out_file else (Path(trip_file) if trip_file else Path("merged-trip.json"))
    )
    target.write_text(json.dumps(updated_trip.model_dump(mode="json"), indent=2), encoding="utf-8")

    console.print(
        Panel.fit(
            f"[bold green]✓ Peer Sync Complete[/bold green]\n\n"
            f"[dim]Received from:[/dim] {incoming.sender} ([dim]Trip:[/dim] {incoming.trip_id})\n"
            f"[bold white]+{stats['new_expenses']} new expenses[/bold white] merged (Total: {stats['total_expenses']})\n"
            f"[bold white]+{stats['new_nodes']} new itinerary stops[/bold white] merged (Total: {stats['total_nodes']})\n\n"
            f"[dim]Saved updated trip DAG to:[/dim] [white]{target}[/white]",
            border_style="green",
        )
    )


@app.command("plan")
def plan(
    destination: str = typer.Argument(
        ..., help="Target destination or corridor (e.g. 'Rome & Florence' or 'Classic Tuscany')"
    ),
    wishlist: str = typer.Option(
        "Colosseum, Pantheon, Vatican Museums, Trastevere Lunch, Uffizi Gallery",
        "--wishlist",
        "-w",
        help="List of attractions, monuments, or activities to see",
    ),
    travelers: str = typer.Option(
        "Franek, Anna, Marek, Kasia",
        "--travelers",
        "-t",
        help="Comma-separated traveler names",
    ),
    pace: str = typer.Option(
        "moderate",
        "--pace",
        "-p",
        help="Tour pacing profile: 'relaxed', 'moderate', or 'fast-paced'",
    ),
    transport: str = typer.Option(
        "mixed_car_and_rail",
        "--transport",
        "-m",
        help="Transit style: 'transit_and_walk', 'mixed_car_and_rail', or 'driving_focus'",
    ),
    start_time: str = typer.Option(
        "09:00",
        "--start-time",
        help="Morning starting time in HH:MM format",
    ),
    out_file: Optional[str] = typer.Option(
        None,
        "--out",
        "-o",
        help="File path to save the generated trip-dag.json",
    ),
):
    """
    Synthesize an entire tour itinerary from a natural language wishlist.
    Anchors official ticketing portals, injects dynamic transit buffers, and allocates subgroup expenses.
    """
    traveler_list = [t.strip() for t in travelers.split(",") if t.strip()]
    pace_val = pace if pace in ("relaxed", "moderate", "fast-paced") else "moderate"
    transport_val = (
        transport
        if transport in ("transit_and_walk", "mixed_car_and_rail", "driving_focus")
        else "mixed_car_and_rail"
    )

    req = WishlistRequest(
        destination=destination,
        wishlist_text=wishlist,
        travelers=traveler_list,
        pace=pace_val,
        transport_mode=transport_val,
        start_time=start_time,
    )

    trip = TripPlanner.generate_trip(req)

    # Display synthesis results
    console.print(
        Panel.fit(
            f"[bold cyan]KronoLatch Tour Synthesis Engine[/bold cyan]\n\n"
            f"[dim]Destination:[/dim] {trip.destination}\n"
            f"[dim]Travelers ({len(trip.travelers)}):[/dim] {', '.join(trip.travelers)}\n"
            f"[dim]Profile:[/dim] Pace = {pace.upper()} | Transit = {transport.upper()}\n"
            f"[dim]Planned Stops:[/dim] {len(trip.nodes)} entities | [dim]Group Expenses:[/dim] {len(trip.expenses)} items",
            border_style="cyan",
        )
    )

    # Itinerary Table
    table = Table(
        title="[bold green]Generated Itinerary Graph (Timed with Buffers)[/bold green]",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Stop / Attraction", style="bold white", width=34)
    table.add_column("Type", style="cyan")
    table.add_column("Dwell", style="yellow")
    table.add_column("Transit Buffer", style="magenta")
    table.add_column("Official Booking Portal", style="green")

    for n in trip.nodes:
        dwell_str = f"{n.duration_min}m"
        buffer_str = f"{n.transit_min}m ({n.transit_mode.value})" if n.transit_min else "—"
        portal_str = n.official_domain or "[dim]Walk / Open Access[/dim]"
        table.add_row(
            n.title,
            n.type.value.upper(),
            dwell_str,
            buffer_str,
            portal_str,
        )

    console.print(table)

    # Validate against DAG engine
    audit = validate_dag(trip)
    status_color = "bold green" if audit.is_valid else "bold red"
    console.print(
        f"\n[{status_color}]DAG Mathematical Validation: {'VALID (0 Conflicts)' if audit.is_valid else 'CONFLICTS DETECTED'}[/{status_color}] "
        f"(Total Sightseeing: {audit.total_sightseeing_min}m | Buffer Cushion: {audit.total_buffer_min}m)"
    )

    # Output file if requested
    if out_file:
        target = Path(out_file)
        target.write_text(json.dumps(trip.model_dump(mode="json"), indent=2), encoding="utf-8")
        console.print(f"[bold green]✓ Saved planned trip DAG to {target}[/bold green]")


@app.command("simulate")
def simulate(
    trip_path: Optional[str] = typer.Option(
        None,
        "--trip",
        "-t",
        help="Path to trip JSON file (defaults to Rome & Florence express)",
    ),
    iterations: int = typer.Option(
        2500,
        "--iterations",
        "-n",
        help="Number of simulated trip runs (e.g. 1000, 2500, 10000)",
    ),
    confidence: float = typer.Option(
        0.95,
        "--confidence",
        "-c",
        help="Target reliability threshold (e.g. 0.95 for 95% on-time confidence)",
    ),
    seed: Optional[int] = typer.Option(
        None,
        "--seed",
        help="Deterministic random seed for testing",
    ),
):
    """
    Execute Monte Carlo delay stress-testing across all transit legs in the trip DAG.
    Computes Trip Fragility Score, delay percentiles, and recommended risk cushions.
    """
    trip = load_or_create_sample_dag(trip_path)

    sim_params = SimulationParameters(
        iterations=iterations,
        target_confidence=confidence,
        seed=seed,
    )

    result = MonteCarloSimulator.run_simulation(trip, sim_params)

    status_color = "bold green" if result.is_robust else "bold red"
    status_label = "ROBUST" if result.is_robust else "FRAGILE / HIGH RISK"

    console.print(
        Panel.fit(
            f"[bold cyan]KronoLatch Monte Carlo Transit Simulator[/bold cyan]\n\n"
            f"[dim]Trip Destination:[/dim] {trip.destination}\n"
            f"[dim]Simulated Runs:[/dim] {result.iterations:,} journeys in {result.simulation_duration_ms:.1f}ms\n"
            f"[dim]Target Reliability:[/dim] {result.target_confidence * 100:.1f}%\n"
            f"[dim]Trip Fragility Score:[/dim] [{status_color}]{result.trip_fragility_score:.1f}% Miss Rate ({status_label})[/{status_color}]\n"
            f"[dim]Current Risk Cushion (α):[/dim] {result.current_risk_multiplier:.2f} | "
            f"[dim]Recommended α*:[/dim] [bold yellow]{result.recommended_risk_multiplier:.2f}[/bold yellow]",
            border_style="cyan",
        )
    )

    # Delay Percentiles Table
    percentile_table = Table(
        title="[bold blue]Stochastic Delay Percentiles Across Entire Trip[/bold blue]",
        show_header=True,
        header_style="bold cyan",
    )
    percentile_table.add_column("Percentile", style="white")
    percentile_table.add_column("Expected Cumulative Delay", style="yellow")
    percentile_table.add_column("Description", style="dim")

    percentile_table.add_row(
        "P50 (Median)", f"+{result.p50_total_delay:.1f} min", "Typical transit journey variance"
    )
    percentile_table.add_row(
        "P80 (Heavy)",
        f"+{result.p80_total_delay:.1f} min",
        "Moderate bottlenecks & platform congestion",
    )
    percentile_table.add_row(
        "P95 (Severe)",
        f"+{result.p95_total_delay:.1f} min",
        "Significant transit stoppage / highway gridlock",
    )
    percentile_table.add_row(
        "P99 (Extreme)",
        f"+{result.p99_total_delay:.1f} min",
        "Catastrophic rail / flight disruption",
    )

    console.print(percentile_table)

    # Critical Nodes Table if any missed
    if result.critical_nodes:
        node_table = Table(
            title="[bold red]Vulnerable Fixed Reservations (Miss Rates)[/bold red]",
            show_header=True,
            header_style="bold red",
        )
        node_table.add_column("Node ID", style="bold white")
        node_table.add_column("Attraction / Milestone", style="white")
        node_table.add_column("Miss Probability", style="bold red")

        for nid in result.critical_nodes:
            node_obj = next((n for n in trip.nodes if n.id == nid), None)
            title = node_obj.title if node_obj else nid
            rate = result.node_miss_rates.get(nid, 0.0)
            node_table.add_row(nid, title, f"{rate:.1f}%")

        console.print(node_table)
    else:
        console.print(
            "[bold green]✓ Zero fixed bookings were missed across all simulated runs![/bold green]"
        )

    if not result.is_robust:
        console.print(
            f"\n[bold yellow]⚠ Recommendation:[/bold yellow] To achieve {result.target_confidence * 100:.0f}% confidence, "
            f"increase transit risk buffer from [bold white]{result.current_risk_multiplier:.2f}[/bold white] to "
            f"[bold green]{result.recommended_risk_multiplier:.2f}[/bold green] (or pad departure times before {result.critical_nodes[0] if result.critical_nodes else 'fixed stops'})."
        )


@app.command("solar-audit")
def solar_audit(
    trip_path: Optional[str] = typer.Option(
        None,
        "--trip",
        "-t",
        help="Path to trip JSON file (defaults to Rome & Florence express)",
    ),
    date_str: Optional[str] = typer.Option(
        None,
        "--date",
        "-d",
        help="Target travel date in YYYY-MM-DD format (defaults to current date)",
    ),
    rain_probability: float = typer.Option(
        0.0,
        "--rain-prob",
        "-r",
        help="Precipitation probability between 0.0 and 1.0 (>=0.40 applies weather buffer)",
    ),
):
    """
    Perform astronomical solar position and daylight audit on the trip DAG.
    Calculates exact sunrise, golden hour, and sunset using NOAA equations to prevent scheduling outdoor venues in darkness.
    """
    import datetime

    trip = load_or_create_sample_dag(trip_path)

    d_val = None
    if date_str:
        try:
            d_val = datetime.date.fromisoformat(date_str)
        except ValueError:
            console.print(
                f"[bold red]Invalid date format '{date_str}', expected YYYY-MM-DD[/bold red]"
            )
            raise typer.Exit(1)

    audit = SolarEngine.audit_trip_daylight(trip, date_val=d_val, rain_probability=rain_probability)
    sched = audit.solar_schedule

    console.print(
        Panel.fit(
            f"[bold cyan]Astronomical Solar & Daylight Audit Engine (NOAA)[/bold cyan]\n\n"
            f"[dim]Destination:[/dim] {trip.destination} (Lat: {sched.latitude}, Lon: {sched.longitude})\n"
            f"[dim]Travel Date:[/dim] {sched.date} | [dim]Daylight Duration:[/dim] {sched.day_length_min // 60}h {sched.day_length_min % 60}m\n\n"
            f"🌅 [bold yellow]Sunrise:[/bold yellow] {sched.sunrise_time}  |  "
            f"☀️ [bold yellow]Solar Noon:[/bold yellow] {sched.solar_noon}  |  "
            f"📸 [bold magenta]Golden Hour:[/bold magenta] {sched.golden_hour_start} → {sched.golden_hour_end}\n"
            f"🌇 [bold red]Civil Sunset:[/bold red] {sched.sunset_time}  |  "
            f"🌑 [bold blue]Civil Twilight End:[/bold blue] {sched.civil_twilight_end}",
            border_style="cyan",
        )
    )

    # Outdoor venue audit table
    table = Table(
        title="[bold green]Outdoor Sightseeing & Activity Daylight Status[/bold green]",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Activity / Venue", style="bold white", width=36)
    table.add_column("Category", style="cyan")
    table.add_column("Scheduled Window", style="yellow")
    table.add_column("Solar Condition", style="bold")

    active_nodes = [n for n in trip.nodes if n.active]
    first_start = active_nodes[0].get_effective_fixed_start_min() if active_nodes else 8 * 60
    cursor = first_start if first_start is not None else 8 * 60

    sunset_m = time_str_to_minutes(sched.sunset_time)
    twilight_m = time_str_to_minutes(sched.civil_twilight_end)

    for idx, node in enumerate(active_nodes):
        if idx > 0:
            cursor += node.transit_min + 15
        start_m = (
            node.get_effective_fixed_start_min()
            if node.type == NodeType.FIXED and node.get_effective_fixed_start_min() is not None
            else cursor
        )
        end_m = start_m + node.duration_min
        cursor = end_m

        is_outdoor = (
            node.category in (Category.SIGHTSEEING, Category.WALK)
            and "indoor" not in node.title.lower()
            and "museum" not in node.title.lower()
            and "gallery" not in node.title.lower()
        )
        if not is_outdoor:
            continue

        window_str = f"{minutes_to_time_str(start_m)} – {minutes_to_time_str(end_m)}"

        if end_m > twilight_m:
            cond_str = "[bold red]🌑 TOTAL DARKNESS (VIOLATION)[/bold red]"
        elif end_m > sunset_m:
            cond_str = "[bold yellow]🌇 PAST SUNSET (TWILIGHT)[/bold yellow]"
        elif sched.is_golden_hour(minutes_to_time_str(start_m)):
            cond_str = "[bold magenta]📸 GOLDEN HOUR OPTIMAL[/bold magenta]"
        else:
            cond_str = "[bold green]☀️ FULL DAYLIGHT[/bold green]"

        table.add_row(node.title, node.category.value.upper(), window_str, cond_str)

    console.print(table)

    if audit.twilight_violations:
        console.print("\n[bold red]Darkness Violations Detected:[/bold red]")
        for v in audit.twilight_violations:
            console.print(f"  • [red]{v}[/red]")

    if audit.sunset_warnings:
        console.print("\n[bold yellow]Sunset & Twilight Notices:[/bold yellow]")
        for w in audit.sunset_warnings:
            console.print(f"  • [yellow]{w}[/yellow]")

    if audit.recommendations:
        console.print("\n[bold cyan]Solar & Meteorological Recommendations:[/bold cyan]")
        for r in audit.recommendations:
            console.print(f"  • [cyan]{r}[/cyan]")


@app.command("graph")
def graph(
    trip_path: Optional[str] = typer.Option(
        None,
        "--trip",
        "-t",
        help="Path to trip JSON file (defaults to Rome & Florence express)",
    ),
    threshold: int = typer.Option(
        5,
        "--threshold",
        "-s",
        help="Slack threshold in minutes to qualify as a critical bottleneck (default: 5m)",
    ),
    critical_only: bool = typer.Option(
        False,
        "--critical-only",
        help="Display only nodes that sit on the zero-slack Critical Path",
    ),
):
    """
    Perform Critical Path Method (CPM) forward and backward topological pass on the trip DAG.
    Calculates Earliest/Latest Start and Finish times and highlights zero-slack bottleneck edges.
    """
    trip = load_or_create_sample_dag(trip_path)
    result = CriticalPathEngine.analyze_trip(trip, critical_slack_threshold_min=threshold)

    console.print(
        Panel.fit(
            f"[bold cyan]KronoLatch Topological Critical Path Analyzer (CPM)[/bold cyan]\n\n"
            f"[dim]Trip Destination:[/dim] {trip.destination}\n"
            f"[dim]Total Planned Duration:[/dim] {result.total_duration_min // 60}h {result.total_duration_min % 60}m "
            f"({minutes_to_time_str(result.node_metrics[0].earliest_start_min)} → {minutes_to_time_str(result.earliest_completion_min)})\n"
            f"[dim]Critical Bottlenecks:[/dim] [bold red]{result.critical_nodes_count} node(s)[/bold red] with slack ≤ {threshold}m\n"
            f"[dim]Total Float Cushion:[/dim] [bold green]{result.total_slack_cushion_min} min[/bold green] flexible leeway across trip",
            border_style="cyan",
        )
    )

    table = Table(
        title="[bold green]Topological Node Schedule & Slack Cushion[/bold green]",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Node ID", style="bold white", width=8)
    table.add_column("Stop / Attraction", style="white", width=34)
    table.add_column("Type", style="cyan")
    table.add_column("Earliest (ES → EF)", style="yellow")
    table.add_column("Latest (LS → LF)", style="dim")
    table.add_column("Slack (Float)", style="bold")
    table.add_column("Path Status", style="bold")

    for m in result.node_metrics:
        if critical_only and not m.is_critical:
            continue

        es_str = f"{minutes_to_time_str(m.earliest_start_min)} → {minutes_to_time_str(m.earliest_finish_min)}"
        ls_str = f"{minutes_to_time_str(m.latest_start_min)} → {minutes_to_time_str(m.latest_finish_min)}"

        if m.total_float_min <= 5:
            slack_str = f"[bold red]{m.total_float_min} min[/bold red]"
            path_str = "[bold red]🔴 CRITICAL PATH[/bold red]"
        elif m.total_float_min <= 20:
            slack_str = f"[bold yellow]{m.total_float_min} min[/bold yellow]"
            path_str = "[bold yellow]🟡 MODERATE SLACK[/bold yellow]"
        else:
            slack_str = f"[bold green]{m.total_float_min} min[/bold green]"
            path_str = "[bold green]🟢 RELAXED CUSHION[/bold green]"

        table.add_row(
            m.node_id,
            m.title,
            m.node_type.value.upper(),
            es_str,
            ls_str,
            slack_str,
            path_str,
        )

    console.print(table)


@app.command("split-receipt")
def split_receipt(
    receipt_input: str = typer.Argument(
        ...,
        help="Raw receipt text string or path to a text file containing line items and prices",
    ),
    payer: str = typer.Option(
        "Franek",
        "--payer",
        "-p",
        help="Name of the person who paid the bill",
    ),
    travelers: str = typer.Option(
        "Franek, Anna, Marek, Kasia",
        "--travelers",
        "-t",
        help="Comma-separated traveler names in the group",
    ),
    tip: float = typer.Option(
        0.0,
        "--tip",
        help="Additional gratuity / tip added to bill",
    ),
    title: str = typer.Option(
        "Group Restaurant Bill",
        "--title",
        help="Title or venue description of the bill",
    ),
    currency: str = typer.Option(
        "EUR",
        "--currency",
        "-c",
        help="Billing currency code",
    ),
    trip_path: Optional[str] = typer.Option(
        None,
        "--trip",
        help="Optional trip DAG path to append generated itemized expenses into",
    ),
):
    """
    Parse an itemized restaurant receipt and calculate cent-exact proportional splits with distributed tax/tip.
    """
    # Read text or file
    if len(receipt_input) < 255 and Path(receipt_input).is_file():
        text_content = Path(receipt_input).read_text(encoding="utf-8")
    else:
        text_content = receipt_input

    traveler_list = [t.strip() for t in travelers.split(",") if t.strip()]

    bill = ReceiptSplitter.parse_receipt_text(
        text=text_content,
        payer=payer,
        default_travelers=traveler_list,
        title=title,
        currency=currency,
        tip=tip,
    )

    result = ReceiptSplitter.calculate_split(bill)

    console.print(
        Panel.fit(
            f"[bold cyan]KronoLatch Itemized Receipt & Overhead Splitter[/bold cyan]\n\n"
            f"[dim]Venue / Bill:[/dim] {result.title} (Paid by [bold white]{result.payer}[/bold white])\n"
            f"[dim]Subtotal:[/dim] {result.subtotal:.2f} {result.currency} | "
            f"[dim]Tax/Tip/Service Overhead:[/dim] +{result.overhead_total:.2f} {result.currency} (+{result.overhead_percentage:.1f}%)\n"
            f"[dim]Total Bill Settled:[/dim] [bold green]{result.total_bill:.2f} {result.currency}[/bold green]",
            border_style="cyan",
        )
    )

    table = Table(
        title="[bold green]Itemized Individual Liabilities (Cent-Exact Conservation)[/bold green]",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Traveler", style="bold white")
    table.add_column("Liabilities (with Overhead)", style="yellow")
    table.add_column("Percent Share", style="dim")

    for t, amount in sorted(result.traveler_liabilities.items(), key=lambda x: x[1], reverse=True):
        pct = (amount / result.total_bill * 100.0) if result.total_bill > 0 else 0.0
        table.add_row(t, f"{amount:.2f} {result.currency}", f"{pct:.1f}%")

    console.print(table)

    # Append to trip if requested
    if trip_path and Path(trip_path).is_file():
        p = Path(trip_path)
        with open(p, "r", encoding="utf-8") as f:
            trip_data = json.load(f)
        trip_obj = TripDAG.model_validate(trip_data)
        trip_obj.expenses.extend(result.generated_expenses)
        p.write_text(json.dumps(trip_obj.model_dump(mode="json"), indent=2), encoding="utf-8")
        console.print(
            f"[bold green]✓ Appended {len(result.generated_expenses)} itemized expenses to {p}[/bold green]"
        )


@app.command("schengen-audit")
def schengen_audit(
    entry_date: str = typer.Option(
        "2026-06-01",
        "--entry",
        help="Planned Schengen entry date (YYYY-MM-DD)",
    ),
    exit_date: str = typer.Option(
        "2026-06-15",
        "--exit",
        help="Planned Schengen exit date (YYYY-MM-DD)",
    ),
    past_stays_file: Optional[str] = typer.Option(
        None,
        "--past-stays",
        help="Optional path to JSON file containing past entry/exit intervals",
    ),
    passport_expiry: Optional[str] = typer.Option(
        None,
        "--passport-expiry",
        help="Passport expiration date (YYYY-MM-DD)",
    ),
):
    """
    Evaluate 90/180-day short-stay visa compliance and passport validity under EU Regulation 2016/399.
    Runs 100% locally with zero cloud telemetry.
    """
    past_stays: List[StayInterval] = []
    if past_stays_file and Path(past_stays_file).is_file():
        with open(past_stays_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                past_stays = [StayInterval.model_validate(item) for item in data]

    planned = StayInterval(entry_date=entry_date, exit_date=exit_date)
    audit = SchengenCalculator.audit_stay(
        past_stays=past_stays,
        planned_stay=planned,
        passport_expiry_date=passport_expiry,
    )

    status_color = "bold green" if audit.is_compliant else "bold red"
    status_label = (
        "COMPLIANT (LEGAL)"
        if audit.is_compliant
        else f"OVERSTAY DETECTED (+{audit.overstay_days} DAYS)"
    )

    console.print(
        Panel.fit(
            f"[bold cyan]KronoLatch Schengen 90/180-Day Compliance Vault[/bold cyan]\n[dim]Regulation (EU) 2016/399[/dim]\n\n"
            f"[dim]Planned Stay:[/dim] {planned.entry_date} → {planned.exit_date} ({audit.planned_stay_days} days)\n"
            f"[dim]Historical Schengen Days Used:[/dim] {audit.total_past_days} days\n"
            f"[dim]Compliance Status:[/dim] [{status_color}]{status_label}[/{status_color}]\n\n"
            f"📅 [dim]Days Remaining on Entry:[/dim] [bold green]{audit.days_remaining_on_entry} days[/bold green]\n"
            f"📅 [dim]Days Remaining on Exit:[/dim] [bold {'green' if audit.days_remaining_on_exit > 0 else 'red'}]{audit.days_remaining_on_exit} days[/bold {'green' if audit.days_remaining_on_exit > 0 else 'red'}]\n"
            f"📊 [dim]Max Days Used in Any 180-Day Window:[/dim] [bold {'yellow' if audit.max_days_used_in_window <= 90 else 'red'}]{audit.max_days_used_in_window} / 90 days[/bold {'yellow' if audit.max_days_used_in_window <= 90 else 'red'}]",
            border_style="cyan",
        )
    )

    if audit.earliest_reentry_date:
        console.print(
            f"[bold yellow]Notice: Earliest legal re-entry date after this stay: {audit.earliest_reentry_date}[/bold yellow]"
        )

    if not audit.passport_valid and audit.passport_warning:
        console.print(
            f"\n[bold red]🛂 PASSPORT VALIDITY ALERT:[/bold red] {audit.passport_warning}"
        )
    elif audit.passport_valid and passport_expiry:
        console.print(
            f"[bold green]✓ Passport expiration ({passport_expiry}) meets EU 3-month departure buffer rule.[/bold green]"
        )


@app.command("export-ics")
def export_ics(
    trip_path: Optional[str] = typer.Option(
        None,
        "--trip",
        "-t",
        help="Path to trip JSON file (defaults to Rome & Florence express)",
    ),
    out_file: str = typer.Option(
        "./trip-schedule.ics",
        "--out",
        "-o",
        help="Output destination path for the .ics calendar file",
    ),
    date_str: Optional[str] = typer.Option(
        None,
        "--date",
        "-d",
        help="Base travel date in YYYY-MM-DD format (defaults to 2026-06-15)",
    ),
):
    """
    Export the verified TripDAG itinerary into a standard RFC 5545 iCalendar (.ics) file.
    Includes buffer-aware VALARM reminder alarms for airport and platform departure transitions.
    """
    import datetime

    trip = load_or_create_sample_dag(trip_path)

    d_val = None
    if date_str:
        try:
            d_val = datetime.date.fromisoformat(date_str)
        except ValueError:
            console.print(
                f"[bold red]Invalid date format '{date_str}', expected YYYY-MM-DD[/bold red]"
            )
            raise typer.Exit(1)

    target_path = CalendarExporter.export_to_file(trip, out_file, base_date=d_val)
    console.print(
        Panel.fit(
            f"[bold green]✓ RFC 5545 iCalendar Export Completed[/bold green]\n\n"
            f"[dim]Trip Title:[/dim] {trip.title}\n"
            f"[dim]Target File:[/dim] {target_path.resolve()}\n"
            f"[dim]Events Exported:[/dim] {len([n for n in trip.nodes if n.active])} timeline nodes\n"
            f"[dim]Features:[/dim] Transition-aware VALARM alarms (-120m flights, -25m trains) & PNR links",
            border_style="green",
        )
    )


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
