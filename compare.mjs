#!/usr/bin/env node
// Compare a Collectr showcase portfolio against TCGplayer market prices.
//
// Sources:
//   1. Collectr public showcase page (rendered with Playwright, data read from the Next.js payload)
//   2. PokemonPriceTracker API (TCGplayer prices, variant + condition aware, daily history, eBay graded sales)
//   3. TCGplayer's own public marketplace endpoint (live market price, used as a cross-check)
//
// Usage:
//   API_KEY=... npm run compare -- [--profile <uuid>] [--collection Main] [--grade <productId>=psa9] [--out reports/<date>]

import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const DEFAULT_PROFILE = '7f99da14-80b0-4914-99c7-44162fab4d04';
const PPT_URL = 'https://www.pokemonpricetracker.com/api/v2/cards';
const TCG_HEADERS = {
  'User-Agent': 'Mozilla/5.0',
  Origin: 'https://www.tcgplayer.com',
  Referer: 'https://www.tcgplayer.com/',
};
const UNGRADED_ID = '52';
const CONDITIONS = { NM: 'Near Mint', LP: 'Lightly Played', MP: 'Moderately Played', HP: 'Heavily Played', DMG: 'Damaged' };
const GRADE_KEYS = ['psa10', 'psa9', 'psa8', 'cgc10', 'cgc9_5', 'bgs9_5', 'bgs9', 'tag10', 'ace10'];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const round2 = (n) => (n == null ? null : Math.round(n * 100) / 100);

function parseArgs(argv) {
  const out = { grades: {} };
  for (let i = 0; i < argv.length; i++) {
    const key = argv[i].replace(/^--/, '');
    const val = argv[++i];
    if (key === 'grade') {
      const [id, grade] = val.split('=');
      out.grades[id] = grade.toLowerCase().replace('.', '_');
    } else {
      out[key] = val;
    }
  }
  return out;
}

// ---------- Collectr ----------

// Return the JSON value (object or array) that starts at str[i].
function sliceJson(str, i) {
  const open = str[i];
  const close = open === '[' ? ']' : '}';
  let depth = 0;
  let inStr = false;
  for (let j = i; j < str.length; j++) {
    const c = str[j];
    if (inStr) {
      if (c === '\\') j++;
      else if (c === '"') inStr = false;
    } else if (c === '"') inStr = true;
    else if (c === open) depth++;
    else if (c === close && --depth === 0) return JSON.parse(str.slice(i, j + 1));
  }
  throw new Error('Unterminated JSON in Collectr payload');
}

function parseShowcase(html) {
  const chunks = [...html.matchAll(/self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)/g)];
  const rsc = chunks.map((m) => JSON.parse(`"${m[1]}"`)).join('');
  const anchor = rsc.indexOf('"showcaseEnabled"');
  if (anchor < 0) throw new Error('Showcase data not found in Collectr page');
  const field = (name) => {
    const k = rsc.indexOf(`"${name}":`, anchor);
    if (k < 0) throw new Error(`Field ${name} not found in Collectr payload`);
    const v = k + name.length + 3;
    return rsc[v] === '[' || rsc[v] === '{' ? sliceJson(rsc, v) : JSON.parse(rsc.slice(v, rsc.indexOf(',', v)));
  };
  return {
    collections: field('collections'),
    products: field('products'),
    portfolioValue: Number(field('portfolio_value')[0]?.price),
    totals: { cards: Number(field('total_cards')), sealed: Number(field('total_sealed')), graded: Number(field('total_graded')) },
  };
}

async function loadCollectr(profileId, collectionName) {
  const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined;
  const browser = await chromium.launch(proxy ? { proxy } : {});
  try {
    const page = await browser.newPage();
    await page.goto(`https://app.getcollectr.com/showcase/profile/${profileId}`, { waitUntil: 'networkidle', timeout: 90000 });
    const data = parseShowcase(await page.content());
    const shown = data.collections.find((c) => c.default);
    if (!shown || shown.name !== collectionName) {
      throw new Error(`Showcase shows "${shown?.name}" by default; only the default collection can be read (asked for "${collectionName}")`);
    }
    const expected = data.totals.cards + data.totals.sealed + data.totals.graded;
    const got = data.products.reduce((s, p) => s + Number(p.quantity), 0);
    if (got < expected) console.warn(`Warning: page lists ${got} items but profile reports ${expected}; extra pages were not loaded`);
    return data;
  } finally {
    await browser.close();
  }
}

