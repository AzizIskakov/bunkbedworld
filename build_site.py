#!/usr/bin/env python3
"""Build BunkBedWorld — fresh Happy Homes scrape + Nova BBW merge."""
import json, subprocess, re

# Load fresh scrape (or backup if scrape hasn't finished)
HH_FILE = 'happy_homes_inventory.json'  # scraper tracking file
try:
    with open(HH_FILE) as f:
        hh_tracking = json.load(f)
except:
    hh_tracking = {}

# Try loading fresh products.json from scraper
try:
    with open('products.json') as f:
        fresh_raw = json.load(f)
    print(f"Fresh scrape: {len(fresh_raw)} products")
    
    # Filter fresh HH products (not sold out, with prices)
    hh_products = []
    for p in fresh_raw:
        if p.get('sold_out'):
            continue
        # Get price - check image file naming or cost price
        price = p.get('cost_price', 0)
        if not price:
            # Try to extract from retail codes
            page_text = p.get('description', '') + p.get('name', '')
            m = re.search(r'7(\d{3,4})7', page_text)
            if m:
                price = int(m.group(1))
        if price:
            p['price'] = price
            hh_products.append(p)
    
    print(f"  Valid HH products: {len(hh_products)}")
except FileNotFoundError:
    print("products.json not found yet (scraper may still be running)")
    hh_products = []

# Load Nova + BBW from backup
with open('products.json.fresh.bak') as f:
    backup_raw = json.load(f)

nova_products = []
bbw_products = []
other = []
for p in backup_raw:
    page = p.get('page', '')
    if 'novafurniture.us' in page:
        nova_products.append(p)
    elif p['id'] in ('b0001', 'b0004') or p.get('page','') == '':
        bbw_products.append(p)
    elif 'generationtrade.com' in page:
        bbw_products.append(p)
    elif 'bunkbedworld' in p.get('name','').lower() or p.get('vendor') == 'BunkBedWorld':
        bbw_products.append(p)
    elif p.get('vendor') and p.get('vendor') != 'Happy Homes':
        nova_products.append(p)

print(f"Backup: {len(nova_products)} Nova, {len(bbw_products)} BBW specials")
print(f"  Total available: {len(hh_products) + len(nova_products) + len(bbw_products)}")

# Merge all products
all_products = hh_products + nova_products + bbw_products

# If we couldn't get fresh HH data, use backup
if not hh_products:
    print("FALLBACK: Using all backup data")
    all_products = []
    for p in backup_raw:
        pid = p.get('id','')
        if pid in ('p1838','p790','p548','b0001'):
            # BBW specials - their prices are locked
            pass
        p['price'] = p.get('price', 0) or p.get('sell_price', 0) or p.get('cost_price', 0)
        all_products.append(p)
    
    # Filter sold out
    all_products = [p for p in all_products if not p.get('sold_out')]

# Ensure every product has: id, name, images[], cat, price, desc
def normalize(p):
    return {
        "id": p.get("id", ""),
        "name": p.get("name", ""),
        "images": p.get("images", [p.get("image", "")] if p.get("image") else []),
        "cat": p.get("cat", "") or p.get("category", ""),
        "price": p.get("price", 0) or p.get("sell_price", 0),
        "desc": p.get("desc", "") or p.get("description", ""),
        "page": p.get("page", ""),
    }

all_products = [normalize(p) for p in all_products if not p.get('sold_out') and p.get('price', 0) > 0]

# BBW special items - LOCKED prices
bbw_locked = {
    'p1838': 50, 'p790': 70, 'p548': 70, 'b0001': 125,
}
for p in all_products:
    if p['id'] in bbw_locked:
        p['price'] = bbw_locked[p['id']]
        print(f"  Locked BBW price: {p['id']} = ${p['price']}")

print(f"\nTotal products: {len(all_products)}")

# Tab definitions
TAB_DEFS = [
    ("Living Room", ["Stationary Sofa & Loveseats", "Stationary Sectionals",
                     "Reclining Sofa & Loveseats", "Reclining Sectionals",
                     "Recliners & Lift Chairs", "Occasional Tables",
                     "TV Stands", "Sleepers & Futons", "Accessories",
                     "Office & Bookcase", "Sofas", "Sofa & Loveseat sets"]),
    ("Bedroom", ["Beds", "Bedrooms", "Daybeds", "Mattresses", "Vanities & Mirrors"]),
    ("Dining Room", ["Dining Rooms", "Barstools & Chairs", "Barstools"]),
    ("Bunk Beds", ["Bunk Beds"]),
]

def esc(s):
    if not s: return ''
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;").replace("\n", "<br>"))

