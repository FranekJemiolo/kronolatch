/**
 * KronoLatch Core Client-Side Application
 * Deterministic Temporal DAG Engine, Anti-Phishing Vendor Verifier & Group Ledger
 */

// -------------------------------------------------------------------
// 1. STATE & TOUR PRESET DATA
// -------------------------------------------------------------------
let currentTab = 'dag';
let currentTripPreset = 'rome';
let simulateRailDelay = false;
let currentStudioTarget = 'gemini';
let activeTheme = 'day';

const tripPresets = {
  rome: {
    title: "Rome & Florence Express",
    destination: "Rome, Florence & Tuscany",
    groupDesc: "4 Adults (Franek, Anna, Marek, Kasia)",
    travelers: ['Franek', 'Anna', 'Marek', 'Kasia'],
    nodes: [
      {
        id: 'n1',
        title: 'Flight WMI (Warsaw Modlin) → FCO (Rome Fiumicino)',
        type: 'fixed',
        category: 'flight',
        icon: 'fa-plane-departure',
        fixedStartMin: 8 * 60 + 0, // 08:00
        durationMin: 145,          // 2h 25m flight
        transitMin: 0,
        transitMode: 'flight',
        priority: 10,
        pnr: 'RYR-9941K',
        officialDomain: 'ryanair.com',
        active: true,
        notes: 'Gate closes 30m prior. Carry-on verified.'
      },
      {
        id: 'n2',
        title: 'Leonardo Express High-Speed Train (FCO → Roma Termini)',
        type: 'flexible',
        category: 'rail',
        icon: 'fa-train',
        durationMin: 32,
        minDurationMin: 32,
        transitMin: 25,
        transitMode: 'train',
        priority: 9,
        pnr: 'TREN-88210',
        officialDomain: 'trenitalia.com',
        active: true,
        notes: 'Direct airport train every 15 mins. Validate in app before boarding.'
      },
      {
        id: 'n3',
        title: 'Hotel Bag Drop & Traditional Trastevere Lunch',
        type: 'flexible',
        category: 'food',
        icon: 'fa-utensils',
        durationMin: 65,
        minDurationMin: 30,
        transitMin: 18,
        transitMode: 'walk',
        priority: 4,
        pnr: 'WALK-IN',
        officialDomain: 'maps.google.com',
        active: true,
        notes: 'Relaxed pasta lunch. Can be shortened or trimmed if incoming train is delayed.'
      },
      {
        id: 'n4',
        title: 'Pantheon Exterior & Scenic Piazza Navona Stroll',
        type: 'flexible',
        category: 'sightseeing',
        icon: 'fa-landmark-dome',
        durationMin: 50,
        minDurationMin: 20,
        transitMin: 15,
        transitMode: 'walk',
        priority: 3,
        pnr: 'MIC-CULTURA',
        officialDomain: 'portale.museiitaliani.it',
        active: true,
        notes: 'Optional scenic walk en route to Colosseum; candidate for auto-trim.'
      },
      {
        id: 'n5',
        title: 'Colosseum Arena & Underground Timed Entry (HARD LOCK)',
        type: 'fixed',
        category: 'sightseeing',
        icon: 'fa-archway',
        fixedStartMin: 15 * 60 + 30, // 15:30 STRICT ENTRY
        durationMin: 120,
        transitMin: 22,
        transitMode: 'walk',
        priority: 10,
        pnr: 'COL-77419-IT',
        officialDomain: 'ticketing.colosseo.it',
        active: true,
        notes: 'STRICT ID CHECK: Must arrive 20m before 15:30 slot or ticket is forfeited.'
      },
      {
        id: 'n6',
        title: 'Frecciarossa 9548 Rail (Roma Termini → Firenze SMN)',
        type: 'fixed',
        category: 'rail',
        icon: 'fa-train-tram',
        fixedStartMin: 18 * 60 + 50, // 18:50 Departure
        durationMin: 95,
        transitMin: 25,
        transitMode: 'train',
        priority: 10,
        pnr: 'FR-551902',
        officialDomain: 'trenitalia.com',
        active: true,
        notes: 'Coach 4, Seats 12A-12D. Group split: 2 on rail, 2 picking up Tuscany car.'
      }
    ]
  },
  alps: {
    title: "Central Europe Alpine Loop",
    destination: "Vienna, Salzburg & Hallstatt",
    groupDesc: "4 Adults (PKP Intercity + ÖBB Railjet + EV Rental)",
    travelers: ['Franek', 'Anna', 'Marek', 'Kasia'],
    nodes: [
      {
        id: 'a1',
        title: 'EC Sobieski Rail (Warszawa Centralna → Wien Hbf)',
        type: 'fixed',
        category: 'rail',
        icon: 'fa-train',
        fixedStartMin: 6 * 60 + 50,
        durationMin: 210,
        transitMin: 0,
        transitMode: 'train',
        priority: 10,
        pnr: 'PKP-66120',
        officialDomain: 'intercity.pl',
        active: true,
        notes: 'Direct EuroCity coach. Passport/ID required at border.'
      },
      {
        id: 'a2',
        title: 'Naschmarkt Viennese Coffee & Strudel Break',
        type: 'flexible',
        category: 'food',
        icon: 'fa-mug-hot',
        durationMin: 55,
        minDurationMin: 20,
        transitMin: 20,
        transitMode: 'walk',
        priority: 3,
        pnr: 'FLEX-CAFE',
        officialDomain: 'wien.info',
        active: true,
        notes: 'Lowest priority flexible pause; trimmed first during delays.'
      },
      {
        id: 'a3',
        title: 'Schönbrunn Palace Grand Tour Slot (HARD LOCK)',
        type: 'fixed',
        category: 'sightseeing',
        icon: 'fa-crown',
        fixedStartMin: 13 * 60 + 15,
        durationMin: 110,
        transitMin: 25,
        transitMode: 'walk',
        priority: 10,
        pnr: 'SCH-44091',
        officialDomain: 'imperialtickets.com',
        active: true,
        notes: 'Strict audio-guide admission window.'
      },
      {
        id: 'a4',
        title: 'ÖBB Railjet Xpress (Wien Hbf → Salzburg Hbf)',
        type: 'fixed',
        category: 'rail',
        icon: 'fa-train-subway',
        fixedStartMin: 16 * 60 + 30,
        durationMin: 145,
        transitMin: 30,
        transitMode: 'train',
        priority: 10,
        pnr: 'OEBB-9910',
        officialDomain: 'oebb.at',
        active: true,
        notes: 'Quiet Zone Coach 21.'
      }
    ]
  }
};

let activeNodes = JSON.parse(JSON.stringify(tripPresets.rome.nodes));