// ---------- PokemonPriceTracker ----------

async function ppt(params) {
  const url = `${PPT_URL}?${new URLSearchParams(params)}`;
  for (let attempt = 0; attempt < 4; attempt++) {
    const r = await fetch(url, { headers: { Authorization: `Bearer ${process.env.API_KEY}` } });
    await sleep(1100); // 60 calls/min limit
    if (r.status === 429) {
      await sleep(15000);
      continue;
    }
    if (r.status === 401 || r.status === 403) throw new Error(`PokemonPriceTracker rejected the API key (${r.status})`);
    if (!r.ok) return [];
    const body = await r.json();
    const d = body.data;
    return Array.isArray(d) ? d : d ? [d] : [];
  }
  return [];
}

const cleanName = (n) => n.replace(/\(JP\)/g, '').replace(/\s+-\s+\d+\s*$/, '').trim();
const cleanNumber = (n) => String(n || '').replace(/^[A-Z]+\s+/, '').replace(/^0+/, '').toLowerCase();

async function findCard(p, extra) {
  for (const language of ['english', 'japanese']) {
    const [card] = await ppt({ tcgPlayerId: p.product_id, language, ...extra });
    if (card) return { card, language, remapped: false };
  }
  // Collectr has its own IDs for some cards (mostly Japanese); search by name + number instead.
  for (const language of ['japanese', 'english']) {
    const hits = await ppt({ search: `${cleanName(p.product_name)} ${p.card_number}`, language, limit: 10 });
    const hit = hits.find((c) => cleanNumber(c.cardNumber) === cleanNumber(p.card_number));
    if (hit) {
      const [card] = await ppt({ tcgPlayerId: hit.tcgPlayerId, language, ...extra });
      if (card) return { card, language, remapped: true };
    }
  }
  return null;
}

function variantPrice(card, subType, cond) {
  const variants = card.prices?.variants || {};
  const name = variants[subType] ? subType : card.prices?.primaryPrinting;
  const byCond = variants[name] || {};
  const key = Object.keys(byCond).find((k) => k.startsWith(cond));
  const price = key ? byCond[key].price : card.variants?.[name]?.marketPrice;
  return { variant: name, price: price ?? null, exact: name === subType };
}

function history(card, variant, cond) {
  const h = card.priceHistory?.variants?.[variant]?.[cond]?.history || [];
  return h.map((x) => ({ date: x.date.slice(0, 10), market: x.market }));
}

// All history dates whose TCGplayer price equals the given price (flat prices match several days).
function matchDates(hist, price) {
  return hist.filter((x) => Math.abs(x.market - price) < 0.006).map((x) => x.date);
}

// ---------- TCGplayer ----------

async function tcgLive(productId, subType, card) {
  try {
    const r = await fetch(`https://mpapi.tcgplayer.com/v2/product/${productId}/pricepoints`, { headers: TCG_HEADERS });
    if (!r.ok) return null;
    const points = await r.json();
    const bucket = subType === 'Normal' || subType.endsWith(' Normal') ? 'Normal' : 'Foil';
    // TCGplayer only splits Normal/Foil here, so it is ambiguous when a card has several foil printings.
    const sameBucket = (card?.printingsAvailable || []).filter((v) => (v.includes('Normal') ? 'Normal' : 'Foil') === bucket);
    if (sameBucket.length > 1) return null;
    return points.find((x) => x.printingType === bucket)?.marketPrice ?? null;
  } catch {
    return null;
  }
}