# Build tabs JSON
tabs_json = []
for tname, cnames in TAB_DEFS:
    items = []
    for cn in cnames:
        cnt = sum(1 for p in all_products if p["cat"] == cn)
        if cnt > 0:
            items.append({"n": cn, "c": cnt})
    if items:
        tabs_json.append({"t": tname, "g": items})

# Sort by price within category
cats = {}
for p in all_products:
    cats.setdefault(p["cat"], []).append(p)
for cat in cats:
    cats[cat].sort(key=lambda x: x["price"])

products_flat = []
for cat in sorted(cats.keys()):
    products_flat.extend(cats[cat])

def render_cards(prods):
    h = ""
    for p in prods:
        img = p["images"][0] if p["images"] else ""
        h += '<div class="card" data-id="' + p["id"] + '">'
        h += '<div class="ci" style="background-image:url(' + img + ')"></div>'
        h += '<div class="cb"><div class="ct">' + esc(p["cat"]) + '</div>'
        h += '<h3>' + esc(p["name"]) + '</h3>'
        h += '<span class="pr">$' + str(p["price"]) + '</span></div></div>'
    return h

SSR_PRODS = [p for p in products_flat if p["cat"] in TAB_DEFS[0][1]]
SSR_HTML = render_cards(SSR_PRODS)

# Tab buttons with dropdowns
tabs_html = ""
first = True
for tname, cnames in TAB_DEFS:
    tot = sum(1 for p in all_products if p["cat"] in cnames)
    act = " active" if first else ""
    first = False
    tabs_html += '<div class="tb' + act + '" data-tab="' + tname + '">'
    tabs_html += tname + '<span class="c">' + str(tot) + '</span><span class="ar">&#9662;</span>'
    tabs_html += '<div class="drop">'
    tabs_html += '<div class="di active" data-cat="all">All<span class="c">' + str(tot) + '</span></div>'
    for cn in cnames:
        c_cnt = sum(1 for p in all_products if p["cat"] == cn)
        if c_cnt > 0:
            tabs_html += '<div class="di" data-cat="' + cn.replace('"', "&quot;") + '">'
            tabs_html += cn + '<span class="c">' + str(c_cnt) + '</span></div>'
    tabs_html += '</div></div>'