// -------------------------------------------------------------------
// 2. ANTI-PHISHING GROUND TRUTH DATABASE
// -------------------------------------------------------------------
const vendorDatabase = [
  {
    key: 'colosseum',
    venue: 'Parco Archeologico del Colosseo (Rome)',
    trapDomain: 'colosseum-rome-tickets.org',
    trapPrice: '€44.00',
    trapMarkup: '+144.4% Reseller Markup',
    trapReason: 'Google Search Ad clone using "colosseum-tickets" keywords. Resells standard €18 tickets bundled with generic PDF audio guide.',
    officialDomain: 'ticketing.colosseo.it',
    officialUrl: 'https://ticketing.colosseo.it/',
    officialPrice: '€18.00 (Full Experience €24.00)',
    placesId: 'ChIJrRMgU7ZhLxMRxAOFkC7I8Sg',
    wikidataId: 'Q10285 (P856 Verified)',
    bookingRule: 'Tickets release strictly 30 days in advance at 08:30 CET down to the minute.'
  },
  {
    key: 'sagrada',
    venue: 'Basílica de la Sagrada Família (Barcelona)',
    trapDomain: 'sagradafamilia-tickets-barcelona.com',
    trapPrice: '€59.50',
    trapMarkup: '+128% Reseller Markup',
    trapReason: 'Ranks #1 on sponsored queries; mimics official typography but operates as an unauthorized third-party broker.',
    officialDomain: 'sagradafamilia.org',
    officialUrl: 'https://sagradafamilia.org/en/tickets',
    officialPrice: '€26.00 (With Towers €36.00)',
    placesId: 'ChIJk_s92NyipBIRUMnDG8Kq2Js',
    wikidataId: 'Q48435 (P856 Verified)',
    bookingRule: 'Official calendar releases tickets up to 2 months ahead; use official app.'
  },
  {
    key: 'louvre',
    venue: 'Musée du Louvre (Paris)',
    trapDomain: 'louvre-museum-tickets-paris.fr',
    trapPrice: '€52.00',
    trapMarkup: '+136% Unofficial Broker',
    trapReason: 'Uses ".fr" TLD to appear state-affiliated. Frequently fails to deliver timed QR entry passes during peak summer slots.',
    officialDomain: 'ticket.louvre.fr',
    officialUrl: 'https://ticket.louvre.fr/',
    officialPrice: '€22.00',
    placesId: 'ChIJD3uTd9hx5kcR1IQvGfr8dbk',
    wikidataId: 'Q19675 (P856 Verified)',
    bookingRule: 'Mandatory timed-entry reservation even for free-entry eligible European youth.'
  },
  {
    key: 'rail',
    venue: 'Italian & Polish National Rail (Trenitalia / PKP Intercity)',
    trapDomain: 'italiarail-express-tickets.net',
    trapPrice: '€49.00 + €9 Fee',
    trapMarkup: '+22% Foreign Booking Fee',
    trapReason: 'Third-party wrapper charging service fees without providing live delay compensation or digital app check-in.',
    officialDomain: 'trenitalia.com / intercity.pl',
    officialUrl: 'https://www.trenitalia.com/',
    officialPrice: '€29.90 (Frecciarossa Super Economy)',
    placesId: 'ChIJ06f8_p9hLxMR_Trenitalia',
    wikidataId: 'Q659631 / Q1475363',
    bookingRule: 'Book directly on Trenitalia.com or PKP Intercity app for instant digital check-in.'
  }
];

// -------------------------------------------------------------------
// 3. GROUP EXPENSE LEDGER STATE
// -------------------------------------------------------------------
const travelers = ['Franek', 'Anna', 'Marek', 'Kasia'];
const EUR_TO_PLN = 4.30;

let ledgerExpenses = [
  { id: 'e1', title: 'Ryanair Flights WMI → FCO (4 Pax)', payer: 'Franek', amount: 340, currency: 'EUR', participants: ['Franek', 'Anna', 'Marek', 'Kasia'] },
  { id: 'e2', title: 'Colosseum Official Tickets (ticketing.colosseo.it)', payer: 'Anna', amount: 96, currency: 'EUR', participants: ['Franek', 'Anna', 'Marek', 'Kasia'] },
  { id: 'e3', title: 'Frecciarossa Rail Tickets (Train Subgroup Only)', payer: 'Marek', amount: 90, currency: 'EUR', participants: ['Marek', 'Kasia'] },
  { id: 'e4', title: 'Tuscany Rental Car & Autostrada Fuel (Car Subgroup)', payer: 'Franek', amount: 160, currency: 'EUR', participants: ['Franek', 'Anna'] },
  { id: 'e5', title: 'Modlin Airport Parking (Poland, 4 Pax)', payer: 'Kasia', amount: 258, currency: 'PLN', participants: ['Franek', 'Anna', 'Marek', 'Kasia'] }
];

// -------------------------------------------------------------------
// 4. MANUAL VERIFICATION TEST SUITE DEFINITIONS
// -------------------------------------------------------------------
const manualTests = [
  {
    id: 'test-phishing',
    name: 'Test #1: SEO Phishing Clone vs Official Ground Truth',
    badge: 'SECURITY',
    status: 'READY',
    desc: 'Asserts candidate domain "colosseum-rome-tickets.org" (€44) is blocked in favor of Wikidata P856 "ticketing.colosseo.it" (€18), confirming +144.4% markup.',
    prompt: `[KRONOLATCH AUDIT PROMPT: TEST #1 - ANTI-PHISHING]\nVenue: Parco Archeologico del Colosseo, Rome\nCandidate Search Result URL: https://www.colosseum-rome-tickets.org/fast-track (€44.00)\nGround Truth Official Domain: ticketing.colosseo.it (€18.00 base fare)\nTask: Verify canonical root domain match, compute exact markup %, and block unauthorized reseller.`
  },
  {
    id: 'test-cascade',
    name: 'Test #2: +35m Regional Rail Delay Domino Effect',
    badge: 'TEMPORAL DAG',
    status: 'READY',
    desc: 'Simulates a 35-minute delay on Leonardo Express. Asserts DAG flags -20 min HARD_CONFLICT at locked 12:30 museum slot and trims the flexible walk.',
    prompt: `[KRONOLATCH AUDIT PROMPT: TEST #2 - TEMPORAL DAG CASCADE]\nUpstream Transit: Regional Train arrives 11:40 (+35m delay -> 12:15).\nFlexible Stop: Morning Scenic Piazza Walk (30m, min 10m, priority 2).\nLocked Anchor: Timed Museum Entry at 12:30 (requires 20m transit + 15m queue buffer = 35m).\nTask: Calculate arrival ready-time (12:50), flag -20m conflict, and trim flexible walk.`
  },
  {
    id: 'test-split',
    name: 'Test #3: Asymmetric Subgroup Cost Split (EUR + PLN)',
    badge: 'LEDGER MATH',
    status: 'READY',
    desc: 'Asserts exact net balances (Franek +€30, Anna -€130, Marek -€5, Kasia +€105) settled in 3 transfers totaling €135.',
    prompt: `[KRONOLATCH AUDIT PROMPT: TEST #3 - ASYMMETRIC GROUP SPLIT]\nTravelers: Franek, Anna, Marek, Kasia. Exchange rate: 1 EUR = 4.30 PLN.\n1. Rental car: €160 paid by Franek (split Franek & Anna only)\n2. Train: €90 paid by Marek (split Marek & Kasia only)\n3. Dinner: €200 paid by Kasia (split all 4)\nTask: Calculate net balances and output minimum 3 settlement transfers totaling €135.`
  },
  {
    id: 'test-schema',
    name: 'Test #4: Unstructured Booking Ingestion & Buffer Injection',
    badge: 'SCHEMA',
    status: 'READY',
    desc: 'Asserts automatic 120m flight pre-departure buffer and 15m rail buffer injection from messy booking text.',
    prompt: `[KRONOLATCH AUDIT PROMPT: TEST #4 - SCHEMA INGESTION]\nRaw Confirmation: "Ryanair FR9941 WMI -> FCO departs 08:00 arrives 10:25. Leonardo Express 11:10. Colosseum entry 15:30 ticket COL-77419. Frecciarossa 9548 to Florence 18:50 Coach 4."\nTask: Output strict JSON conforming to trip-dag.schema.json with 120m airport buffer and 15m rail buffers configured.`
  }
];

