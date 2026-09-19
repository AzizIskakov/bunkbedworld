#!/usr/bin/env python3
"""Generate BunkBedWorld index.html from happy-homes-data.md"""

import re, json

# Read the markdown data
with open('happy-homes-data.md', 'r', encoding='utf-8') as f:
    md = f.read()

# Parse categories and products
categories = []
current_cat = None
current_cat_url = None

lines = md.split('\n')
for i, line in enumerate(lines):
    m = re.match(r'^## (.+?)\s*\((/c\d+)\)', line)
    if m:
        current_cat = m.group(1).strip()
        current_cat_url = m.group(2)
        categories.append({
            'name': current_cat,
            'products': [],
            'url': current_cat_url
        })
        continue
    # Parse product rows: | N | Product Name | image_url | product_page |
    if current_cat and line.strip().startswith('| '):
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 5 and re.match(r'^\d+$', parts[1]):
            name = parts[2]
            img = parts[3]
            page = parts[4]
            # Extract product ID from page URL
            pid_m = re.search(r'/store/(p\d+)/', page)
            pid = pid_m.group(1) if pid_m else f"p{len(categories[-1]['products'])}"
            categories[-1]['products'].append({
                'id': pid,
                'name': name,
                'image': img,
                'page': page
            })

# Tab mapping: which categories go under which tab
tab_map = {
    'Living Room': [
        'Stationary Sofa & Loveseats',
        'Stationary Sectionals',
        'Reclining Sofa & Loveseats',
        'Reclining Sectionals',
        'Recliners & Lift Chairs',
        'Occasional Tables',
        'TV Stands',
        'Sleepers & Futons',
        'Accessories',
        'Office & Bookcase'
    ],
    'Bed Room': [
        'Beds',
        'Bedrooms',
        'Daybeds',
        'Mattresses',
        'Vanities & Mirrors'
    ],
    'Dining Room': [
        'Dining Rooms',
        'Barstools'
    ],
    'Bunk Beds': [
        'Bunk Beds'
    ]
}

# Build lookup: cat name -> products
cat_lookup = {c['name']: c for c in categories}

# Build all products JSON
all_products = []
for cat in categories:
    for p in cat['products']:
        all_products.append({
            'id': p['id'],
            'name': p['name'],
            'image': p['image'],
            'page': p['page'],
            'category': cat['name']
        })

products_json = json.dumps(all_products)

# Escape for embedding in HTML
escaped_json = products_json.replace('</', '<\\/')

# Count products per category for display
cat_counts = {}
for cat in categories:
    cat_counts[cat['name']] = len(cat['products'])

# Generate tab structure JSON
tab_structure = []
for tab_name, subcats in tab_map.items():
    entries = []
    for sc in subcats:
        cat = cat_lookup.get(sc)
        if cat:
            entries.append({
                'name': sc,
                'count': len(cat['products']),
                'cat_id': cat['url'].replace('/', '')
            })
    tab_structure.append({
        'tab': tab_name,
        'categories': entries
    })
tab_json = json.dumps(tab_structure)

oz_old_html = open('index.html', 'r', encoding='utf-8').read()

