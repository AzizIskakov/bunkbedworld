import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_FILE = path.join(__dirname, 'products.json');
const PROGRESS_FILE = path.join(__dirname, 'scrape_progress.json');

// Load products
const products = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));

// Stats
let stats = { total: products.length, skipped: 0, fetched: 0, errors: 0, updated: 0, fields_filled: {} };

// Load progress if exists
let progress = {};
if (fs.existsSync(PROGRESS_FILE)) {
  try { progress = JSON.parse(fs.readFileSync(PROGRESS_FILE, 'utf8')); } catch(e) {}
}

const NEED_FIELDS = ['color', 'material', 'dimensions', 'description', 'sell_price', 'cost_price'];

function needsUpdate(p) {
  return NEED_FIELDS.some(f => !p[f] && p[f] !== 0 && p[f] !== false);
}

function saveProgress() {
  fs.writeFileSync(PROGRESS_FILE, JSON.stringify({ index: progress.index, stats }, null, 2));
}

function saveProducts() {
  fs.writeFileSync(DATA_FILE, JSON.stringify(products, null, 2));
}

// Parse paragraph text from wsite description
function parseDescription(html) {
  // Extract text from #wsite-com-product-short-description .paragraph
  const match = html.match(/<div[^>]*id="wsite-com-product-short-description"[^>]*>.*?<div[^>]*class="paragraph"[^>]*>(.*?)<\/div>/s);
  if (!match) return {};

  let text = match[1]
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .trim();

  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  const result = {};

  for (const line of lines) {
    const lc = line.toLowerCase();

    if (lc.startsWith('item name') || lc.startsWith('name')) {
      const val = line.split(':').slice(1).join(':').trim();
      if (val) result.name_from_page = val;
    }
    else if (lc.startsWith('color')) {
      const val = line.split(':').slice(1).join(':').trim();
      if (val) result.color = val;
    }
    else if (lc.startsWith('dimensions') || lc.startsWith('dimension')) {
      const val = line.split(':').slice(1).join(':').trim();
      if (val) result.dimensions = val;
    }
    else if (lc.startsWith('material')) {
      const val = line.split(':').slice(1).join(':').trim();
      if (val) result.material = val;
    }
    else if (lc.startsWith('features') || lc.startsWith('feature')) {
      const val = line.split(':').slice(1).join(':').trim();
      if (val) result.description = val;
    }
    else if (lc.startsWith('retail code') || lc.startsWith('code')) {
      // Skip - internal code, not useful for display
    }
    else if (lc.startsWith('sold') || lc.includes('sold out')) {
      result.sold_out = true;
    }
    else if (lc.includes('usb') || lc.includes('led') || lc.includes('charg') || lc.includes('cup holder')) {
      // Accumulate as description details
      if (!result.features) result.features = [];
      result.features.push(line);
    }
  }

  return result;
}

// Try to extract price from the page
function parsePrice(html) {
  // Look for price in JSON+LD
  const ldMatch = html.match(/<script[^>]*type="application\/ld\+json"[^>]*>(.*?)<\/script>/s);
  if (ldMatch) {
    try {
      const ld = JSON.parse(ldMatch[1]);
      if (ld.offers && ld.offers.price) return parseFloat(ld.offers.price);
    } catch(e) {}
  }

  // Look for price in specific spans
  const priceMatch = html.match(/<span[^>]*id="wsite-com-product-price"[^>]*>.*?(\$[\d,]+\.?\d*)/);
  if (priceMatch) {
    return parseFloat(priceMatch[1].replace(/[$,]/g, ''));
  }

  // Try common patterns
  const pricePatt = html.match(/\$(\d+\.?\d{0,2})/);
  if (pricePatt) return parseFloat(pricePatt[1]);

  return null;
}

// Also try to extract full description from the long description area
function parseLongDescription(html) {
  const match = html.match(/<div[^>]*id="wsite-com-product-description"[^>]*>.*?<div[^>]*class="paragraph"[^>]*>(.*?)<\/div>/s);
  if (!match) return '';

  let text = match[1]
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .trim();

  return text;
}

async function fetchPage(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  try {
    const resp = await fetch(url, { signal: controller.signal });
    clearTimeout(timeout);
    if (!resp.ok) return null;
    return await resp.text();
  } catch(e) {
    clearTimeout(timeout);
    return null;
  }
}