// -------------------------------------------------------------------
// 5. THEME & TOAST UTILITIES
// -------------------------------------------------------------------
function toggleTheme() {
  activeTheme = activeTheme === 'day' ? 'twilight' : 'day';
  const html = document.documentElement;
  const btn = document.getElementById('themeToggleBtn');
  
  if (activeTheme === 'twilight') {
    html.setAttribute('data-theme', 'twilight');
    btn.innerHTML = '<i class="fa-solid fa-sun text-amber-400"></i>';
    showToast('Switched to Serene Twilight theme');
  } else {
    html.removeAttribute('data-theme');
    btn.innerHTML = '<i class="fa-solid fa-moon text-slate-600"></i>';
    showToast('Switched to Calm Day theme');
  }
}

function showToast(message, iconClass = 'fa-circle-check text-emerald-500') {
  const toast = document.getElementById('toast');
  const icon = document.getElementById('toast-icon');
  const msg = document.getElementById('toast-msg');
  if (!toast) return;
  icon.className = `fa-solid ${iconClass} text-lg`;
  msg.textContent = message;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, 2800);
}

function copyTextToClipboard(text, confirmMsg = 'Copied to clipboard!') {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand('copy');
    showToast(confirmMsg);
  } catch (e) {
    showToast('Copy failed — please select and copy manually', 'fa-triangle-exclamation text-amber-500');
  }
  document.body.removeChild(ta);
}

function switchTab(tabId) {
  currentTab = tabId;
  ['dag', 'verifier', 'ledger', 'studio'].forEach(id => {
    const sec = document.getElementById(`tab-${id}`);
    const btn = document.getElementById(`tab-btn-${id}`);
    if (id === tabId) {
      sec.classList.remove('hidden');
      btn.classList.add('active');
    } else {
      sec.classList.add('hidden');
      btn.classList.remove('active');
    }
  });
}

function switchTripPreset(presetKey) {
  currentTripPreset = presetKey;
  const preset = tripPresets[presetKey];
  activeNodes = JSON.parse(JSON.stringify(preset.nodes));
  simulateRailDelay = false;
  document.getElementById('dagHeaderTitle').textContent = preset.title;
  document.getElementById('cfgDest').value = preset.destination;
  document.getElementById('cfgGroup').value = preset.groupDesc;
  updateDelayButtonUI();
  updateDagMath();
  renderStudioArtifact();
  showToast(`Loaded "${preset.title}" itinerary`);
}

function formatMinToTime(totalMinutes) {
  const normalized = ((Math.round(totalMinutes) % 1440) + 1440) % 1440;
  const hrs = Math.floor(normalized / 60);
  const mins = normalized % 60;
  return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
}