# CSS
CSS = """*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:#f8f7f4;color:#2c2c2c}
.hdr{background:#1a1a2e;color:#fff;padding:1rem 2rem}.hdr h1{font-size:1.4rem;font-weight:800}.hdr h1 span{color:#e8b86d}.hdr p{font-size:.8rem;color:#999;margin-top:2px}
.nav{display:flex;background:#fff;border-bottom:2px solid #e0ddd8;position:sticky;top:0;z-index:10;overflow-x:auto}
.tb{position:relative;flex:1 0 auto;padding:.9rem 1.2rem;font-weight:600;font-size:.9rem;color:#777;background:none;border:none;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;transition:.2s;display:flex;align-items:center;justify-content:center}
.tb:hover{color:#1a1a2e;background:#f8f7f4}.tb.active{color:#1a1a2e;border-bottom-color:#e8b86d}
.tb .c{display:inline-block;background:#e8b86d20;color:#1a1a2e;font-size:.7rem;padding:1px 7px;border-radius:10px;margin-left:5px}
.tb .ar{margin-left:4px;font-size:.65rem;transition:transform .2s}.tb.active .ar{transform:rotate(180deg)}
.drop{display:none;position:absolute;top:100%;left:0;background:#fff;border:1px solid #e0ddd8;border-radius:0 0 10px 10px;box-shadow:0 8px 28px rgba(0,0,0,.12);min-width:200px;z-index:50;overflow:hidden}
.drop.a{display:block}
.di{padding:.7rem 1.2rem;font-size:.85rem;color:#555;font-weight:500;cursor:pointer;white-space:nowrap;transition:.15s;border-bottom:1px solid #f0eee8;display:flex;align-items:center;justify-content:space-between}
.di:last-child{border-bottom:none}.di:hover{background:#e8b86d20;color:#1a1a2e}.di.active{background:#e8b86d20;color:#1a1a2e;font-weight:700}
.di .c{font-size:.7rem;background:#f0eee8;padding:1px 7px}.di.active .c{background:#e8b86d;color:#1a1a2e}
.ctr{max-width:1200px;margin:0 auto;padding:2rem 1.5rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1.5rem}
.card{background:#fff;border-radius:12px;overflow:hidden;cursor:pointer;box-shadow:0 2px 12px rgba(0,0,0,.06);transition:transform .25s,box-shadow .25s}
.card:hover{transform:translateY(-4px);box-shadow:0 8px 28px rgba(0,0,0,.1)}
.ci{width:100%;height:200px;background-size:cover;background-position:center;background-color:#e8e3dc}
.cb{padding:1rem 1.2rem 1.3rem}.cb .ct{font-size:.72rem;color:#e8b86d;font-weight:600;text-transform:uppercase;margin-bottom:3px}
.cb h3{font-size:.95rem;color:#1a1a2e;line-height:1.3;margin-bottom:2px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.cb .pr{font-size:1.1rem;font-weight:700;color:#1a1a2e}
.ov{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.6);z-index:100;justify-content:center;align-items:center;padding:2rem}.ov.a{display:flex}
.dc{background:#fff;border-radius:16px;max-width:800px;width:100%;max-height:90vh;overflow-y:auto;padding:2rem;position:relative;box-shadow:0 20px 60px rgba(0,0,0,.3)}
.dx{position:absolute;top:1rem;right:1rem;background:none;border:none;font-size:1.5rem;cursor:pointer;color:#888;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;z-index:5}
.dx:hover{background:#f0f0f0}
.dci{width:100%;height:300px;background-size:contain;background-position:center;background-repeat:no-repeat;background-color:#e8e3dc;border-radius:12px;margin-bottom:.5rem}
.car{display:flex;gap:6px;justify-content:center;margin-bottom:1rem;flex-wrap:wrap}
.car span{width:10px;height:10px;border-radius:50%;background:#ddd;cursor:pointer;transition:.2s}.car span.a{background:#e8b86d}
.dc .ct{font-size:.8rem;color:#e8b86d;font-weight:600;text-transform:uppercase;margin-bottom:.5rem;padding:0 60px 0 0}
.dc h2{font-size:1.4rem;color:#1a1a2e;margin-bottom:.5rem;padding:0 60px 0 0}
.dc .pb{display:inline-block;background:#e8b86d20;color:#1a1a2e;font-weight:700;font-size:1.3rem;padding:8px 24px;border-radius:8px;margin:.5rem 0}
.dc .ds{margin-top:.8rem;white-space:pre-wrap;font-size:.9rem;color:#555;line-height:1.5}
.ftr{background:#1a1a2e;color:#888;text-align:center;padding:2rem;margin-top:2rem;font-size:.85rem}.ftr strong{color:#e8b86d}
.ld{text-align:center;padding:4rem;color:#aaa;font-size:1.1rem}
@media(max-width:600px){.hdr{padding:.8rem 1rem}.tb{padding:.7rem .8rem;font-size:.85rem}.grid{grid-template-columns:1fr}.ov{padding:1rem}.dc{padding:1.5rem}.dci{height:220px}.drop{min-width:160px}}
"""