async function main() {
  let startIdx = progress.index || 0;
  let batchCount = 0;

  for (let i = startIdx; i < products.length; i++) {
    const product = products[i];

    // Check if product needs any field updates and has a page URL
    if (!product.page) {
      stats.skipped++;
      progress.index = i + 1;
      continue;
    }

    if (!needsUpdate(product)) {
      stats.skipped++;
      progress.index = i + 1;
      continue;
    }

    // Already processed in a previous run?
    const procKey = product.id;
    if (progress[procKey] === true) {
      stats.skipped++;
      progress.index = i + 1;
      continue;
    }

    // Fetch
    process.stdout.write(`[${i+1}/${products.length}] Fetching ${product.id}... `);
    const html = await fetchPage(product.page);
    if (!html) {
      console.log('ERROR (fetch failed)');
      stats.errors++;
      progress[procKey] = true;
      progress.index = i + 1;
      batchCount++;
      if (batchCount >= 20) { saveProducts(); saveProgress(); batchCount = 0; }
      await sleep(1000);
      continue;
    }

    let updated = false;

    // Parse short description fields
    const parsed = parseDescription(html);

    for (const field of ['color', 'material', 'dimensions']) {
      if (!product[field] && parsed[field]) {
        product[field] = parsed[field];
        stats.fields_filled[field] = (stats.fields_filled[field] || 0) + 1;
        updated = true;
      }
    }

    // Description: try short description first
    if (!product.description) {
      if (parsed.description) {
        product.description = parsed.description;
        stats.fields_filled.description = (stats.fields_filled.description || 0) + 1;
        updated = true;
      } else if (parsed.features && parsed.features.length > 0) {
        // Build description from unmatched feature lines
        let descText = parsed.features.join('\n');
        // Also check long description
        const longDesc = parseLongDescription(html);
        if (longDesc && longDesc.length > descText.length) {
          descText = longDesc;
        }
        if (descText) {
          product.description = descText;
          stats.fields_filled.description = (stats.fields_filled.description || 0) + 1;
          updated = true;
        }
      } else {
        const longDesc = parseLongDescription(html);
        if (longDesc) {
          product.description = longDesc;
          stats.fields_filled.description = (stats.fields_filled.description || 0) + 1;
          updated = true;
        }
      }
    }

    // Price: only fill if currently missing
    if (!product.sell_price && !product.cost_price) {
      const price = parsePrice(html);
      if (price) {
        if (!product.sell_price) product.sell_price = price;
        stats.fields_filled.sell_price = (stats.fields_filled.sell_price || 0) + 1;
        updated = true;
      }
    }

    if (updated) {
      stats.updated++;
      console.log('UPDATED');
    } else {
      console.log('no new data found');
      stats.skipped++;
    }

    progress[procKey] = true;
    progress.index = i + 1;
    batchCount++;

    if (batchCount >= 20) {
      saveProducts();
      saveProgress();
      console.log(`  ✓ Saved checkpoint (${i+1}/${products.length})`);
      batchCount = 0;
    }

    // Rate limit: 1 second between requests
    await sleep(1200);
  }

  // Final save
  saveProducts();
  saveProgress();

  // Summary
  const summary = `# Scrape Complete

## Stats
- Total products: ${stats.total}
- Fetched: ${stats.fetched}
- Updated: ${stats.updated}
- Skipped (already complete): ${stats.skipped}
- Errors: ${stats.errors}

## Fields Filled
${Object.entries(stats.fields_filled).map(([f, c]) => `- ${f}: ${c}`).join('\n')}

## Remaining gaps
- Color: ${products.filter(p => !p.color).length}
- Material: ${products.filter(p => !p.material).length}
- Dimensions: ${products.filter(p => !p.dimensions).length}
- Description: ${products.filter(p => !p.description).length}
- Missing sell_price: ${products.filter(p => !p.sell_price).length}
`;

  fs.writeFileSync(path.join(__dirname, 'SCRAPE_DONE.md'), summary);
  console.log('\n' + summary);
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

main().catch(err => {
  console.error('Fatal error:', err);
  saveProducts();
  saveProgress();
});