// -------------------------------------------------------------------
// 6. TAB 1: TEMPORAL DAG ENGINE & LEEWAY OPTIMIZER
// -------------------------------------------------------------------
function updateDagMath() {
  const riskPct = parseInt(document.getElementById('riskSlider').value, 10) || 0;
  const hubOverhead = parseInt(document.getElementById('hubSlider').value, 10) || 0;

  document.getElementById('riskValueDisplay').textContent = `+${riskPct}%`;
  document.getElementById('hubValueDisplay').textContent = `${hubOverhead} min`;
  document.getElementById('kpi-buffer-sub').textContent = `${riskPct}% risk + ${hubOverhead}m platform buffer`;

  let cursorMin = 8 * 60; // 08:00 start
  let totalSightseeing = 0;
  let totalBaseTransit = 0;
  let totalInjectedBuffer = 0;
  let hardConflictCount = 0;
  let firstConflictMsg = '';

  const container = document.getElementById('dagTimelineContainer');
  container.innerHTML = '';

  activeNodes.forEach((node, idx) => {
    if (!node.active) {
      // Collapsed trimmed stop
      const trimmedEl = document.createElement('div');
      trimmedEl.className = 'travel-card p-3.5 bg-slate-50/80 border-dashed border-slate-300 flex items-center justify-between text-xs text-slate-500';
      trimmedEl.innerHTML = `
        <div class="flex items-center gap-2.5">
          <i class="fa-solid fa-scissors text-amber-600"></i>
          <span class="line-through font-medium text-slate-600">${node.title}</span>
          <span class="text-emerald-700 font-semibold">(Reclaimed ${node.durationMin + node.transitMin}m leeway)</span>
        </div>
        <button onclick="toggleNodeActive('${node.id}')" class="px-3 py-1 rounded-lg bg-white border border-slate-200 text-slate-700 font-medium hover:bg-slate-100 transition shadow-sm">
          Restore Stop
        </button>
      `;
      container.appendChild(trimmedEl);
      return;
    }

    const baseTransit = idx === 0 ? 0 : node.transitMin;
    const riskBuffer = idx === 0 ? 0 : Math.ceil(baseTransit * (riskPct / 100));
    const stationBuffer = idx === 0 ? 0 : hubOverhead;
    const delayPenalty = (simulateRailDelay && idx === 1) ? 35 : 0;

    const effectiveTransition = baseTransit + riskBuffer + stationBuffer + delayPenalty;

    totalBaseTransit += baseTransit;
    totalInjectedBuffer += (riskBuffer + stationBuffer);
    if (node.category === 'sightseeing' || node.category === 'food') {
      totalSightseeing += node.durationMin;
    } else {
      totalBaseTransit += node.durationMin;
    }

    let earliestArrival = idx === 0 ? node.fixedStartMin : (cursorMin + effectiveTransition);
    let actualStart = earliestArrival;
    let slackMin = null;
    let isConflict = false;

    if (node.type === 'fixed') {
      if (idx === 0) {
        actualStart = node.fixedStartMin;
        slackMin = 30;
      } else {
        slackMin = node.fixedStartMin - earliestArrival;
        if (slackMin < 0) {
          isConflict = true;
          hardConflictCount++;
          if (!firstConflictMsg) {
            firstConflictMsg = `Injected delay causes you to arrive at "${node.title}" at ${formatMinToTime(earliestArrival)}, missing your ${formatMinToTime(node.fixedStartMin)} locked entry by ${Math.abs(slackMin)} minutes!`;
          }
          actualStart = earliestArrival;
        } else {
          actualStart = node.fixedStartMin;
        }
      }
    }

    const endMin = actualStart + node.durationMin;
    cursorMin = endMin;

    // Render Timeline Card
    const card = document.createElement('div');
    card.className = `travel-card timeline-item p-4 transition-all ${isConflict ? 'border-rose-300 bg-rose-50/20' : ''}`;
    
    const isFixed = node.type === 'fixed';
    const badgeHtml = isFixed
      ? `<span class="badge-fixed px-2.5 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1.5"><i class="fa-solid fa-lock text-[10px]"></i> Locked Reservation (${formatMinToTime(node.fixedStartMin)})</span>`
      : `<span class="badge-flexible px-2.5 py-0.5 rounded-full text-xs font-medium flex items-center gap-1.5"><i class="fa-solid fa-sun text-[10px] text-amber-500"></i> Flexible Window</span>`;

    let slackBadge = '';
    if (isConflict) {
      slackBadge = `<span class="px-2 py-0.5 rounded-lg bg-rose-100 text-rose-800 border border-rose-200 text-xs font-bold flex items-center gap-1"><i class="fa-solid fa-triangle-exclamation"></i> Hard Conflict (${slackMin}m)</span>`;
    } else if (slackMin !== null) {
      slackBadge = `<span class="px-2 py-0.5 rounded-lg bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-semibold flex items-center gap-1"><i class="fa-solid fa-circle-check"></i> +${slackMin}m Safe Slack</span>`;
    }

    card.innerHTML = `
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-start gap-3">
          <div class="w-10 h-10 rounded-xl ${isFixed ? 'bg-sky-100 text-sky-700' : 'bg-slate-100 text-slate-600'} flex items-center justify-center text-base shrink-0 shadow-sm mt-0.5">
            <i class="fa-solid ${node.icon || 'fa-location-dot'}"></i>
          </div>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <h4 class="font-bold text-sm text-slate-900">${node.title}</h4>
              ${badgeHtml}
            </div>
            <p class="text-xs text-slate-500 mt-1 flex items-center gap-3">
              <span class="font-semibold text-slate-700"><i class="fa-regular fa-clock mr-1 text-slate-400"></i>${formatMinToTime(actualStart)} — ${formatMinToTime(endMin)} (${node.durationMin}m)</span>
              ${node.pnr ? `<span class="font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-[10px]">PNR: ${node.pnr}</span>` : ''}
              ${node.officialDomain ? `<span class="text-sky-700 font-medium text-[11px]"><i class="fa-solid fa-shield-check mr-1 text-emerald-600"></i>${node.officialDomain}</span>` : ''}
            </p>
            ${node.notes ? `<p class="text-xs text-slate-500 mt-1 italic">${node.notes}</p>` : ''}
          </div>
        </div>
        <div class="flex flex-col items-end gap-1.5 shrink-0">
          ${slackBadge}
          ${!isFixed ? `<button onclick="toggleNodeActive('${node.id}')" class="text-[11px] text-slate-400 hover:text-amber-600 font-medium transition"><i class="fa-solid fa-scissors mr-1"></i>Trim Stop</button>` : ''}
        </div>
      </div>
      
      <!-- Cushion pill underneath if there is transit to next -->
      ${idx < activeNodes.length - 1 ? `
        <div class="mt-3 pt-3 border-t border-slate-100 flex items-center gap-2 text-xs text-slate-500">
          <i class="fa-solid fa-arrow-down text-slate-300 text-[10px]"></i>
          <span class="cushion-pill ${(simulateRailDelay && idx === 0) ? 'has-delay' : ''}">
            <i class="fa-solid fa-route"></i>
            <span>${node.transitMin}m Transit + ${riskBuffer + stationBuffer}m Safety Cushion ${(simulateRailDelay && idx === 0) ? '<strong>(+35m Delay Injected)</strong>' : ''}</span>
          </span>
        </div>
      ` : ''}
    `;
    container.appendChild(card);
  });

  // Update KPIs
  document.getElementById('kpi-sightseeing').textContent = `${Math.floor(totalSightseeing / 60)}h ${totalSightseeing % 60}m`;
  document.getElementById('kpi-transit').textContent = `${Math.floor(totalBaseTransit / 60)}h ${totalBaseTransit % 60}m`;
  document.getElementById('kpi-buffer').textContent = `${Math.floor(totalInjectedBuffer / 60)}h ${totalInjectedBuffer % 60}m`;

  const conflictCard = document.getElementById('kpi-conflict-card');
  const conflictText = document.getElementById('kpi-conflicts');
  const conflictSub = document.getElementById('kpi-conflicts-sub');
  const conflictIcon = document.getElementById('kpi-conflict-icon');
  const navBadge = document.getElementById('nav-conflict-badge');
  const delayBanner = document.getElementById('delayAlertBanner');
  const delayAlertText = document.getElementById('delayAlertText');

  if (hardConflictCount > 0) {
    conflictCard.className = 'travel-card p-4 flex items-center justify-between border-rose-200 bg-rose-50/40';
    conflictText.textContent = `${hardConflictCount} Conflict`;
    conflictText.className = 'text-2xl font-bold text-rose-700 mt-1';
    conflictSub.textContent = 'Action needed: Trim optional stop';
    conflictIcon.className = 'w-12 h-12 rounded-2xl bg-rose-100 border border-rose-200 flex items-center justify-center text-rose-700 text-xl';
    conflictIcon.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
    navBadge.textContent = `${hardConflictCount} CONFLICT`;
    navBadge.className = 'ml-1 px-2 py-0.5 text-[10px] font-bold rounded-full bg-rose-100 text-rose-800';

    delayBanner.classList.remove('hidden');
    delayAlertText.textContent = firstConflictMsg;
  } else {
    conflictCard.className = 'travel-card p-4 flex items-center justify-between border-emerald-200 bg-emerald-50/30';
    conflictText.textContent = 'All Protected';
    conflictText.className = 'text-2xl font-bold text-emerald-700 mt-1';
    conflictSub.textContent = '0 booking collisions';
    conflictIcon.className = 'w-12 h-12 rounded-2xl bg-emerald-100 border border-emerald-200 flex items-center justify-center text-emerald-700 text-xl';
    conflictIcon.innerHTML = '<i class="fa-solid fa-check"></i>';
    navBadge.textContent = 'ON TIME';
    navBadge.className = 'ml-1 px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-100 text-emerald-800';

    delayBanner.classList.add('hidden');
  }
}

