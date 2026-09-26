#!/usr/bin/env python3
"""
BunkBedWorld Complete Scraper & Site Generator v2
==================================================
- Crawls all Happy Homes categories (with pagination support)
- Skips sold-out items
- Extracts all product images for carousel display
- Parses descriptions from "Item:" to "Retail Code:"
- Extracts Retail Code (7XXXX7 format) → vendor price × 1.7 → always ends with 9
- Generates products.json + index.html with carousels
"""
import json, re, sys, os, time
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# ─── Config ─────────────────────────────────────────────────────────────────
BASE = "https://www.happyhomesindustries.com"
JSON_OUT = "products.json"
HTML_OUT = "index.html"
DELAY = 0.5

CATEGORIES = {
    "Stationary Sofa & Loveseats": "/stationary-sofa--loveseats.html",
    "Stationary Sectionals": "/stationary-sectionals.html",
    "Reclining Sofa & Loveseats": "/reclining-sofa--loveseats.html",
    "Reclining Sectionals": "/reclining-sectionals.html",
    "Recliners & Lift Chairs": "/recliners--lift-chairs.html",
    "Occasional Tables": "/occasional-tables.html",
    "TV Stands": "/tv-stands.html",
    "Sleepers & Futons": "/sleepers--futons.html",
    "Accessories": "/accessories.html",
    "Office & Bookcase": "/office--bookcase.html",
    "Beds": "/beds.html",
    "Bedrooms": "/bedrooms.html",
    "Daybeds": "/daybeds.html",
    "Mattresses": "/mattresses.html",
    "Vanities & Mirrors": "/vanities--mirrors.html",
    "Dining Rooms": "/dining-rooms.html",
    "Barstools": "/barstools.html",
    "Bunk Beds": "/bunk-beds.html",
}


def fetch(url):
    """Fetch URL and return HTML string."""
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
    resp = urlopen(req, timeout=30)
    html = resp.read().decode('utf-8', errors='replace')
    resp.close()
    return html


def is_sold_out(html):
    """Check if a product is truly Sold Out (not hidden template text)."""
    # Strategy 1: Check visible text for clear sold-out indicators
    sold_patterns = [
        r'>\s*sold\s*out\s*<',          # >Sold Out< as visible text between tags
        r'>\s*out\s*of\s*stock\s*<',   # >Out of Stock< as visible text
        r'sold[\s-]*out[\s-]*sign',      # "Sold Out" sign/badge text
        r'sold[\s-]*out[\s-]*badge',     # badge
        r'class=["\'][^"\']*\bsold\s*out\b[^"\']*["\']',  # CSS class "sold-out"
    ]
    for pat in sold_patterns:
        if re.search(pat, html, re.IGNORECASE):
            return True

    # Strategy 2: Check if the add-to-cart button says "Sold Out" instead of "Add to Cart"
    has_add = re.search(r'value=["\'](Add\s*to\s*Cart|Buy\s*Now)["\']', html, re.IGNORECASE)
    has_sold = re.search(r'value=["\']Sold\s*Out["\']', html, re.IGNORECASE)
    if has_sold and not has_add:
        return True

    # Strategy 3: Check for price-unavailable div visible (not just present in template)
    # Only flag if both: unavailable div exists AND no main price div exists
    has_price = re.search(r'class=["\']wsite-com-product-price-main["\']', html)
    no_price = re.search(r'id=["\']wsite-com-product-price-unavailable["\']', html)
    if no_price and not has_price:
        # Check if the unavailable div actually says something visible
        avail_area = re.search(r'price-unavailable[^<]*<[^>]*>[^<]*unavailable', html, re.IGNORECASE)
        if avail_area:
            return True

    return False