// ---------- Main ----------

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!process.env.API_KEY) throw new Error('Set API_KEY (PokemonPriceTracker key) in the environment');
  const profile = args.profile || DEFAULT_PROFILE;
  const collection = args.collection || 'Main';
  const runAt = new Date();
  const outDir = args.out || path.join('reports', runAt.toISOString().slice(0, 10));

  console.log(`Loading Collectr showcase ${profile} (${collection})...`);
  const collectr = await loadCollectr(profile, collection);
  console.log(`  ${collectr.products.length} line items, Collectr total $${collectr.portfolioValue.toFixed(2)}`);

  const rows = [];
  const raw = [];
  for (const p of collectr.products) {
    const graded = p.grade_id !== UNGRADED_ID;
    const cond = CONDITIONS[p.card_condition] || 'Near Mint';
    const found = await findCard(p, { includeHistory: 'true', days: 14, ...(graded ? { includeEbay: 'true' } : {}) });
    const card = found?.card;
    const tcgId = card?.tcgPlayerId || p.product_id;
    const collectrPrice = Number(p.market_price);
    const collectrBase = collectrPrice - Number(p.market_price_diff);
    const row = {
      collectr_id: p.product_id,
      tcgplayer_id: card ? tcgId : '',
      name: cleanName(p.product_name),
      set: p.catalog_group,
      number: p.card_number,
      printing: p.product_sub_type,
      condition: p.card_condition,
      grade: graded ? args.grades[p.product_id] || `unknown (Collectr grade_id ${p.grade_id})` : 'raw',
      qty: Number(p.quantity),
      collectr: round2(collectrPrice),
      api: null,
      tcg_live: null,
      diff: null,
      diff_pct: null,
      collectr_matches_tcg_on: null,
      collectr_change_base_on: null,
      freshness: null,
      note: '',
    };
    if (!card) {
      row.note = 'Not found on TCGplayer';
    } else if (graded) {
      const sales = card.ebay?.salesByGrade || {};
      const g = args.grades[p.product_id];
      const s = g && sales[g];
      row.api = s ? round2(s.smartMarketPrice?.price ?? s.medianPrice) : null;
      row.note = GRADE_KEYS.filter((k) => sales[k])
        .map((k) => `${k} median $${round2(sales[k].medianPrice)} (n=${sales[k].count})`)
        .join('; ');
      if (!g) row.note = `Pass --grade ${p.product_id}=<grade> to score. eBay: ${row.note}`;
    } else {
      const vp = variantPrice(card, p.product_sub_type, cond);
      const hist = history(card, vp.variant, cond);
      row.api = round2(vp.price);
      row.tcg_live = round2(await tcgLive(tcgId, p.product_sub_type, card));
      const latest = hist.at(-1)?.date;
      row.collectr_matches_tcg_on = matchDates(hist, collectrPrice).join(' ') || null;
      row.collectr_change_base_on = matchDates(hist, collectrBase).join(' ') || null;
      row.freshness = !row.collectr_matches_tcg_on
        ? 'no match'
        : row.collectr_matches_tcg_on.includes(latest)
          ? 'current'
          : `stale (${row.collectr_matches_tcg_on.split(' ').at(-1)})`;
      const notes = [];
      if (found.remapped) notes.push(`Collectr uses its own ID ${p.product_id}; TCGplayer listing is ${tcgId}`);
      if (!vp.exact) notes.push(`printing "${p.product_sub_type}" not on TCGplayer, used ${vp.variant}`);
      const others = (card.printingsAvailable || []).filter((v) => v !== vp.variant && card.variants?.[v]?.marketPrice != null);
      if (others.length) {
        notes.push(`other printings: ${others.map((v) => `${v} $${round2(card.variants[v].marketPrice)}`).join(', ')}`);
      }
      row.note = notes.join('; ');
    }
    if (row.api != null) {
      row.diff = round2(row.collectr - row.api);
      row.diff_pct = round2((row.diff / row.api) * 100);
    }
    rows.push(row);
    raw.push({ collectr: p, ppt: card || null });
    console.log(`  ${row.name.padEnd(28)} Collectr ${String(row.collectr).padStart(7)}  API ${String(row.api).padStart(7)}  TCG ${String(row.tcg_live).padStart(7)}`);
  }

  const summary = summarize(rows, collectr, runAt);
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'comparison.csv'), toCsv(rows));
  fs.writeFileSync(path.join(outDir, 'raw.json'), JSON.stringify({ runAt, profile, collection, raw }, null, 1));
  fs.writeFileSync(path.join(outDir, 'report.md'), toMarkdown(rows, summary, profile, collection));
  console.log(`\nWrote ${outDir}/report.md, comparison.csv, raw.json`);
  console.log(JSON.stringify(summary, null, 1));
}