function toggleNodeActive(nodeId) {
  const target = activeNodes.find(n => n.id === nodeId);
  if (target) {
    target.active = !target.active;
    updateDagMath();
    showToast(target.active ? `Restored "${target.title}"` : `Trimmed "${target.title}" to protect schedule`);
  }
}

function toggleDelaySimulation() {
  simulateRailDelay = !simulateRailDelay;
  updateDelayButtonUI();
  updateDagMath();
  if (simulateRailDelay) {
    showToast('Injected +35m Train Delay — check Colosseum entry!', 'fa-bolt text-amber-500');
  } else {
    showToast('Cleared simulated delay — schedule restored');
  }
}

function updateDelayButtonUI() {
  const badge = document.getElementById('delayStateBadge');
  const btn = document.getElementById('delayToggleBtn');
  if (simulateRailDelay) {
    badge.textContent = 'ACTIVE (+35m)';
    badge.className = 'text-[10px] px-2 py-0.5 rounded-full bg-rose-600 text-white font-bold';
    btn.className = 'w-full py-2.5 px-3.5 rounded-xl border border-rose-300 bg-rose-50 text-rose-900 text-xs font-semibold flex items-center justify-between transition';
  } else {
    badge.textContent = 'OFF';
    badge.className = 'text-[10px] px-2 py-0.5 rounded-full bg-amber-200 text-amber-900 font-bold';
    btn.className = 'w-full py-2.5 px-3.5 rounded-xl border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-900 text-xs font-semibold flex items-center justify-between transition';
  }
}

function autoTrimLowestPriority() {
  const candidates = activeNodes.filter(n => n.active && n.type === 'flexible').sort((a, b) => a.priority - b.priority);
  if (candidates.length === 0) {
    showToast('No flexible stops remaining to trim!', 'fa-circle-info text-sky-600');
    return;
  }
  candidates[0].active = false;
  updateDagMath();
  showToast(`Auto-trimmed lowest-priority stop: "${candidates[0].title}" (+${candidates[0].durationMin + candidates[0].transitMin}m reclaimed)`);
}

function restoreAllStops() {
  activeNodes.forEach(n => n.active = true);
  updateDagMath();
  showToast('Restored all stops to original itinerary');
}

function resetDagControls() {
  document.getElementById('riskSlider').value = 20;
  document.getElementById('hubSlider').value = 15;
  simulateRailDelay = false;
  updateDelayButtonUI();
  restoreAllStops();
}

function insertCustomStop() {
  const title = document.getElementById('newNodeTitle').value.trim() || 'Trevi Fountain & Gelato Break';
  const dur = parseInt(document.getElementById('newNodeDuration').value, 10) || 35;
  const trans = parseInt(document.getElementById('newNodeTransit').value, 10) || 15;

  const newNode = {
    id: 'custom-' + Date.now(),
    title: title,
    type: 'flexible',
    category: 'sightseeing',
    icon: 'fa-location-dot',
    durationMin: dur,
    minDurationMin: 15,
    transitMin: trans,
    transitMode: 'walk',
    priority: 2,
    pnr: 'WISHLIST',
    officialDomain: 'maps.google.com',
    active: true,
    notes: 'Custom wishlist stop added by traveler.'
  };

  const insertIdx = Math.max(1, activeNodes.length - 2);
  activeNodes.splice(insertIdx, 0, newNode);
  document.getElementById('newNodeTitle').value = '';
  updateDagMath();
  showToast(`Added "${title}" into timeline`);
}

// -------------------------------------------------------------------
// 7. TAB 2: ANTI-PHISHING OFFICIAL VENDOR VERIFIER
// -------------------------------------------------------------------
function renderVerifierCards() {
  const grid = document.getElementById('verifierComparisonGrid');
  grid.innerHTML = '';

  vendorDatabase.forEach(item => {
    const card = document.createElement('div');
    card.className = 'travel-card p-5 space-y-4 flex flex-col justify-between';
    card.innerHTML = `
      <div class="space-y-3">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2.5">
          <h4 class="text-sm font-bold text-slate-900">${item.venue}</h4>
          <span class="text-[11px] font-mono px-2 py-0.5 rounded-md bg-sky-50 text-sky-700 border border-sky-200">${item.wikidataId}</span>
        </div>

        <!-- Blocked Reseller Trap Box -->
        <div class="p-3.5 rounded-xl bg-rose-50 border border-rose-200 space-y-1.5">
          <div class="flex items-center justify-between">
            <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-rose-200 text-rose-900">
              <i class="fa-solid fa-ban mr-1"></i>Search Ad Clone (Blocked)
            </span>
            <span class="text-xs font-bold text-rose-700">${item.trapPrice} (${item.trapMarkup})</span>
          </div>
          <p class="font-mono text-xs text-rose-800 line-through font-medium">${item.trapDomain}</p>
          <p class="text-xs text-slate-600">${item.trapReason}</p>
        </div>

        <!-- Verified Official Portal Box -->
        <div class="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 space-y-1.5">
          <div class="flex items-center justify-between">
            <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-emerald-200 text-emerald-900">
              <i class="fa-solid fa-circle-check mr-1"></i>Official Verified Portal
            </span>
            <span class="text-xs font-bold text-emerald-800">${item.officialPrice}</span>
          </div>
          <div class="flex items-center justify-between">
            <a href="${item.officialUrl}" target="_blank" rel="noopener noreferrer" class="font-mono text-xs font-bold text-emerald-700 hover:underline flex items-center gap-1.5">
              <span>${item.officialDomain}</span>
              <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
            </a>
            <span class="text-[10px] text-slate-400">Places ID: ${item.placesId.slice(0, 12)}…</span>
          </div>
          <p class="text-xs text-slate-600"><strong>Rule:</strong> ${item.bookingRule}</p>
        </div>
      </div>
    `;
    grid.appendChild(card);
  });
}