def get_category_links(cat_name, cat_path):
    """Scrape a category page and all its pagination pages, return product links."""
    all_links = []
    page_num = 1
    seen = set()

    while True:
        url = BASE + cat_path
        # If this isn't the first page, add page parameter
        if page_num > 1:
            if '?' in url:
                url += '&page=' + str(page_num)
            else:
                url += '?page=' + str(page_num)

        print(f"    Page {page_num}...", end=" ", flush=True)

        try:
            html = fetch(url)
        except Exception as e:
            print(f"❌ {e}")
            break

        # Find product links
        links = re.findall(r'href=["\'](/store/p\d+/[^"\']+)["\']', html, re.IGNORECASE)

        new_links = 0
        for link in links:
            if link not in seen:
                seen.add(link)
                all_links.append(link)
                new_links += 1

        if new_links == 0:
            print(f"(no new links) ✅")
            break

        print(f"{new_links} products")

        # Check if there's a next page
        has_next = False
        # Look for pagination: "Next" or ">" link
        for m in re.finditer(r'href=["\'][^"\']*page=(\d+)[^"\']*["\'][^>]*>.*?(?:Next|next|›|»|Next Page)', html, re.IGNORECASE):
            next_page = int(m.group(1))
            if next_page > page_num:
                has_next = True
                break

        # Also check for numbered page list
        if not has_next:
            page_numbers = set()
            for m in re.finditer(r'href=["\'][^"\']*page=(\d+)[^"\']*["\']', html, re.IGNORECASE):
                page_numbers.add(int(m.group(1)))
            if page_num in page_numbers and (page_num + 1) in page_numbers:
                has_next = True

        if not has_next:
            break

        page_num += 1
        time.sleep(DELAY)

    return all_links


def extract_images(html, pid):
    """Extract all product image URLs, converting relative to absolute."""
    images = []
    seen = set()
    pid_str = f"p{pid[1:]}" if pid else ""

    # Find ALL image URLs from <img> tags and background-image styles
    patterns = [
        r'<img[^>]+src=["\'](/uploads/[^"\']+?\.(?:jpe?g|png|webp|gif))',
        r'background(?:-image)?\s*:\s*url\(["\']?(/uploads/[^)"\']+?\.(?:jpe?g|png|webp|gif))',
        r'data-imgurl=["\'](/uploads/[^"\']+?\.(?:jpe?g|png|webp|gif))',
        r'(https://[^"\']*happyhomesindustries[^"\']*?uploads/[^"\']+?\.(?:jpe?g|png|webp|gif))',
    ]

    for pat in patterns:
        for m in re.finditer(pat, html, re.IGNORECASE):
            url = m.group(1)
            # Convert relative to absolute
            if url.startswith('/'):
                url = BASE + url
            # Strip query params
            url = url.split('?')[0]

            # Skip non-product images
            lower = url.lower()
            if any(bad in lower for bad in ['logo', 'icon', 'banner', 'slide', 'favicon', 'screenshot', 'email']):
                continue

            if url not in seen:
                seen.add(url)

    # Filter to product-related images (contain product ID or are in product area)
    filtered = []
    for url in seen:
        if pid_str and pid_str in url:
            filtered.append(url)

    # If no images matched the product ID, use all non-logo images
    if not filtered:
        for url in seen:
            lower = url.lower()
            if any(bad in lower for bad in ['logo', 'icon', 'banner']):
                continue
            filtered.append(url)

    return filtered