function summarize(rows, collectr, runAt) {
  const scored = rows.filter((r) => r.grade === 'raw' && r.api != null);
  const abs = scored.map((r) => Math.abs(r.diff_pct)).sort((a, b) => a - b);
  const sum = (xs, f) => round2(xs.reduce((s, r) => s + f(r) * r.qty, 0));
  const live = scored.filter((r) => r.tcg_live != null);
  const tally = (xs) => xs.reduce((o, x) => ((o[x] = (o[x] || 0) + 1), o), {});
  const freshness = tally(scored.map((r) => r.freshness));
  // Only cards whose price moved give an unambiguous date, so count single-date matches.
  const single = (field) => tally(scored.map((r) => r[field]).filter((d) => d && !d.includes(' ')));
  return {
    runAt: runAt.toISOString(),
    collectrTotal: round2(collectr.portfolioValue),
    lineItems: rows.length,
    rawScored: scored.length,
    collectrTotalScored: sum(scored, (r) => r.collectr),
    apiTotalScored: sum(scored, (r) => r.api),
    medianAbsPct: round2(abs[Math.floor(abs.length / 2)]),
    meanAbsPct: round2(abs.reduce((s, x) => s + x, 0) / (abs.length || 1)),
    within1pct: abs.filter((x) => x <= 1).length,
    within2pct: abs.filter((x) => x <= 2).length,
    within5pct: abs.filter((x) => x <= 5).length,
    exactMatches: scored.filter((r) => r.diff === 0).length,
    apiVsTcgLiveMedianAbsPct: round2(
      live.map((r) => Math.abs(((r.api - r.tcg_live) / r.tcg_live) * 100)).sort((a, b) => a - b)[Math.floor(live.length / 2)]
    ),
    freshness,
    collectrPriceMatchesTcgOn: single('collectr_matches_tcg_on'),
    collectrChangeBaseMatchesTcgOn: single('collectr_change_base_on'),
  };
}

function toCsv(rows) {
  const cols = Object.keys(rows[0]);
  const esc = (v) => (v == null ? '' : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
  return [cols.join(','), ...rows.map((r) => cols.map((c) => esc(r[c])).join(','))].join('\n') + '\n';
}

function toMarkdown(rows, s, profile, collection) {
  const money = (n) => (n == null ? 'n/a' : `$${n.toFixed(2)}`);
  const pct = (n) => (n == null ? '' : `${n > 0 ? '+' : ''}${n.toFixed(1)}%`);
  const lines = [
    `# Collectr vs TCGplayer: ${collection} folder`,
    '',
    `Run: ${s.runAt} · Collectr profile \`${profile}\``,
    '',
    '## Summary',
    '',
    `- Collectr total: **${money(s.collectrTotal)}** across ${s.lineItems} line items`,
    `- Raw cards scored against the API: ${s.rawScored}. Collectr ${money(s.collectrTotalScored)} vs API ${money(s.apiTotalScored)} (${pct(((s.collectrTotalScored - s.apiTotalScored) / s.apiTotalScored) * 100)})`,
    `- Per card error: median ${s.medianAbsPct}%, mean ${s.meanAbsPct}%. Within 1%: ${s.within1pct}, within 2%: ${s.within2pct}, within 5%: ${s.within5pct} of ${s.rawScored}. Exact to the cent: ${s.exactMatches}`,
    `- API vs TCGplayer live (sanity check on the API itself): median gap ${s.apiVsTcgLiveMedianAbsPct}%`,
    `- Freshness (does Collectr's price equal TCGplayer's latest daily price, or an older one): ${JSON.stringify(s.freshness)}`,
    `- Cards that match exactly one day of TCGplayer history, by day: ${JSON.stringify(s.collectrPriceMatchesTcgOn)}`,
    `- Day Collectr measures its +/- change from (single-day matches): ${JSON.stringify(s.collectrChangeBaseMatchesTcgOn)}`,
    '',
    '## Cards',
    '',
    '| Card | Set | # | Grade | Collectr | API (TCGplayer) | TCGplayer live | Diff | Freshness | Note |',
    '|---|---|---|---|--:|--:|--:|--:|---|---|',
    ...rows.map(
      (r) =>
        `| ${r.name} | ${r.set} | ${r.number} | ${r.grade} | ${money(r.collectr)} | ${money(r.api)} | ${money(r.tcg_live)} | ${pct(r.diff_pct)} | ${r.freshness || ''} | ${r.note.replace(/\|/g, '/')} |`
    ),
    '',
  ];
  return lines.join('\n');
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