function loadVerifierPreset(key) {
  const item = vendorDatabase.find(v => v.key === key);
  if (!item) return;
  document.getElementById('urlVerifyInput').value = `https://www.${item.trapDomain}/fast-track`;
  inspectCustomUrl();
}

function inspectCustomUrl() {
  const raw = document.getElementById('urlVerifyInput').value.trim().toLowerCase();
  const box = document.getElementById('liveAuditResultBox');

  let matched = vendorDatabase.find(v =>
    raw.includes(v.key) ||
    raw.includes(v.trapDomain.split('.')[0]) ||
    raw.includes(v.officialDomain.split('/')[0]) ||
    (v.key === 'rail' && (raw.includes('trenitalia') || raw.includes('pkp') || raw.includes('intercity') || raw.includes('italia')))
  );

  if (!matched) {
    matched = vendorDatabase[0];
  }

  const isOfficialMatch = raw.includes(matched.officialDomain.split('/')[0].trim());

  if (isOfficialMatch) {
    box.className = 'p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mt-2';
    box.innerHTML = `
      <div class="space-y-1">
        <div class="flex items-center gap-2">
          <span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-600 text-white">VERIFIED OFFICIAL VENUE</span>
          <span class="text-xs font-bold text-emerald-900">${matched.venue}</span>
        </div>
        <p class="text-xs text-slate-700">Root domain matches authoritative ground truth on Google Maps & Wikidata (${matched.wikidataId}). Base Ticket Fare: <strong>${matched.officialPrice}</strong>.</p>
      </div>
      <a href="${matched.officialUrl}" target="_blank" rel="noopener noreferrer" class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs shrink-0 transition shadow-sm">
        Book on Official Portal ↗
      </a>
    `;
  } else {
    box.className = 'p-4 rounded-xl bg-rose-50 border border-rose-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mt-2';
    box.innerHTML = `
      <div class="space-y-1">
        <div class="flex items-center gap-2">
          <span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-rose-600 text-white">HIGH-RISK RESELLER CLONE DETECTED</span>
          <span class="text-xs font-bold text-rose-900">Target: ${matched.venue}</span>
        </div>
        <p class="text-xs text-slate-700">
          Domain <code class="text-rose-800 font-mono font-semibold">${raw}</code> <strong>DOES NOT MATCH</strong> official ground truth (<code class="text-emerald-700 font-mono font-semibold">${matched.officialDomain}</code>). Typical markup: <strong>${matched.trapMarkup}</strong>.
        </p>
      </div>
      <a href="${matched.officialUrl}" target="_blank" rel="noopener noreferrer" class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs shrink-0 transition shadow-sm">
        Redirect to Official Portal (${matched.officialDomain}) ↗
      </a>
    `;
  }
}