def extract_data(product_url, cat_name):
    """Scrape a product page: name, images, description, retail code, pricing."""
    full_url = BASE + product_url

    try:
        html = fetch(full_url)
    except Exception as e:
        return None, str(e)

    # Check sold out
    if is_sold_out(html):
        return None, "SOLD OUT"

    # Product ID
    pid = ""
    m = re.search(r'/store/p(\d+)/', product_url)
    if m:
        pid = "p" + m.group(1)

    # Product name
    name = ""
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
    if m:
        name = m.group(1).strip()
        name = re.sub(r'<[^>]+>', '', name).strip()
    if not name:
        m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        if m:
            name = m.group(1).strip()

    # Images
    images = extract_images(html, pid)

    # Extract text for description parsing
    text = html
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL|re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)

    # Decode HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&rsquo;', "'")

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    clean_text = '\n'.join(lines)

    # Description (Item: to Retail Code:)
    description = ""
    dm = re.search(r'Item\s*Name:.*?(?=Retail Code:)', clean_text, re.IGNORECASE | re.DOTALL)
    if dm:
        dl = [l.strip() for l in dm.group(0).strip().split('\n') if l.strip()]
        description = '\n'.join(dl)

    # Color
    color = ""
    m = re.search(r'Color:\s*(.*?)$', clean_text, re.IGNORECASE | re.MULTILINE)
    if m: color = m.group(1).strip()

    # Material
    material = ""
    m = re.search(r'Material:\s*(.*?)$', clean_text, re.IGNORECASE | re.MULTILINE)
    if m: material = m.group(1).strip()

    # Dimensions
    dimensions = ""
    dm2 = re.search(r'Dimensions:\s*\n((?:(?!Retail Code|Item Name|Color|Material).*\n?)*)', clean_text, re.IGNORECASE | re.MULTILINE)
    if dm2:
        d2 = dm2.group(1).strip()
        if d2: dimensions = d2

    # Retail Code
    retail_raw = ""
    rm = re.search(r'Retail\s*Code:(.*?)(?=$)', clean_text, re.IGNORECASE | re.DOTALL)
    if rm:
        retail_raw = rm.group(1).strip()

    # Parse Retail Code for 7XXXX7 pattern
    cost_prices = []
    for m in re.finditer(r'(?:Queen|King|Full|Twin|CK|Cal\s*King|Twin\s*XL)[^:\n]*:\s*-?\s*(7\d{3}7)', retail_raw, re.IGNORECASE):
        code = m.group(1).strip()
        if len(code) == 5 and code[0] == '7' and code[-1] == '7':
            cost_prices.append(int(code[1:-1]))

    if not cost_prices:
        for m in re.finditer(r'(7\d{3}7)', retail_raw):
            code = m.group(1)
            if len(code) == 5:
                vc = int(code[1:-1])
                if 0 < vc < 9999:
                    cost_prices.append(vc)

    cost_price = min(cost_prices) if cost_prices else 0

    # Sell price: ×1.7, no decimals, always ends with 9
    if cost_price <= 0:
        sell_price = 0
    else:
        raw = cost_price * 1.7
        r = int(round(raw))
        ld = r % 10
        if ld != 9:
            r = r - ld + 9
        if r < 9: r = 9
        sell_price = r

    return {
        "id": pid,
        "name": name,
        "images": images,
        "page": product_url,
        "full_url": full_url,
        "category": cat_name,
        "color": color,
        "material": material,
        "dimensions": dimensions,
        "description": description,
        "retail_codes_raw": retail_raw,
        "cost_price": cost_price,
        "sell_price": sell_price,
    }, None


def generate_html(products):
    """Generate index.html with carousels."""
    # Group by category, sort by price
    cats = {}
    for p in products:
        cat = p["category"]
        if cat not in cats: cats[cat] = []
        cats[cat].append(p)
    for cat in cats:
        cats[cat].sort(key=lambda p: p["sell_price"] if p["sell_price"] > 0 else 999999)

    # Tab structure
    tab_groups = [
        ("Living Room", ["Stationary Sofa & Loveseats", "Stationary Sectionals",
                         "Reclining Sofa & Loveseats", "Reclining Sectionals",
                         "Recliners & Lift Chairs", "Occasional Tables",
                         "TV Stands", "Sleepers & Futons", "Accessories", "Office & Bookcase",
                         "Sofa & Loveseat sets", "Sofas"]),
        ("Bed Room", ["Beds", "Bedrooms", "Daybeds", "Mattresses", "Vanities & Mirrors"]),
        ("Dining Room", ["Dining Rooms", "Barstools", "Barstools & Chairs"]),
        ("Bunk Beds", ["Bunk Beds"]),
    ]

    tabs = []
    cid = 0
    for tname, cnames in tab_groups:
        tc = []
        for cn in cnames:
            if cn in cats:
                cid += 1
                tc.append({"n": cn, "c": len(cats[cn]), "i": "c" + str(cid)})
        if tc:
            tabs.append({"t": tname, "g": tc})

    all_products = []
    for p in products:
        all_products.append({
            "id": p["id"], "name": p["name"], "images": p.get("images", []),
            "page": p["full_url"], "cat": p["category"],
            "desc": p.get("description", ""), "price": p.get("sell_price", 0),
        })

    pjson = json.dumps(all_products, indent=2)
    tjson = json.dumps(tabs, indent=2)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>BunkBedWorld</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,'Inter',sans-serif;background:#f8f7f4;color:#2c2c2c}}