TABS_JSON_STR = json.dumps(tabs_json)
JS = """var T=""" + TABS_JSON_STR + """;
var P=[],ct='Living Room',sc='all';

function esc(s){if(!s)return'';var d=document.createElement('div');d.appendChild(document.createTextNode(s));return d.innerHTML.replace(/\\n/g,'<br>')}

// Card click — set immediately
(function(){var m=document.getElementById('m');if(m)m.onclick=function(e){var el=e.target.closest('.card');if(el&&el.dataset.id){e.preventDefault();od(el.dataset.id);return false;}};})();

// Tab init — called after data loads
function init(){
  var tabs=document.querySelectorAll('.tb');
  for(var i=0;i<tabs.length;i++){(function(b){
    b.onclick=function(e){e.stopPropagation();var n=b.dataset.tab;for(var j=0;j<tabs.length;j++){if(tabs[j]!==b){var od=tabs[j].querySelector('.drop');if(od)od.classList.remove('a');}tabs[j].classList.toggle('active',tabs[j].dataset.tab===n);}var dd=b.querySelector('.drop');if(dd)dd.classList.toggle('a');ct=n;};
    var dis=b.querySelectorAll('.di');
    for(var k=0;k<dis.length;k++){(function(d){d.onclick=function(e){e.stopPropagation();sc=d.dataset.cat;var dd=b.querySelector('.drop');if(dd)dd.classList.remove('a');for(var m=0;m<dis.length;m++)dis[m].classList.remove('active');d.classList.add('active');if(P.length)rc();};})(dis[k]);}
  })(tabs[i]);}
  document.addEventListener('click',function(){var ads=document.querySelectorAll('.tb .drop');for(var j=0;j<ads.length;j++)ads[j].classList.remove('a');});
  if(P.length)rc();
}

fetch('/data.json').then(function(r){return r.json()}).then(function(d){P=d;init();}).catch(function(e){console.log('fetch',e);setTimeout(function(){if(!P.length){try{P=JSON.parse(document.getElementById('pd').textContent);}catch(e2){}init();}},100);});

function rc(){
  if(!P.length){setTimeout(rc,50);return;}
  var c=document.getElementById('m');
  var tab=T.find(function(t){return t.t===ct});if(!tab){c.innerHTML='<div class="ld">No products.</div>';return;}
  var fp=sc==='all'?P.filter(function(p){return tab.g.some(function(g){return g.n===p.cat})}):P.filter(function(p){return p.cat===sc});
  var h='';
  for(var i=0;i<fp.length;i++){var p=fp[i];h+='<div class="card" data-id="'+p.id+'">';h+='<div class="ci" style="background-image:url('+p.images[0]+')"></div>';h+='<div class="cb"><div class="ct">'+esc(p.cat)+'</div><h3>'+esc(p.name)+'</h3><span class="pr">$'+p.price+'</span></div></div>';}
  c.innerHTML=h||'<div class="ld">No products in this category.</div>';
}

function od(id){
  if(!P.length){document.getElementById('dco').innerHTML='<div class="ld">Loading...</div>';document.getElementById('ov').classList.add('a');document.body.style.overflow='hidden';setTimeout(function(){if(P.length)od(id);else ca();},300);return;}
  var p=P.find(function(x){return x.id===id});if(!p){document.getElementById('dco').innerHTML='<div class="ld">Not found.</div>';return;}
  var h='<div class="dci" id="dci" style="background-image:url('+p.images[0]+')"></div>';
  if(p.images.length>1){h+='<div class="car" id="car">';for(var i=0;i<p.images.length;i++)h+='<span'+(i===0?' class="a"':'')+' data-n="'+i+'"></span>';h+='</div>';}
  h+='<div class="ct">'+esc(p.cat)+'</div><h2>'+esc(p.name)+'</h2>';
  if(p.price>0)h+='<div class="pb">$'+p.price+'</div><br>';
  if(p.desc)h+='<div class="ds">'+esc(p.desc)+'</div>';
  document.getElementById('dco').innerHTML=h;
  var car=document.getElementById('car');if(car){car.onclick=function(e){var sp=e.target.closest('span');if(sp&&sp.dataset.n){var n=parseInt(sp.dataset.n);document.getElementById('dci').style.backgroundImage='url('+p.images[n]+')';var sps=car.querySelectorAll('span');for(var i=0;i<sps.length;i++)sps[i].classList.toggle('a',i===n);}};}
  document.getElementById('ov').classList.add('a');document.body.style.overflow='hidden';
}

function ca(e){if(e&&e.target!==e.currentTarget)return;document.getElementById('ov').classList.remove('a');document.body.style.overflow='';}
"""

# Write data.json
data_json = json.dumps(products_flat, indent=2)
with open('data.json', 'w') as f:
    f.write(data_json)

# Inline data fallback
DATA_INLINE = '<script id="pd" type="application/json">' + json.dumps(products_flat) + '</script>'

# Build HTML
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>BunkBedWorld</title>
<style>""" + CSS + """</style>
</head>
<body>
<div class="hdr"><h1>BunkBed<span>World</span></h1><p>Furniture for every room</p></div>
<nav class="nav">""" + tabs_html + """</nav>
""" + DATA_INLINE + """
<div class="ctr" id="m"><div class="grid">""" + SSR_HTML + """</div></div>
<div class="ov" id="ov" onclick="ca(event)"><div class="dc" onclick="event.stopPropagation()"><button class="dx" onclick="ca()">&#10005;</button><div id="dco"></div></div></div>
<div class="ftr"><p><strong>BunkBedWorld</strong> — Chicago</p></div>
<script>""" + JS + """</script>
</body>
</html>"""

with open('index.html', 'w') as f:
    f.write(HTML)

print(f"\nBuilt: index.html ({len(HTML)//1024} KB), data.json ({len(data_json)//1024} KB)")

r = subprocess.run(['node', '-e', f'try{{new Function({repr(JS)});console.log("JS: OK")}}catch(e){{console.log("JS:",e.message)}}'],
                   capture_output=True, text=True, timeout=5)
print(r.stdout.strip())

total_imgs = sum(len(p["images"]) for p in products_flat)
multi = sum(1 for p in products_flat if len(p["images"])>1)
desc = sum(1 for p in products_flat if p["desc"])
print(f"Total: {len(products_flat)} products, {total_imgs} images ({multi} multi-image), {desc} with desc")
for tname, cnames in TAB_DEFS:
    tot = sum(1 for p in all_products if p["cat"] in cnames)
    print(f"  {tname}: {tot}")
print(f"SSR: {len(SSR_PRODS)} cards ({len(SSR_HTML)//1024} KB)")