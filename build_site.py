#!/usr/bin/env python3
"""Build BunkBedWorld v2 — clean design from scratch."""
import json

with open('products.json.bak') as f:
    raw = json.load(f)

# Filter out sold-out items
raw = [p for p in raw if not p.get('sold_out') and 'sell_price' in p]

# Map old categories to new menu tabs
TAB_DEFS = [
    ("Living Room", ["Stationary Sofa & Loveseats", "Stationary Sectionals",
                     "Reclining Sofa & Loveseats", "Reclining Sectionals",
                     "Recliners & Lift Chairs", "Occasional Tables",
                     "TV Stands", "Sleepers & Futons", "Accessories",
                     "Office & Bookcase"]),
    ("Bedroom", ["Beds", "Bedrooms", "Daybeds", "Mattresses",
                  "Vanities & Mirrors"]),
    ("Dining Room", ["Dining Rooms", "Barstools"]),
    ("Bunk Beds", ["Bunk Beds"]),
]

# Build tabs JSON (used by JS for switching)
tabs_json = []
for tname, cnames in TAB_DEFS:
    items = []
    for cn in cnames:
        items.append({"n": cn, "c": sum(1 for p in raw if p["category"] == cn)})
    if items:
        tabs_json.append({"t": tname, "g": items})

# Convert data to simplified format
products = []
for p in raw:
    products.append({
        "id": p["id"],
        "n": p["name"],
        "img": p["image"],
        "cat": p["category"],
        "p": p["sell_price"],
        "d": p.get("description", ""),
    })

# Sort by price within each category
cats = {}
for p in products:
    cat = p["cat"]
    if cat not in cats:
        cats[cat] = []
    cats[cat].append(p)
for cat in cats:
    cats[cat].sort(key=lambda x: x["p"])

products_sorted = []
for p in raw:  # preserve order but sort each category
    pass
products_flat = []
for cat in sorted(cats.keys()):
    products_flat.extend(cats[cat])

# SSR: pre-render Living Room grid
def esc(s):
    if not s: return ''
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;").replace("\n", "<br>"))

def render_cards(prods):
    h = ""
    for p in prods:
        h += '<div class="card" onclick="od(\'' + p["id"] + '\')">'
        h += '<div class="ci" style="background-image:url(' + p["img"] + ')"></div>'
        h += '<div class="cb"><div class="ct">' + esc(p["cat"]) + '</div>'
        h += '<h3>' + esc(p["n"]) + '</h3>'
        h += '<span class="pr">$' + str(p["p"]) + '</span></div></div>'
    return h

SSR_CATS = TAB_DEFS[0][1]
SSR_PRODS = [p for p in products_flat if p["cat"] in SSR_CATS]
SSR_PRODS = [p for p in products_flat if p["cat"] in SSR_CATS]
SSR_HTML = render_cards([p for p in products_flat if p["cat"] in SSR_CATS])

# Tab buttons HTML
tabs_html = ""
first = True
for tname, _ in TAB_DEFS:
    cnt = sum(len(cats.get(cn, [])) for cn in _ if cn in cats)
    act = ' active' if first else ''
    tabs_html += '<button class="tb' + act + '" data-tab="' + tname + '">' + tname + '<span class="c">' + str(cnt) + '</span></button>\n'
    first = False

# CSS
CSS = """*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:#f8f7f4;color:#2c2c2c}
.hdr{background:#1a1a2e;color:#fff;padding:1rem 2rem}
.hdr h1{font-size:1.4rem;font-weight:800}
.hdr h1 span{color:#e8b86d}
.hdr p{font-size:.8rem;color:#999;margin-top:2px}
.nav{display:flex;background:#fff;border-bottom:2px solid #e0ddd8;position:sticky;top:0;z-index:10;overflow-x:auto}
.tb{flex:1 0 auto;padding:.9rem 1.2rem;font-weight:600;font-size:.9rem;color:#777;background:none;border:none;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;transition:.2s}
.tb:hover{color:#1a1a2e;background:#f8f7f4}
.tb.active{color:#1a1a2e;border-bottom-color:#e8b86d}
.tb .c{display:inline-block;background:#e8b86d20;color:#1a1a2e;font-size:.7rem;padding:1px 7px;border-radius:10px;margin-left:5px}
.ctr{max-width:1200px;margin:0 auto;padding:2rem 1.5rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1.5rem}
.card{background:#fff;border-radius:12px;overflow:hidden;cursor:pointer;box-shadow:0 2px 12px rgba(0,0,0,.06);transition:transform .25s,box-shadow .25s}
.card:hover{transform:translateY(-4px);box-shadow:0 8px 28px rgba(0,0,0,.1)}
.ci{width:100%;height:200px;background-size:cover;background-position:center;background-color:#e8e3dc}
.cb{padding:1rem 1.2rem 1.3rem}
.cb .ct{font-size:.72rem;color:#e8b86d;font-weight:600;text-transform:uppercase;margin-bottom:2px}
.cb h3{font-size:.95rem;color:#1a1a2e;line-height:1.3;margin-bottom:2px}
.cb .pr{font-size:1.1rem;font-weight:700;color:#1a1a2e}
.ov{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.6);z-index:100;justify-content:center;align-items:center;padding:2rem}
.ov.a{display:flex}
.dc{background:#fff;border-radius:16px;max-width:800px;width:100%;max-height:90vh;overflow-y:auto;padding:2rem;position:relative;box-shadow:0 20px 60px rgba(0,0,0,.3)}
.dx{position:absolute;top:1rem;right:1rem;background:none;border:none;font-size:1.5rem;cursor:pointer;color:#888;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center}
.dx:hover{background:#f0f0f0}
.dci{width:100%;height:300px;background-size:contain;background-position:center;background-repeat:no-repeat;background-color:#e8e3dc;border-radius:12px;margin-bottom:1.5rem}
.dc .ct{font-size:.8rem;color:#e8b86d;font-weight:600;text-transform:uppercase;margin-bottom:.5rem}
.dc h2{font-size:1.4rem;color:#1a1a2e;margin-bottom:.5rem}
.dc .pb{display:inline-block;background:#e8b86d20;color:#1a1a2e;font-weight:700;font-size:1.3rem;padding:8px 24px;border-radius:8px;margin:.5rem 0}
.dc .ds{margin-top:1rem;white-space:pre-wrap;font-size:.9rem;color:#555;line-height:1.5}
.ftr{background:#1a1a2e;color:#888;text-align:center;padding:2rem;margin-top:2rem;font-size:.85rem}
.ftr strong{color:#e8b86d}
.ld{text-align:center;padding:4rem;color:#888}
@media(max-width:600px){.hdr{padding:.8rem 1rem}.tb{padding:.7rem .8rem;font-size:.85rem}.grid{grid-template-columns:1fr}.ov{padding:1rem}.dc{padding:1.5rem}.dci{height:220px}}
"""