.header{{background:#1a1a2e;color:#fff;padding:1.2rem 2rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap}}
.logo{{font-size:1.6rem;font-weight:800}} .logo span{{color:#e8b86d}}
.hero{{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:3rem 2rem;text-align:center}}
.hero h1{{font-size:2.4rem;font-weight:800;margin-bottom:.5rem}} .hero h1 span{{color:#e8b86d}}
.hero p{{color:#b0b0c0;max-width:600px;margin:0 auto}}

.tab-nav{{display:flex;background:#fff;border-bottom:2px solid #e0ddd8;position:sticky;top:0;z-index:10;overflow-x:auto}}
.tab-btn{{flex:1 0 auto;padding:.9rem 1.2rem;font-weight:600;font-size:.95rem;color:#777;background:none;border:none;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;transition:.2s}}
.tab-btn:hover{{color:#1a1a2e;background:#f8f7f4}}
.tab-btn.active{{color:#1a1a2e;border-bottom-color:#e8b86d}}
.tab-btn .bc{{display:inline-block;background:#e8b86d20;color:#1a1a2e;font-size:.7rem;padding:1px 7px;border-radius:10px;margin-left:5px}}

.container{{max-width:1200px;margin:0 auto;padding:2rem 1.5rem}}

.subcat-bar{{display:flex;align-items:center;gap:10px;margin-bottom:1rem;flex-wrap:wrap}}
.subcat-bar label{{font-weight:600;color:#555}}
.subcat-select{{padding:8px 16px;border:2px solid #ddd;border-radius:8px;font-size:.95rem;font-weight:500;min-width:200px;cursor:pointer}}
.subcat-select:focus{{outline:none;border-color:#e8b86d}}

.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1.5rem}}

.card{{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.06);cursor:pointer;color:inherit;text-decoration:none;transition:transform .25s,box-shadow .25s}}
.card:hover{{transform:translateY(-4px);box-shadow:0 8px 28px rgba(0,0,0,.1)}}
.card-body{{padding:1rem 1.2rem 1.3rem}}
.card-body .ct{{font-size:.72rem;color:#e8b86d;font-weight:600;text-transform:uppercase;margin-bottom:2px}}
.card-body h3{{font-size:.95rem;color:#1a1a2e;line-height:1.3;margin-bottom:2px}}
.card-body .pt{{font-size:1.1rem;font-weight:700;color:#1a1a2e;margin-top:5px}}

.cc{{position:relative;width:100%;height:200px;overflow:hidden;background:#e8e3dc}}
.cs{{position:absolute;top:0;left:0;width:100%;height:100%;background-size:cover;background-position:center;opacity:0;transition:opacity .5s}}
.cs.a{{opacity:1}}
.cb{{position:absolute;top:50%;transform:translateY(-50%);background:rgba(0,0,0,.4);color:#fff;border:none;width:30px;height:60px;cursor:pointer;font-size:1.2rem;z-index:2;transition:.2s}}
.cb:hover{{background:rgba(0,0,0,.7)}} .cb.n{{right:0}}
.cd{{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);display:flex;gap:5px;z-index:2}}
.cd span{{width:8px;height:8px;border-radius:50%;background:rgba(255,255,255,.5);cursor:pointer;transition:.2s}}
.cd span.a{{background:#e8b86d}}

.ov{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.6);z-index:100;justify-content:center;align-items:center;padding:2rem}}
.ov.a{{display:flex}}
.dc{{background:#fff;border-radius:16px;max-width:800px;width:100%;max-height:90vh;overflow-y:auto;padding:2rem;position:relative;box-shadow:0 20px 60px rgba(0,0,0,.3)}}
.dx{{position:absolute;top:1rem;right:1rem;background:none;border:none;font-size:1.5rem;cursor:pointer;color:#888;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center}}
.dx:hover{{background:#f0f0f0}}

.dc-car{{position:relative;width:100%;max-height:400px;overflow:hidden;border-radius:12px;margin-bottom:1.5rem;background:#e8e3dc}}
.dc-car .cs{{height:400px;background-size:contain;background-repeat:no-repeat}}

.dc h2{{font-size:1.4rem;color:#1a1a2e;margin-bottom:.5rem}}
.dc .ct{{font-size:.8rem;color:#e8b86d;font-weight:600;text-transform:uppercase;margin-bottom:.8rem}}
.dc .pb{{display:inline-block;background:#e8b86d20;color:#1a1a2e;font-weight:700;font-size:1.3rem;padding:8px 24px;border-radius:8px;margin:.5rem 0}}
.dc .ds{{margin-top:.8rem;white-space:pre-wrap;font-size:.9rem;color:#555;line-height:1.5}}
.dc .bh{{display:inline-block;background:#1a1a2e;color:#fff;text-decoration:none;padding:10px 20px;border-radius:8px;font-weight:600;margin-top:10px}}
.dc .bh:hover{{background:#2c2c4e}}

.footer{{background:#1a1a2e;color:#888;text-align:center;padding:2rem;margin-top:2rem}}
.footer strong{{color:#e8b86d}}

.ni{{width:100%;height:200px;background:#e8e3dc;display:flex;align-items:center;justify-content:center;color:#aaa}}
.loading{{text-align:center;padding:4rem;color:#888}}

@media(max-width:600px){{
.hero h1{{font-size:1.8rem}}
.tab-btn{{padding:.7rem .8rem;font-size:.85rem}}
.grid{{grid-template-columns:1fr}}
.ov{{padding:1rem}} .dc{{padding:1.5rem}}
}}
</style>
</head>
<body>

<div class="header"><div class="logo">BunkBed<span>World</span></div><div class="tagline">Furniture for every room</div></div>
<div class="hero"><h1>Your Home, <span>Done Right</span></h1><p>From cozy living rooms to bunk beds — find furniture that fits your space and budget.</p></div>
<nav class="tab-nav" id="tabNav"></nav>
<div class="container" id="main"><div class="loading">Loading products...</div></div>
<div class="ov" id="ov" onclick="ca(event)"><div class="dc" onclick="event.stopPropagation()"><button class="dx" onclick="ca()">✕</button><div id="dco"></div></div></div>
<div class="footer"><p><strong>BunkBedWorld</strong> — founded in Chicago, built for your home.</p></div>

<script>
var P={pjson};
var T={tjson};
var ct=null,cn=null,ci={{}};

function esc(s){{if(!s)return'';var d=document.createElement('div');d.appendChild(document.createTextNode(s));return d.innerHTML.replace(/\\n/g,'<br>')}}
function jq(s){{return JSON.stringify(s)}}

function init(){{
  var n=document.getElementById('tabNav');n.innerHTML='';
  T.forEach(function(t){{
    var b=document.createElement('button');
    b.className='tab-btn';
    b.textContent=t.t;
    var sp=document.createElement('span');sp.className='bc';
    var tot=0;t.g.forEach(function(g){{tot+=g.c}});
    sp.textContent=tot;
    b.appendChild(sp);
    b.onclick=function(){{sw(t.t)}};
    n.appendChild(b);
  }});
  sw('Living Room');
}}

function sw(name){{
  ct=name;cn=null;
  document.querySelectorAll('.tab-btn').forEach(function(b){{
    b.classList.toggle('active',b.textContent.trim().startsWith(name));
  }});
  rc();
}}

function rc(){{
  var c=document.getElementById('main');
  var tab=T.find(function(t){{return t.t===ct}});
  if(!tab){{c.innerHTML='<div class="loading">No products found.</div>';return}}

  var h='<div class="subcat-bar"><label>Filter:</label><select class="subcat-select" onchange="fs(this.value)">';
  h+='<option value="__all__">All '+ct+'</option>';
  tab.g.forEach(function(g){{h+='<option value="'+g.i+'">'+g.n+' ('+g.c+')</option>'}});
  h+='</select></div><div class="grid">';

  var cnames=tab.g.map(function(g){{return g.n}});
  var fp=P.filter(function(p){{return cnames.indexOf(p.cat)>=0}});

  fp.forEach(function(p){{
    var imgs=p.images||[];
    h+='<a class="card" onclick="event.preventDefault();od(\\\''+p.id+'\\')">';
    if(imgs.length==0){{h+='<div class="ni">No Image</div>'}}
    else if(imgs.length==1){{h+='<div class="cc"><div class="cs a" style="background-image:url('+jq(imgs[0])+')"></div></div>'}}
    else{{
      h+='<div class="cc" id="c'+p.id+'">';
      imgs.forEach(function(img,i){{h+='<div class="cs'+(i==0?' a':'')+'" style="background-image:url('+jq(img)+')"></div>'}});
      h+='<button class="cb" onclick="event.stopPropagation();cm(\\''+p.id+'\\',-1)">‹</button>';
      h+='<button class="cb n" onclick="event.stopPropagation();cm(\\''+p.id+'\\',1)">›</button>';
      h+='<div class="cd">';
      imgs.forEach(function(img,i){{h+='<span'+(i==0?' class="a"':'')+' onclick="event.stopPropagation();cg(\\''+p.id+'\\','+i+')"></span>'}});
      h+='</div></div>';
    }}
    h+='<div class="card-body"><div class="ct">'+p.cat+'</div><h3>'+esc(p.name)+'</h3><div class="pt">$'+p.price+'</div></div></a>';
  }});
  h+='</div>';
  c.innerHTML=h;

  var sel=c.querySelector('.subcat-select');if(sel)sel.value='__all__';
  for(var k in ci)clearInterval(ci[k]);ci={{}};
  document.querySelectorAll('.cc').forEach(function(cc){{
    var id=cc.id.slice(1);if(id&&!ci[id])ci[id]=setInterval(function(){{cm(id,1)}},4000);
  }});
}}

function cm(id,dir){{
  var cc=document.getElementById('c'+id);if(!cc)return;
  var slides=cc.querySelectorAll('.cs'),dots=cc.querySelectorAll('.cd span');
  var cur=0;slides.forEach(function(s,i){{if(s.classList.contains('a'))cur=i}});
  if(!slides.length)return;
  slides[cur].classList.remove('a');if(dots[cur])dots[cur].classList.remove('a');
  cur=(cur+dir+slides.length)%slides.length;
  slides[cur].classList.add('a');if(dots[cur])dots[cur].classList.add('a');
}}

function cg(id,idx){{
  var cc=document.getElementById('c'+id);if(!cc)return;
  var slides=cc.querySelectorAll('.cs'),dots=cc.querySelectorAll('.cd span');
  slides.forEach(function(s){{s.classList.remove('a')}});
  dots.forEach(function(d){{d.classList.remove('a')}});
  slides[idx].classList.add('a');if(dots[idx])dots[idx].classList.add('a');
}}

function fs(val){{
  var grid=document.querySelector('.grid');if(!grid)return;
  var tab=T.find(function(t){{return t.t===ct}});
  grid.querySelectorAll('.card').forEach(function(c){{
    if(val=='__all__'){{c.style.display='';return}}
    var ct2=c.querySelector('.ct');if(!ct2){{c.style.display='';return}}
    var ce=tab.g.find(function(g){{return g.i===val}});
    if(!ce){{c.style.display='';return}}
    c.style.display=ct2.textContent.trim()===ce.n?'':'none';
  }});
}}

function od(id){{
  var p=P.find(function(x){{return x.id===id}});if(!p)return;
  var d=document.getElementById('dco');d.innerHTML='';
  var imgs=p.images||[];
  if(imgs.length){{
    d.innerHTML+='<div class="dc-car" id="dc-'+id+'">';
    imgs.forEach(function(img,i){{d.innerHTML+='<div class="cs'+(i==0?' a':'')+'" style="background-image:url('+jq(img)+')"></div>'}});
    if(imgs.length>1){{
      d.innerHTML+='<button class="cb" onclick="event.stopPropagation();dm(\\''+id+'\\',-1)">‹</button>';
      d.innerHTML+='<button class="cb n" onclick="event.stopPropagation();dm(\\''+id+'\\',1)">›</button>';
      d.innerHTML+='<div class="cd">';
      imgs.forEach(function(img,i){{d.innerHTML+='<span'+(i==0?' class="a"':'')+' onclick="event.stopPropagation();dg(\\''+id+'\\','+i+')"></span>'}});
      d.innerHTML+='</div>';
    }}
    d.innerHTML+='</div>';
  }}
  d.innerHTML+='<div class="ct">'+p.cat+'</div><h2>'+esc(p.name)+'</h2>';
  if(p.price>0)d.innerHTML+='<div class="pb">$'+p.price+'</div><br>';
  if(p.desc)d.innerHTML+='<div class="ds">'+esc(p.desc)+'</div>';
  d.innerHTML+='<div><a class="bh" href="'+p.page+'" target="_blank">View on Happy Homes →</a></div>';
  document.getElementById('ov').classList.add('a');document.body.style.overflow='hidden';
  if(imgs.length>1){{if(window.dt)clearInterval(window.dt);window.dt=setInterval(function(){{dm(id,1)}},4000)}}
}}

function dm(id,dir){{
  var dc=document.getElementById('dc-'+id);if(!dc)return;
  var slides=dc.querySelectorAll('.cs'),dots=dc.querySelectorAll('.cd span');
  var cur=0;slides.forEach(function(s,i){{if(s.classList.contains('a'))cur=i}});
  if(!slides.length)return;
  slides[cur].classList.remove('a');if(dots[cur])dots[cur].classList.remove('a');
  cur=(cur+dir+slides.length)%slides.length;
  slides[cur].classList.add('a');if(dots[cur])dots[cur].classList.add('a');
}}

function dg(id,idx){{
  var dc=document.getElementById('dc-'+id);if(!dc)return;
  var slides=dc.querySelectorAll('.cs'),dots=dc.querySelectorAll('.cd span');
  slides.forEach(function(s){{s.classList.remove('a')}});
  dots.forEach(function(d){{d.classList.remove('a')}});
  slides[idx].classList.add('a');if(dots[idx])dots[idx].classList.add('a');
}}

function ca(e){{if(e&&e.target!==e.currentTarget)return;
  document.getElementById('ov').classList.remove('a');document.body.style.overflow='';
  if(window.dt)clearInterval(window.dt);
}}

window.addEventListener('DOMContentLoaded',init);
</script>
</body>
</html>'''


def main():
    print("=" * 60)
    print("BunkBedWorld v2 — Complete Rebuild")
    print("=" * 60)

    # Step 1: Crawl all categories with pagination
    print("\n📋 Step 1: Crawling categories (with pagination)...")
    all_urls = []
    url_cat = {}

    for cat_name, cat_path in CATEGORIES.items():
        print(f"  {cat_name}:")
        links = get_category_links(cat_name, cat_path)
        for link in links:
            if link not in url_cat:
                url_cat[link] = cat_name
                all_urls.append(link)
        time.sleep(DELAY)

    print(f"\n  Total unique product URLs: {len(all_urls)}")

    # Step 2: Scrape each product
    print("\n🔍 Step 2: Scraping products...")
    products = []
    skipped = 0
    errors = 0

    for i, url in enumerate(all_urls):
        cat = url_cat[url]
        print(f"  [{i+1}/{len(all_urls)}] ", end="", flush=True)

        data, err = extract_data(url, cat)
        if err == "SOLD OUT":
            print("⏭️ Sold out")
            skipped += 1
        elif err:
            print(f"⚠️ {err}")
            errors += 1
        else:
            print(f"✅ ${data['sell_price']} ({len(data['images'])} img, {data['id']})")
            products.append(data)

        time.sleep(DELAY)

    print(f"\n  Results: {len(products)} scraped, {skipped} sold out, {errors} errors")

    # ── Step 2b: Merge Nova Furniture products ──
    print("\n🔀 Merging Nova Furniture products...")
    nova_path = "nova_backup.json"
    if os.path.exists(nova_path):
        with open(nova_path) as f:
            nova = json.load(f)
        for np in nova:
            # Convert Nova format to match HH format
            np_data = {
                "id": np["id"],
                "name": np.get("name", ""),
                "images": [np["image"]] if np.get("image") else [],
                "page": np.get("page", ""),
                "full_url": np.get("page", ""),
                "category": np.get("category", "Accessories"),
                "color": np.get("color", ""),
                "material": np.get("material", ""),
                "dimensions": np.get("dimensions", ""),
                "description": np.get("description", ""),
                "retail_codes_raw": "",
                "cost_price": np.get("cost_price", 0),
                "sell_price": np.get("sell_price", 0),
            }
            products.append(np_data)
        print(f"  Merged {len(nova)} Nova Furniture products")

    # ── Step 2c: Merge BunkBedWorld special items ──
    print("\n🔀 Merging BunkBedWorld special items...")
    bbw_path = "bbw_backup.json"
    if os.path.exists(bbw_path):
        with open(bbw_path) as f:
            bbw = json.load(f)
        for bp in bbw:
            bp_data = {
                "id": bp["id"],
                "name": bp.get("name", ""),
                "images": [bp["image"]] if bp.get("image") else [],
                "page": bp.get("page", ""),
                "full_url": bp.get("page", ""),
                "category": bp.get("category", "Accessories"),
                "color": bp.get("color", ""),
                "material": bp.get("material", ""),
                "dimensions": bp.get("dimensions", ""),
                "description": bp.get("description", ""),
                "retail_codes_raw": "",
                "cost_price": bp.get("cost_price", 0),
                "sell_price": bp.get("sell_price", 0),
            }
            products.append(bp_data)
        print(f"  Merged {len(bbw)} BBW special items")

    # ── Step 2d: Override special BBW items that must NEVER change ──
    print("\n🔒 Applying BBW special item overrides...")
    # These items are rebranded BunkBedWorld items — their prices are fixed
    special_overrides = {
        "p1838": {
            "name": "1.5\" BOARD",
            "cost_price": 50,
            "sell_price": 50,
            "description": "Available in: Twin ($50), Full ($60), Queen ($70), King ($120)",
        },
        "p790": {
            "name": "4.5\" Inch Low Profile Foundation",
            "cost_price": 70,
            "sell_price": 70,
            "description": "Available in: Twin ($70), Full ($80), Queen ($90), King ($150)",
        },
        "p548": {
            "name": "9\" Foundation",
            "cost_price": 70,
            "sell_price": 70,
            "description": "Available in: Twin ($70), Full ($80), Queen ($90), King ($150)",
        },
        "b0001": {
            "name": "6\" Elsa Innerspring Queen Mattress",
            "cost_price": 125,
            "sell_price": 125,
        },
    }
    for pid, over in special_overrides.items():
        for p in products:
            if p["id"] == pid:
                p["name"] = over["name"]
                p["cost_price"] = over["cost_price"]
                p["sell_price"] = over["sell_price"]
                if "description" in over:
                    p["description"] = over["description"]
                print(f"  {pid}: {over['name']} — fixed at ${over['sell_price']}")
                break

    # Step 3: Save products.json
    print("\n💾 Saving products.json...")
    cat_order = [
        "Stationary Sofa & Loveseats", "Stationary Sectionals",
        "Reclining Sofa & Loveseats", "Reclining Sectionals",
        "Recliners & Lift Chairs", "Occasional Tables",
        "TV Stands", "Sleepers & Futons", "Accessories", "Office & Bookcase",
        "Sofa & Loveseat sets", "Sofas",
        "Beds", "Bedrooms", "Daybeds", "Mattresses", "Vanities & Mirrors",
        "Dining Rooms", "Barstools", "Barstools & Chairs",
        "Bunk Beds",
    ]
    cat_index = {c: i for i, c in enumerate(cat_order)}
    products.sort(key=lambda p: (
        cat_index.get(p["category"], 999),
        p["sell_price"] if p["sell_price"] > 0 else 999999
    ))
    with open(JSON_OUT, 'w') as f:
        json.dump(products, f, indent=2)
    print(f"  Saved {len(products)} products")

    # Step 4: Generate HTML
    print("\n🎨 Generating index.html...")
    html = generate_html(products)
    with open(HTML_OUT, 'w') as f:
        f.write(html)
    print(f"  Generated {len(html):,} bytes")

    print("\n✅ Complete!")


if __name__ == '__main__':
    main()