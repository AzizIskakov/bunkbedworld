#!/usr/bin/env python3
"""Build BunkBedWorld — simple: menu + grid, no overlay."""
import json, subprocess

# Use backup data (860 products)
with open('products.json.fresh.bak') as f:
    raw = json.load(f)

products = []
for p in raw:
    pid = p.get('id','')
    price = p.get('price',0) or p.get('sell_price',0)
    if price <= 0:
        continue
    # Lock BBW prices
    if pid == 'p1838': price = 50
    elif pid == 'p790': price = 70
    elif pid == 'p548': price = 70
    elif pid == 'b0001': price = 125
    products.append({
        "id": pid,
        "name": p.get("name",""),
        "img": (p.get("images",[p.get("image","")]) or [""])[0],
        "cat": p.get("cat","") or p.get("category",""),
        "price": price,
    })

print(f"Products: {len(products)}")

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
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;").replace("'","&#39;")

# Build tabs JSON
tabs_json = []
for tname, cnames in TAB_DEFS:
    items = []
    for cn in cnames:
        cnt = sum(1 for p in products if p["cat"] == cn)
        if cnt > 0:
            items.append({"n": cn, "c": cnt})
    if items:
        tabs_json.append({"t": tname, "g": items})

# Sort by price within category
cats = {}
for p in products:
    cats.setdefault(p["cat"], []).append(p)
for cat in cats:
    cats[cat].sort(key=lambda x: x["price"])

products_flat = []
for cat in sorted(cats.keys()):
    products_flat.extend(cats[cat])

def render_cards(prods):
    h = ""
    for p in prods:
        h += '<div class="card">'
        h += '<div class="ci" style="background-image:url(' + p["img"] + ')"></div>'
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
    tot = sum(1 for p in products if p["cat"] in cnames)
    act = " active" if first else ""
    first = False
    tabs_html += '<div class="tb' + act + '" data-tab="' + tname + '">'
    tabs_html += tname + '<span class="c">' + str(tot) + '</span><span class="ar">&#9662;</span>'
    tabs_html += '<div class="drop">'
    tabs_html += '<div class="di active" data-cat="all">All<span class="c">' + str(tot) + '</span></div>'
    for cn in cnames:
        c_cnt = sum(1 for p in products if p["cat"] == cn)
        if c_cnt > 0:
            tabs_html += '<div class="di" data-cat="' + cn.replace('"', "&quot;") + '">'
            tabs_html += cn + '<span class="c">' + str(c_cnt) + '</span></div>'
    tabs_html += '</div></div>'

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
.card{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.06)}
.ci{width:100%;height:200px;background-size:cover;background-position:center;background-color:#e8e3dc}
.cb{padding:1rem 1.2rem 1.3rem}.cb .ct{font-size:.72rem;color:#e8b86d;font-weight:600;text-transform:uppercase;margin-bottom:3px}
.cb h3{font-size:.95rem;color:#1a1a2e;line-height:1.3;margin-bottom:2px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.cb .pr{font-size:1.1rem;font-weight:700;color:#1a1a2e}
.ftr{background:#1a1a2e;color:#888;text-align:center;padding:2rem;margin-top:2rem;font-size:.85rem}.ftr strong{color:#e8b86d}
.ld{text-align:center;padding:4rem;color:#aaa;font-size:1.1rem}
@media(max-width:600px){.hdr{padding:.8rem 1rem}.tb{padding:.7rem .8rem;font-size:.85rem}.grid{grid-template-columns:1fr}.drop{min-width:160px}}
"""

TABS_JSON_STR = json.dumps(tabs_json)
JS = """var T=""" + TABS_JSON_STR + """;
var P=[],ct='Living Room',sc='all';
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
fetch('/data.json').then(function(r){return r.json()}).then(function(d){P=d;init();}).catch(function(e){console.log('fetch',e);});
function rc(){
  if(!P.length){setTimeout(rc,50);return;}
  var c=document.getElementById('m');
  var tab=T.find(function(t){return t.t===ct});if(!tab){c.innerHTML='<div class="ld">No products.</div>';return;}
  var fp=sc==='all'?P.filter(function(p){return tab.g.some(function(g){return g.n===p.cat})}):P.filter(function(p){return p.cat===sc});
  var h='';
  for(var i=0;i<fp.length;i++){var p=fp[i];h+='<div class="card">';h+='<div class="ci" style="background-image:url('+p.img+')"></div>';h+='<div class="cb"><div class="ct">'+p.cat+'</div><h3>'+p.name+'</h3><span class="pr">$'+p.price+'</span></div></div>';}
  c.innerHTML=h||'<div class="ld">No products in this category.</div>';
}
"""

data_json = json.dumps(products_flat, indent=2)
with open('data.json', 'w') as f:
    f.write(data_json)
DATA_INLINE = '<script id="pd" type="application/json">' + json.dumps(products_flat) + '</script>'

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
<div class="ftr"><p><strong>BunkBedWorld</strong> — Chicago</p></div>
<script>""" + JS + """</script>
</body>
</html>"""

with open('index.html', 'w') as f:
    f.write(HTML)

print(f"Built: index.html ({len(HTML)//1024} KB), data.json ({len(data_json)//1024} KB, {len(products_flat)} products)")
r = subprocess.run(['node', '-e', f'try{{new Function({repr(JS)});console.log("JS: OK")}}catch(e){{console.log("JS:",e.message)}}'],
                   capture_output=True, text=True, timeout=5)
print(r.stdout.strip())
for tname, cnames in TAB_DEFS:
    tot = sum(1 for p in products if p["cat"] in cnames)
    print(f"  {tname}: {tot}")
print("No overlay — pure grid + dropdown.")