# JavaScript
JS = """var P=[],T=TAB_JSON,ct='Living Room';
function esc(s){if(!s)return'';var d=document.createElement('div');d.appendChild(document.createTextNode(s));return d.innerHTML.replace(/\\n/g,'<br>')}
function init(){
  document.querySelectorAll('.tb').forEach(function(b){
    b.onclick=function(){
      var n=b.dataset.tab;
      document.querySelectorAll('.tb').forEach(function(x){x.classList.toggle('active',x.dataset.tab===n)});
      ct=n;if(P.length)rc();else setTimeout(rc,99);
    };
  });
  if(P.length){rc();}
}
fetch('/data.json').then(function(r){return r.json()}).then(function(d){P=d;init();}).catch(function(){});
function rc(){
  if(!P.length){setTimeout(rc,99);return;}
  var c=document.getElementById('m');
  var tab=T.find(function(t){return t.t===ct});
  if(!tab){c.innerHTML='<div class=\\"ld\\">No products.</div>';return}
  var fp=P.filter(function(p){return tab.g.some(function(g){return g.n===p.cat})});
  var h='';
  fp.forEach(function(p){
    h+='<div class=\\"card\\" onclick=\\"od(\\'"+p.id+"\\')\\">';
    h+='<div class=\\"ci\\" style=\\"background-image:url('+p.img+')\\"></div>';
    h+='<div class=\\"cb\\"><div class=\\"ct\\">'+esc(p.cat)+'</div><h3>'+esc(p.n)+'</h3><span class=\\"pr\\">$'+p.p+'</span></div></div>';
  });
  c.innerHTML=h;
}
function od(id){
  if(!P.length){
    document.getElementById('dco').innerHTML='<div class=\\"ld\\">Loading...</div>';
    document.getElementById('ov').classList.add('a');document.body.style.overflow='hidden';
    setTimeout(function(){if(P.length)od(id);else{ca()}},500);return;
  }
  var p=P.find(function(x){return x.id===id});if(!p)return;
  var d=document.getElementById('dco');d.innerHTML='';
  d.innerHTML+='<div class=\\"dci\\" style=\\"background-image:url('+p.img+')\\"></div>';
  d.innerHTML+='<div class=\\"ct\\">'+esc(p.cat)+'</div><h2>'+esc(p.n)+'</h2>';
  if(p.p>0)d.innerHTML+='<div class=\\"pb\\">$'+p.p+'</div><br>';
  if(p.d)d.innerHTML+='<div class=\\"ds\\">'+esc(p.d)+'</div>';
  document.getElementById('ov').classList.add('a');document.body.style.overflow='hidden';
}
function ca(e){if(e&&e.target!==e.currentTarget)return;document.getElementById('ov').classList.remove('a');document.body.style.overflow='';}
"""
JS = JS.replace("TAB_JSON", json.dumps(tabs_json))

# Build HTML
# Convert products_flat to JSON for data.json
data_json = json.dumps(products_flat, indent=2)

with open('data.json', 'w') as f:
    f.write(data_json)

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>BunkBedWorld</title>
<style>{CSS}</style>
</head>
<body>
<div class="hdr"><h1>BunkBed<span>World</span></h1><p>Furniture for every room</p></div>
<nav class="nav">{tabs_html}</nav>
<div class="ctr" id="m"><div class="grid">{SSR_HTML}</div></div>
<div class="ov" id="ov" onclick="ca(event)"><div class="dc" onclick="event.stopPropagation()"><button class="dx" onclick="ca()">&#10005;</button><div id="dco"></div></div></div>
<div class="ftr"><p><strong>BunkBedWorld</strong> — Chicago</p></div>
<script>{JS}</script>
</body>
</html>"""

with open('index.html', 'w') as f:
    f.write(HTML)

print(f"✅ Built: index.html ({len(HTML)/1024:.0f} KB), data.json ({len(data_json)/1024:.0f} KB, {len(products_flat)} products)")

# Validate JS
import subprocess
result = subprocess.run(['node', '-e', f'try{{eval({repr(JS)})}}catch(e){{console.log(e.message)}}'],
                       capture_output=True, text=True)
if result.stdout.strip():
    print(f"❌ JS: {result.stdout.strip()}")
else:
    print("✅ JS valid")
    print(f"   tabs: {len(tabs_json)} tabs, SSR: {len(SSR_HTML)} bytes")