# Build the new HTML - complete rewrite
html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BunkBedWorld – Furniture for Every Room</title>
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8f7f4;
            color: #2c2c2c;
            line-height: 1.6;
        }
        .header {
            background: #1a1a2e;
            color: #fff;
            padding: 1.2rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 1rem;
        }
        .logo { font-size: 1.8rem; font-weight: 800; letter-spacing: -0.5px; }
        .logo span { color: #e8b86d; }
        .tagline { font-size: 0.9rem; color: #aaa; }
        .hero {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            padding: 4rem 2rem;
            text-align: center;
        }
        .hero h1 { font-size: 2.8rem; font-weight: 800; margin-bottom: 0.8rem; }
        .hero h1 span { color: #e8b86d; }
        .hero p { font-size: 1.15rem; color: #b0b0c0; max-width: 600px; margin: 0 auto 1.5rem; }

        .tab-nav {
            display: flex;
            background: #fff;
            border-bottom: 2px solid #e0ddd8;
            position: sticky;
            top: 0;
            z-index: 10;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .tab-btn {
            flex: 1;
            padding: 1rem 1.2rem;
            text-align: center;
            font-weight: 600;
            font-size: 0.95rem;
            color: #777;
            background: none;
            border: none;
            cursor: pointer;
            transition: color 0.2s, background 0.2s, border-color 0.2s;
            border-bottom: 3px solid transparent;
        }
        .tab-btn:hover { color: #1a1a2e; background: #f8f7f4; }
        .tab-btn.active {
            color: #1a1a2e;
            border-bottom-color: #e8b86d;
            background: #fff;
        }
        .tab-btn .count {
            display: inline-block;
            background: #e8b86d20;
            color: #1a1a2e;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 0.1rem 0.5rem;
            border-radius: 12px;
            margin-left: 0.4rem;
        }

        .container { max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .subcat-bar {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }
        .subcat-bar label { font-weight: 600; font-size: 0.9rem; color: #555; }
        .subcat-select {
            padding: 0.6rem 1.2rem;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 0.95rem;
            font-weight: 500;
            background: #fff;
            color: #1a1a2e;
            cursor: pointer;
            transition: border-color 0.2s;
            min-width: 200px;
            max-width: 100%;
        }
        .subcat-select:focus { outline: none; border-color: #e8b86d; }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 1.8rem;
        }

        .card {
            background: #fff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
            transition: transform 0.25s, box-shadow 0.25s;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
            display: block;
        }
        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 28px rgba(0,0,0,0.1);
        }
        .card-img {
            width: 100%;
            height: 200px;
            background: #e8e3dc;
            background-size: cover;
            background-position: center;
            position: relative;
        }
        .card-body { padding: 1.2rem 1.2rem 1.4rem; }
        .card-body h3 {
            font-size: 0.95rem;
            margin-bottom: 0.2rem;
            color: #1a1a2e;
            line-height: 1.3;
        }
        .card-body .cat-tag {
            font-size: 0.72rem;
            color: #e8b86d;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 0.2rem;
        }
        .card-body .desc {
            font-size: 0.82rem;
            color: #888;
        }

        /* Product Detail View */
        .detail-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.6);
            z-index: 100;
            justify-content: center;
            align-items: center;
            padding: 2rem;
        }
        .detail-overlay.active { display: flex; }
        .detail-card {
            background: #fff;
            border-radius: 16px;
            max-width: 700px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
            padding: 2rem;
            position: relative;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .detail-close {
            position: absolute;
            top: 1rem; right: 1rem;
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: #888;
            width: 40px; height: 40px;
            display: flex; align-items: center; justify-content: center;
            border-radius: 50%;
            transition: background 0.2s;
        }
        .detail-close:hover { background: #f0f0f0; }
        .detail-card img {
            width: 100%;
            max-height: 400px;
            object-fit: cover;
            border-radius: 12px;
            margin-bottom: 1.5rem;
        }
        .detail-card h2 { font-size: 1.5rem; color: #1a1a2e; margin-bottom: 0.5rem; }
        .detail-card .cat-tag {
            font-size: 0.82rem; color: #e8b86d; font-weight: 600;
            text-transform: uppercase; margin-bottom: 1rem;
        }
        .detail-card .price-badge {
            display: inline-block;
            background: #e8b86d20;
            color: #1a1a2e;
            font-weight: 700;
            padding: 0.5rem 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        .detail-card .btn-happy {
            display: inline-block;
            background: #1a1a2e;
            color: #fff;
            text-decoration: none;
            padding: 0.7rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            transition: background 0.2s;
            margin-top: 0.5rem;
        }
        .detail-card .btn-happy:hover { background: #2c2c4e; }
        .detail-card .btn-back {
            display: inline-block;
            background: #eee;
            color: #333;
            text-decoration: none;
            padding: 0.7rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            margin-right: 0.5rem;
            transition: background 0.2s;
            border: none;
            cursor: pointer;
        }
        .detail-card .btn-back:hover { background: #ddd; }

        .footer {
            background: #1a1a2e;
            color: #888;
            text-align: center;
            padding: 2.5rem 2rem;
            margin-top: 2rem;
        }
        .footer strong { color: #e8b86d; }

        .loading {
            text-align: center;
            padding: 4rem;
            color: #888;
        }

        @media (max-width: 600px) {
            .header { flex-direction: column; text-align: center; }
            .hero h1 { font-size: 1.8rem; }
            .tab-nav { flex-wrap: wrap; }
            .tab-btn { flex: 1 0 45%; font-size: 0.85rem; padding: 0.75rem 0.5rem; }
            .grid { grid-template-columns: 1fr; }
            .detail-overlay { padding: 1rem; }
            .detail-card { padding: 1.5rem; }
        }
    </style>
</head>
<body>

<header class="header">
    <div class="logo">BunkBed<span>World</span></div>
    <div class="tagline">🛏️ Built for sleep. Designed for life.</div>
</header>

<section class="hero">
    <h1>Your Home, <span>Done Right</span></h1>
    <p>From cozy living rooms to bunk beds — find furniture that fits your space, your style, and your budget.</p>
</section>

<nav class="tab-nav" id="tabNav"></nav>

<div class="container" id="mainContent">
    <div class="loading">Loading products...</div>
</div>

<!-- Detail Overlay -->
<div class="detail-overlay" id="detailOverlay" onclick="closeDetail(event)">
    <div class="detail-card" onclick="event.stopPropagation()">
        <button class="detail-close" onclick="closeDetail()">✕</button>
        <div id="detailContent"></div>
    </div>
</div>

<footer class="footer">
    <p><strong>BunkBedWorld</strong> — founded in Chicago, built for your home.</p>
    <p style="margin-top:0.4rem; font-size:0.85rem;">📞 (555) 123-BUNK &nbsp;·&nbsp; ✉️ hello@bunkbedworld.com</p>
    <p style="margin-top:0.4rem; font-size:0.75rem;">© 2026 BunkBedWorld. All rights reserved.</p>
</footer>

<script>
// ==== ALL PRODUCT DATA ====
var PRODUCTS = ''' + escaped_json + ''';

// ==== TAB STRUCTURE ====
var TABS = ''' + tab_json + ''';

// Current state
var currentTab = "Living Room";
var currentSubcat = null;

function init() {
    renderTabs();
    switchTab("Living Room");
    checkHash();
    window.addEventListener('hashchange', checkHash);
}

function renderTabs() {
    var nav = document.getElementById('tabNav');
    nav.innerHTML = '';
    TABS.forEach(function(tab) {
        var total = 0;
        tab.categories.forEach(function(c) { total += c.count; });
        var btn = document.createElement('button');
        btn.className = 'tab-btn';
        btn.setAttribute('onclick', 'switchTab(\\'' + tab.tab + '\\')');
        btn.innerHTML = tab.tab + ' <span class="count">' + total + '</span>';
        nav.appendChild(btn);
    });
}

function switchTab(name) {
    currentTab = name;
    currentSubcat = null;
    // Update tab buttons
    var btns = document.querySelectorAll('.tab-btn');
    btns.forEach(function(b) {
        b.classList.remove('active');
        if (b.textContent.trim().startsWith(name)) b.classList.add('active');
    });
    renderContent();
}

function renderContent() {
    var container = document.getElementById('mainContent');
    var tab = TABS.find(function(t) { return t.tab === currentTab; });
    if (!tab) { container.innerHTML = '<div class="loading">No products found.</div>'; return; }

    var html = '<div class="subcat-bar">';
    html += '<label for="subcat">Filter:</label>';
    html += '<select id="subcat" class="subcat-select" onchange="filterSubcat(this.value)">';
    html += '<option value="__all__">All ' + currentTab + '</option>';
    tab.categories.forEach(function(c) {
        html += '<option value="' + c.cat_id + '">' + c.name + ' (' + c.count + ')</option>';
    });
    html += '</select></div>';

    // Find which products belong to this tab
    var catNames = tab.categories.map(function(c) { return c.name; });
    var filtered = PRODUCTS.filter(function(p) { return catNames.indexOf(p.category) >= 0; });

    html += '<div class="grid">';
    filtered.forEach(function(p) {
        html += '<a class="card" href="#product-' + p.id + '" onclick="event.preventDefault(); openDetail(\\'' + p.id + '\\'); window.location.hash=\\'product-' + p.id + '\\';">';
        html += '<div class="card-img" style="background-image: url(\\'' + p.image + '\\');"></div>';
        html += '<div class="card-body">';
        html += '<div class="cat-tag">' + p.category + '</div>';
        html += '<h3>' + p.name + '</h3>';
        html += '</div></a>';
    });
    html += '</div>';
    container.innerHTML = html;

    // Restore subcat filter if switching back
    var sel = document.getElementById('subcat');
    if (sel) sel.value = '__all__';
}

function filterSubcat(catId) {
    currentSubcat = catId;
    var container = document.getElementById('mainContent');
    var grid = container.querySelector('.grid');
    if (!grid) return;
    var cards = grid.querySelectorAll('.card');
    cards.forEach(function(c) {
        if (catId === '__all__') { c.style.display = ''; return; }
        // Get category name from the cat-tag div
        var catTag = c.querySelector('.cat-tag');
        if (!catTag) { c.style.display = ''; return; }
        var catName = catTag.textContent.trim();
        // Check if this category's tab entry matches
        var tab = TABS.find(function(t) { return t.tab === currentTab; });
        if (!tab) { c.style.display = ''; return; }
        var catEntry = tab.categories.find(function(ce) { return ce.cat_id === catId; });
        if (!catEntry) { c.style.display = ''; return; }
        c.style.display = (catName === catEntry.name) ? '' : 'none';
    });
}

function openDetail(pid) {
    var product = PRODUCTS.find(function(p) { return p.id === pid; });
    if (!product) return;
    var dc = document.getElementById('detailContent');
    dc.innerHTML = '';
    dc.innerHTML += '<img src="' + product.image + '" alt="' + product.name + '" onerror="this.style.display=\'none\'">';
    dc.innerHTML += '<div class="cat-tag">' + product.category + '</div>';
    dc.innerHTML += '<h2>' + product.name + '</h2>';
    dc.innerHTML += '<div class="price-badge">Call for Price</div><br>';
    dc.innerHTML += '<div style="margin-top:0.5rem;">';
    dc.innerHTML += '<a class="btn-happy" href="' + product.page + '" target="_blank">View on Happy Homes →</a>';
    dc.innerHTML += '</div>';
    document.getElementById('detailOverlay').classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeDetail(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById('detailOverlay').classList.remove('active');
    document.body.style.overflow = '';
    // Remove hash without scrolling
    history.replaceState(null, '', window.location.pathname);
}

function checkHash() {
    var hash = window.location.hash;
    if (hash && hash.startsWith('#product-')) {
        var pid = hash.replace('#product-', '');
        // Find which tab this product belongs to
        var product = PRODUCTS.find(function(p) { return p.id === pid; });
        if (product) {
            // Find the tab for this category
            for (var ti = 0; ti < TABS.length; ti++) {
                var tab = TABS[ti];
                for (var ci = 0; ci < tab.categories.length; ci++) {
                    if (tab.categories[ci].name === product.category) {
                        switchTab(tab.tab);
                        openDetail(pid);
                        return;
                    }
                }
            }
        }
    }
}

// Init on load
window.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>'''

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

# Count total products embedded
total = len(all_products)
total_cats = len(categories)
print(f"Generated index.html with {total} products across {total_cats} categories")