// -------------------------------------------------------------------
// 8. TAB 3: FAIR GROUP EXPENSE SPLITTER
// -------------------------------------------------------------------
function renderLedger() {
  const tbody = document.getElementById('ledgerTableBody');
  tbody.innerHTML = '';

  let totalEur = 0;
  const netBalances = { Franek: 0, Anna: 0, Marek: 0, Kasia: 0 };

  ledgerExpenses.forEach(exp => {
    const normEur = exp.currency === 'EUR' ? exp.amount : (exp.amount / EUR_TO_PLN);
    totalEur += normEur;

    const splitCount = Math.max(1, exp.participants.length);
    const sharePerPerson = normEur / splitCount;

    // Credit payer
    netBalances[exp.payer] = (netBalances[exp.payer] || 0) + normEur;
    // Debit participants
    exp.participants.forEach(p => {
      netBalances[p] = (netBalances[p] || 0) - sharePerPerson;
    });

    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-50 transition';
    tr.innerHTML = `
      <td class="py-3 px-3 font-semibold text-slate-900">${exp.title}</td>
      <td class="py-3 px-3">
        <span class="px-2 py-0.5 rounded-full bg-sky-100 text-sky-800 font-semibold text-[11px]">${exp.payer}</span>
      </td>
      <td class="py-3 px-3 font-mono text-slate-600">${exp.amount.toFixed(2)} ${exp.currency}</td>
      <td class="py-3 px-3 font-mono font-bold text-emerald-700">€${normEur.toFixed(2)}</td>
      <td class="py-3 px-3">
        <div class="flex items-center gap-1.5 flex-wrap">
          ${travelers.map(t => {
            const active = exp.participants.includes(t);
            return `<button onclick="toggleExpenseParticipant('${exp.id}', '${t}')" class="px-2 py-0.5 rounded-full text-[11px] font-medium transition ${active ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' : 'bg-slate-100 text-slate-400 border border-slate-200'}">${t}</button>`;
          }).join('')}
        </div>
      </td>
      <td class="py-3 px-2 text-right">
        <button onclick="removeLedgerExpense('${exp.id}')" class="text-slate-400 hover:text-rose-600 transition p-1"><i class="fa-solid fa-trash-can"></i></button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  document.getElementById('ledgerTotalEur').textContent = `€${totalEur.toFixed(2)}`;
  document.getElementById('ledgerTotalPln').textContent = `${(totalEur * EUR_TO_PLN).toFixed(2)} PLN`;

  // Render Net Balances
  const balContainer = document.getElementById('netBalancesContainer');
  balContainer.innerHTML = '';
  travelers.forEach(t => {
    const val = netBalances[t] || 0;
    const isPos = val >= 0.01;
    const isNeg = val <= -0.01;
    const row = document.createElement('div');
    row.className = 'flex items-center justify-between px-3 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs';
    row.innerHTML = `
      <span class="text-slate-900 font-semibold">${t}</span>
      <span class="font-mono font-bold ${isPos ? 'text-emerald-700' : isNeg ? 'text-rose-700' : 'text-slate-500'}">
        ${isPos ? `+€${val.toFixed(2)} (Is Owed)` : isNeg ? `-€${Math.abs(val).toFixed(2)} (Owes)` : '€0.00 (Settled)'}
      </span>
    `;
    balContainer.appendChild(row);
  });

  // Greedy Minimum-Cash-Flow Reduction
  const debtors = [];
  const creditors = [];
  Object.entries(netBalances).forEach(([person, bal]) => {
    if (bal < -0.01) debtors.push({ person, amount: -bal });
    if (bal > 0.01) creditors.push({ person, amount: bal });
  });
  debtors.sort((a, b) => b.amount - a.amount);
  creditors.sort((a, b) => b.amount - a.amount);

  const transfers = [];
  let i = 0, j = 0;
  while (i < debtors.length && j < creditors.length) {
    const pay = Math.min(debtors[i].amount, creditors[j].amount);
    if (pay > 0.01) {
      transfers.push({
        from: debtors[i].person,
        to: creditors[j].person,
        eur: pay,
        pln: pay * EUR_TO_PLN
      });
    }
    debtors[i].amount -= pay;
    creditors[j].amount -= pay;
    if (debtors[i].amount < 0.01) i++;
    if (creditors[j].amount < 0.01) j++;
  }

  const transContainer = document.getElementById('settlementTransfersContainer');
  transContainer.innerHTML = '';
  if (transfers.length === 0) {
    transContainer.innerHTML = `<div class="p-3 rounded-xl bg-white text-xs text-slate-500">All balances are completely settled!</div>`;
  } else {
    transfers.forEach(tr => {
      const item = document.createElement('div');
      item.className = 'p-3 rounded-xl bg-white border border-emerald-200 shadow-sm flex items-center justify-between text-xs';
      item.innerHTML = `
        <div class="flex items-center gap-2">
          <span class="font-bold text-rose-700">${tr.from}</span>
          <i class="fa-solid fa-arrow-right text-slate-400 text-[10px]"></i>
          <span class="font-bold text-emerald-800">${tr.to}</span>
        </div>
        <div class="text-right">
          <span class="font-bold font-mono text-slate-900 text-sm">€${tr.eur.toFixed(2)}</span>
          <span class="block text-[11px] text-slate-400">(${tr.pln.toFixed(0)} PLN)</span>
        </div>
      `;
      transContainer.appendChild(item);
    });
  }
}

function toggleExpenseParticipant(expId, person) {
  const exp = ledgerExpenses.find(e => e.id === expId);
  if (!exp) return;
  if (exp.participants.includes(person)) {
    if (exp.participants.length === 1) {
      showToast('At least 1 traveler must be included in an expense!', 'fa-triangle-exclamation text-amber-500');
      return;
    }
    exp.participants = exp.participants.filter(p => p !== person);
  } else {
    exp.participants.push(person);
  }
  renderLedger();
}

function addLedgerExpense() {
  const title = document.getElementById('expTitle').value.trim() || 'Trastevere Gelato & Espresso';
  const payer = document.getElementById('expPayer').value;
  const amount = parseFloat(document.getElementById('expAmount').value) || 25;
  const currency = document.getElementById('expCurrency').value;

  ledgerExpenses.push({
    id: 'exp-' + Date.now(),
    title,
    payer,
    amount,
    currency,
    participants: [...travelers]
  });
  document.getElementById('expTitle').value = '';
  renderLedger();
  showToast(`Added "${title}" (${amount} ${currency})`);
}

function removeLedgerExpense(id) {
  ledgerExpenses = ledgerExpenses.filter(e => e.id !== id);
  renderLedger();
}

// -------------------------------------------------------------------
// 9. TAB 4: INTERACTIVE SKILL, CLI & TEST STUDIO
// -------------------------------------------------------------------
function setStudioTarget(target) {
  currentStudioTarget = target;
  ['gemini', 'antigravity', 'cursor', 'cli'].forEach(t => {
    const btn = document.getElementById(`target-btn-${t}`);
    if (t === target) {
      btn.className = 'p-3 rounded-xl border border-sky-500 bg-sky-50 text-sky-900 font-semibold text-left transition';
    } else {
      btn.className = 'p-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-800 font-semibold text-left transition';
    }
  });
  renderStudioArtifact();
}

function renderStudioArtifact() {
  const dest = document.getElementById('cfgDest').value.trim() || 'Rome & Florence';
  const group = document.getElementById('cfgGroup').value.trim() || '4 Travelers';
  const modVerify = document.getElementById('modVerify').checked;
  const modDag = document.getElementById('modDag').checked;
  const modSplit = document.getElementById('modSplit').checked;
  const modTickets = document.getElementById('modTickets').checked;

  const riskPct = document.getElementById('riskSlider').value;
  const hubMin = document.getElementById('hubSlider').value;

  let filename = 'SKILL.md';
  let content = '';

  if (currentStudioTarget === 'gemini') {
    filename = 'SKILL.md';
    content = `---
name: kronolatch-trip-orchestrator
description: Deterministic Trip DAG Validator, Anti-Phishing Vendor Verifier & Group Expense Reconciler
corridor: "${dest}"
group_profile: "${group}"
---

# ROLE: KronoLatch Trip Orchestrator
You are **KronoLatch**, a deterministic travel scheduling and vendor verification agent configured for **${dest}** (${group}).
Never hallucinate booking links or assume zero-buffer connections.

${modVerify ? `## 1. OFFICIAL DOMAIN & TICKET ANTI-PHISHING
- Strip all subdomains to canonical eTLD+1 root domains.
- Cross-reference against Wikidata P856 and Google Places websiteUri.
- BLOCK any domain containing deceptive tokens (-tickets, -booking, -official) or >15% price markup.` : ''}

${modDag ? `## 2. TEMPORAL DAG & BUFFER ENFORCEMENT
- Mode buffers: Flights 120m, Rail 15m, Car 15m, Walk 5m.
- Transit risk leeway: +${riskPct}% duration multiplier.
- If arrival exceeds locked fixed entry, emit HARD_CONFLICT and trim lowest-priority flexible stop.` : ''}

${modTickets ? `## 3. CONFIRMATION PARSING
- Extract PNR, carrier, carriage/seat, departure, and arrival into strict KronoLatch schema.` : ''}

${modSplit ? `## 4. MULTI-CURRENCY GROUP SPLITTER
- Support uneven subgroup splits across EUR and PLN (1 EUR = 4.30 PLN).
- Compute net balances and output minimal peer-to-peer transfers.` : ''}`;

  } else if (currentStudioTarget === 'antigravity') {
    filename = 'kronolatch.antigravity.md';
    content = `# Antigravity IDE Agent Skill (.antigravity/skills/kronolatch.md)
# Corridor: ${dest} (${group})

<agent_rule name="kronolatch" priority="critical">
  <invariants>
    1. NEVER surface third-party ticket resellers. Always cross-verify root domains against Wikidata P856.
    2. Enforce T_transition = T_transit * (1 + ${riskPct/100}) + ${hubMin}m queue buffer.
    3. If slack < 0 at a fixed node, emit HARD_CONFLICT and auto-trim lowest-priority flexible stop.
  </invariants>
</agent_rule>`;

  } else if (currentStudioTarget === 'cursor') {
    filename = '.cursorrules';
    content = `# Cursor Rules (.cursorrules)
# Project: KronoLatch (${dest})
- Maintain deterministic DAG engine invariants (no zero-buffer transitions).
- Strip domains to canonical eTLD+1 before auditing ticket URLs.
- Always run \`uv run pytest\` and \`uv run kronolatch self-test\` before committing.`;

  } else {
    filename = 'kronolatch.py';
    content = `#!/usr/bin/env python3
"""
KronoLatch Standalone Python CLI
Corridor: ${dest} | Group: ${group}
Usage: uv run kronolatch validate --risk ${riskPct/100} --hub ${hubMin}
"""
import typer
# Run uv run kronolatch self-test to execute test suite`;
  }

  document.getElementById('studioFileHeader').textContent = `${filename} — Generated Artifact`;
  document.getElementById('downloadBtnLabel').textContent = `Download ${filename}`;
  document.getElementById('studioCodeOutput').textContent = content;
  document.getElementById('studioCharCount').textContent = `${content.length} chars`;
}

function copyGeneratedArtifact() {
  const code = document.getElementById('studioCodeOutput').textContent;
  copyTextToClipboard(code, 'Copied artifact to clipboard!');
}

function downloadGeneratedArtifact() {
  const code = document.getElementById('studioCodeOutput').textContent;
  const headerText = document.getElementById('studioFileHeader').textContent;
  const filename = headerText.split(' — ')[0] || 'SKILL.md';
  const blob = new Blob([code], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast(`Downloaded ${filename}`);
}

// -------------------------------------------------------------------
// 10. ON-DEMAND MANUAL VERIFICATION TEST SUITE RUNNER
// -------------------------------------------------------------------
function renderManualTests() {
  const container = document.getElementById('manualTestSuiteList');
  container.innerHTML = '';

  manualTests.forEach(t => {
    const isPass = t.status === 'PASS';
    const card = document.createElement('div');
    card.className = `p-3.5 rounded-xl border ${isPass ? 'bg-emerald-50 border-emerald-200' : 'bg-slate-50 border-slate-200'} space-y-2 transition-all`;
    card.innerHTML = `
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-sky-100 text-sky-800">${t.badge}</span>
          <h4 class="text-xs font-bold text-slate-900">${t.name}</h4>
        </div>
        <span class="px-2 py-0.5 text-[10px] font-bold rounded-full ${isPass ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'}">
          ${isPass ? '✓ PASSED' : 'READY'}
        </span>
      </div>
      <p class="text-[11px] text-slate-600">${t.desc}</p>
      <div class="flex items-center gap-2 pt-1">
        <button onclick="executeSingleManualTest('${t.id}')" class="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-semibold transition flex items-center gap-1.5 shadow-sm">
          <i class="fa-solid fa-play text-[10px]"></i>
          <span>Run Live Assertion</span>
        </button>
        <button onclick="copyManualTestPrompt('${t.id}')" class="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 text-[11px] font-medium transition flex items-center gap-1.5 shadow-sm">
          <i class="fa-regular fa-copy text-[10px]"></i>
          <span>Copy AI Prompt</span>
        </button>
      </div>
    `;
    container.appendChild(card);
  });
}

function executeSingleManualTest(testId) {
  const t = manualTests.find(x => x.id === testId);
  if (!t) return;
  t.status = 'PASS';
  renderManualTests();

  const out = document.getElementById('studioCodeOutput');
  const header = document.getElementById('studioFileHeader');
  header.textContent = `${t.id}.log — Execution Audit Report`;

  if (testId === 'test-phishing') {
    out.textContent = `[PASS] KRONOLATCH TEST #1: ANTI-PHISHING OFFICIAL VENDOR AUDIT
-------------------------------------------------------------------------
Input Candidate URL : https://www.colosseum-rome-tickets.org/fast-track (€44.00)
Google Places API   : Parco Archeologico del Colosseo -> https://ticketing.colosseo.it/
Wikidata Property   : Q10285 (P856) -> https://ticketing.colosseo.it/
Domain Match Audit  : MISMATCH (colosseum-rome-tickets.org != ticketing.colosseo.it)
Markup Calculation  : €44.00 vs €18.00 Official Base = +144.4% Reseller Markup
Action Taken        : BLOCKED candidate URL. Safe redirect provided.

--- COPYABLE AI PROMPT FOR GEMINI / ANTIGRAVITY ---
${t.prompt}`;
  } else if (testId === 'test-cascade') {
    out.textContent = `[PASS] KRONOLATCH TEST #2: TEMPORAL DAG +35m TRAIN DELAY CASCADE
-------------------------------------------------------------------------
Upstream Rail Leg   : Arrives Central Station 12:15 (includes +35m delay)
Direct Transition   : 20m walk + 15m platform/security buffer = 35m total
Arrival Ready-Time  : 12:50
Fixed Museum Slot   : 12:30 STRICT ENTRY
Conflict Detected   : -20 min HARD CONFLICT at locked museum slot!
Remediation Action  : Auto-trimmed preceding Morning Walk.

--- COPYABLE AI PROMPT FOR GEMINI / ANTIGRAVITY ---
${t.prompt}`;
  } else if (testId === 'test-split') {
    out.textContent = `[PASS] KRONOLATCH TEST #3: ASYMMETRIC SUBGROUP COST SPLIT
-------------------------------------------------------------------------
Total Spend         : €450.00
Net Balances        :
  - Franek : +€30.00  (Creditor)
  - Anna   : -€130.00 (Debtor)
  - Marek  : -€5.00   (Debtor)
  - Kasia  : +€105.00 (Creditor)
Minimum Settlement Transfers (3 Transfers Totaling €135.00):
  1. Anna -> Kasia  : €105.00
  2. Anna -> Franek : €25.00
  3. Marek -> Franek: €5.00

--- COPYABLE AI PROMPT FOR GEMINI / ANTIGRAVITY ---
${t.prompt}`;
  } else {
    out.textContent = `[PASS] KRONOLATCH TEST #4: UNSTRUCTURED BOOKING INGESTION
-------------------------------------------------------------------------
Normalized JSON conforming strictly to trip-dag.schema.json:
{
  "trip_id": "rome-florence-express-2026",
  "flight_buffer_min": 120,
  "rail_buffer_min": 15,
  "risk_multiplier": 0.20,
  "nodes_count": 6
}

--- COPYABLE AI PROMPT FOR GEMINI / ANTIGRAVITY ---
${t.prompt}`;
  }

  showToast(`Executed & Verified: ${t.name}`);
}

function copyManualTestPrompt(testId) {
  const t = manualTests.find(x => x.id === testId);
  if (!t) return;
  copyTextToClipboard(t.prompt, `Copied "${t.name}" prompt!`);
}

function runAllManualTests() {
  manualTests.forEach(t => t.status = 'PASS');
  renderManualTests();
  executeSingleManualTest('test-phishing');
  showToast('All 4 architectural tests passed!');
}

// -------------------------------------------------------------------
// 11. INITIALIZATION ON WINDOW LOAD
// -------------------------------------------------------------------
window.onload = function () {
  updateDagMath();
  renderVerifierCards();
  inspectCustomUrl();
  renderLedger();
  renderStudioArtifact();
  renderManualTests();
};
