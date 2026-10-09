#!/usr/bin/env python3
"""Build BunkBedWorld site — fresh, clickable items, image gallery, no old code."""

import json, math

PRODUCTS_FILE = 'products.json'
OUTPUT_FILE = 'index.html'

# ── Tab definitions ─────────────────────────────────────────────────────────
TABS = [
    ("Living Room", [
        "Stationary Sofa & Loveseats", "Stationary Sectionals",
        "Reclining Sofa & Loveseats", "Reclining Sectionals",
        "Recliners & Lift Chairs", "Occasional Tables",
        "TV Stands", "Sleepers & Futons", "Accessories",
        "Office & Bookcase", "Sofas", "Sofa & Loveseat sets",
    ]),
    ("Bedroom", [
        "Beds", "Bedrooms", "Daybeds", "Mattresses", "Vanities & Mirrors",
    ]),
    ("Dining Room", [
        "Dining Rooms", "Barstools & Chairs", "Barstools",
    ]),
    ("Bunk Beds", [
        "Bunk Beds",
    ]),
]

# ── Helpers ─────────────────────────────────────────────────────────────────
def esc(s):
    if not s: return ''
    return (s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            .replace('"',"&quot;").replace("'","&#39;"))

def get_images(product):
    """Return list of image paths for a product."""
    imgs = product.get('images') or []
    if isinstance(imgs, str):
        imgs = [imgs]
    if product.get('image') and product['image'] not in imgs:
        imgs.insert(0, product['image'])
    return [i for i in imgs if i]

# ── Load products ───────────────────────────────────────────────────────────
print("Loading products...")
with open(PRODUCTS_FILE) as f:
    raw = json.load(f)

products = [p for p in raw if p.get('price', 0) > 0]
print(f"  Loaded {len(products)} products with prices")

# Lock special prices
SPECIAL = {'p1838': 50, 'p790': 70, 'p548': 70, 'b0001': 125}
for p in products:
    pid = p.get('id', '')
    if pid in SPECIAL:
        p['price'] = SPECIAL[pid]

# Group by category, sort by price within each
cats = {}
for p in products:
    c = p.get('category', 'Accessories')
    cats.setdefault(c, []).append(p)
for c in cats:
    cats[c].sort(key=lambda x: x['price'])

# Flatten in tab/category order
cat_order = []
for tname, tcats in TABS:
    for c in tcats:
        if c in cats and c not in cat_order:
            cat_order.append(c)
for c in cats:
    if c not in cat_order:
        cat_order.append(c)

flat = []
for c in cat_order:
    flat.extend(cats[c])

print(f"  {len(flat)} products across {len(cat_order)} categories")
for tname, tcats in TABS:
    cnt = sum(len(cats.get(c, [])) for c in tcats)
    if cnt: print(f"    {tname}: {cnt}")

# ── Build data JSON ─────────────────────────────────────────────────────────
prods_data = []
for p in flat:
    imgs = get_images(p)
    prods_data.append({
        "id": p.get("id", ""),
        "name": p.get("name", ""),
        "imgs": imgs,
        "cat": p.get("category", ""),
        "price": p.get("price", 0),
        "desc": p.get("description", ""),
        "color": p.get("color", ""),
        "mat": p.get("material", ""),
        "dim": p.get("dimensions", ""),
    })

data_html = json.dumps(prods_data).replace('<', '\\u003c').replace('>', '\\u003e')

# Tab structure for JS
tabs_data = []
for tname, tcats in TABS:
    groups = []
    for c in tcats:
        cnt = len(cats.get(c, []))
        if cnt:
            groups.append({"n": c, "c": cnt})
    total = sum(g["c"] for g in groups)
    if total:
        tabs_data.append({"t": tname, "g": groups, "c": total})

# ── Build HTML ──────────────────────────────────────────────────────────────
CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:#f8f7f4;color:#2c2c2c}
.hdr{background:#1a1a2e;color:#fff;padding:1rem 2rem}.hdr h1{font-size:1.4rem;font-weight:800;margin:0}.hdr h1 span{color:#e8b86d}.hdr p{font-size:.8rem;color:#999;margin-top:2px}
.nav{display:flex;background:#fff;border-bottom:2px solid #e0ddd8;position:sticky;top:0;z-index:20;overflow-x:auto}
.tab{position:relative;flex:1 0 auto;padding:.9rem 1.2rem;font-weight:600;font-size:.9rem;color:#777;border:none;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;display:flex;align-items:center;justify-content:center;transition:.2s;background:none}
.tab:hover{color:#1a1a2e;background:#f8f7f4}.tab.on{color:#1a1a2e;border-bottom-color:#e8b86d;background:#f8f7f4}
.tab .c{background:#e8b86d20;color:#1a1a2e;font-size:.7rem;padding:1px 7px;border-radius:10px;margin-left:5px}
.tab .ar{margin-left:4px;font-size:.65rem}.tab.on .ar{transform:rotate(180deg)}
.dd{display:none;position:absolute;top:100%;left:0;background:#fff;border:1px solid #e0ddd8;border-radius:0 0 10px 10px;box-shadow:0 8px 28px rgba(0,0,0,.12);min-width:220px;z-index:30;max-height:70vh;overflow-y:auto}
.dd.s{display:block}
.di{padding:.7rem 1.2rem;font-size:.85rem;color:#555;cursor:pointer;border-bottom:1px solid #f0eee8;display:flex;align-items:center;justify-content:space-between;transition:.15s}
.di:last-child{border-bottom:none}.di:hover{background:#e8b86d20;color:#1a1a2e}
.di .c{font-size:.7rem;background:#f0eee8;padding:1px 7px;border-radius:10px}
.di.on .c{background:#e8b86d;color:#1a1a2e}
.ctr{max-width:1200px;margin:0 auto;padding:2rem 1.5rem;display:none}
.ctr.s{display:block}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:500px){.grid{grid-template-columns:1fr}}
.cd{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.06);cursor:pointer;transition:.2s}
.cd:hover{box-shadow:0 6px 24px rgba(0,0,0,.1)}
.ci{width:100%;height:200px;background-size:cover;background-position:center;background-color:#e8e3dc}
.cb{padding:1rem 1.2rem 1.3rem}.cb .ct{font-size:.72rem;color:#e8b86d;font-weight:600;text-transform:uppercase;margin-bottom:4px}
.cb h3{font-size:.95rem;color:#1a1a2e;line-height:1.3;margin:0 0 4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.cb .pr{font-size:1.1rem;font-weight:700;color:#1a1a2e}
.ftr{background:#1a1a2e;color:#888;text-align:center;padding:2rem;margin-top:2rem;font-size:.85rem}
.ld{text-align:center;padding:4rem;color:#aaa;font-size:1.1rem}
.ov{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.55);z-index:99;padding:2rem;overflow-y:auto}
.ov.s{display:flex;align-items:center;justify-content:center}
.oc{background:#fff;border-radius:16px;max-width:820px;width:100%;padding:2rem;position:relative;box-shadow:0 20px 60px rgba(0,0,0,.3);max-height:92vh;overflow-y:auto;margin:auto}
.x{position:absolute;top:1rem;right:1rem;width:40px;height:40px;border:none;background:none;font-size:1.5rem;cursor:pointer;border-radius:50%;color:#888;display:flex;align-items:center;justify-content:center;transition:.2s;z-index:3}
.x:hover{background:#eee}
.gal{position:relative;width:100%;border-radius:12px;overflow:hidden;margin-bottom:1rem}
.gal img{width:100%;max-height:450px;object-fit:contain;display:block;border-radius:12px}
.gn{position:absolute;top:50%;transform:translateY(-50%);background:rgba(255,255,255,.85);border:none;width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.3rem;cursor:pointer;color:#1a1a2e;transition:.2s;z-index:2}
.gn:hover{background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.15)}
.gl{left:10px}.gr{right:10px}
.dots{display:flex;gap:6px;justify-content:center;margin-top:8px}
.dot{width:10px;height:10px;border-radius:50%;background:#ddd;border:none;cursor:pointer;transition:.25s}
.dot.on{background:#e8b86d;transform:scale(1.3)}
.det{padding:0 1rem 1.5rem}.det .ct{font-size:.78rem;color:#e8b86d;font-weight:600;text-transform:uppercase;margin-bottom:4px}
.det h2{font-size:1.3rem;color:#1a1a2e;margin-bottom:8px}
.det .pr{font-size:1.5rem;font-weight:800;color:#1a1a2e;margin:12px 0 8px}
.det .info{margin-top:12px;font-size:.85rem;color:#555;line-height:1.5}
.det .info strong{color:#1a1a2e}
.det .dim{color:#888;font-size:.8rem;margin-top:8px;white-space:pre-line;line-height:1.5}
@media(max-width:600px){.hdr{padding:.8rem 1rem}.tab{padding:.7rem .8rem;font-size:.85rem}.dd{min-width:160px}.ov{padding:.5rem}.oc{padding:1rem}}
"""

# Tab buttons HTML
tabs_html_parts = []
first = True
for tname, tcats in TABS:
    total = sum(len(cats.get(c, [])) for c in tcats)
    if total == 0:
        continue
    cl = ['tab']
    if first:
        cl.append('on')
        first = False
    html = '<button class="' + ' '.join(cl) + '" data-t="' + tname + '">'
    html += tname + '<span class="c">' + str(total) + '</span><span class="ar">&#9662;</span>'
    html += '<div class="dd">'
    html += '<div class="di on" data-c="">All<span class="c">' + str(total) + '</span></div>'
    for c in tcats:
        cnt = len(cats.get(c, []))
        if cnt:
            html += '<div class="di" data-c="' + esc(c) + '">' + esc(c) + '<span class="c">' + str(cnt) + '</span></div>'
    html += '</div></button>'
    tabs_html_parts.append(html)
TABS_HTML = ''.join(tabs_html_parts)

# SSR Living Room grid
ssr_cats = [c for c in TABS[0][1] if c in cats]
ssr_prods = [p for p in flat if p["category"] in ssr_cats]

def card(p):
    imgs = get_images(p)
    img = imgs[0] if imgs else ''
    return '<div class="cd" onclick="openP(\'' + p["id"] + '\')"><div class="ci" style="background-image:url(' + img + ')"></div><div class="cb"><div class="ct">' + esc(p["category"]) + '</div><h3>' + esc(p["name"]) + '</h3><span class="pr">$' + str(p["price"]) + '</span></div></div>'

SSR_HTML = ''.join(card(p) for p in ssr_prods)

# JavaScript (not in f-string to avoid brace issues)
JS_SNIPPET = """var P=JSON.parse(document.getElementById('pd').textContent);
var T=""" + json.dumps(tabs_data) + """;
var ct="Living Room",sc="",pi=0,pc=[];

function initT(){
 var tb=document.querySelectorAll(".tab");
 for(var i=0;i<tb.length;i++){(function(b){b.onclick=function(e){
  e.stopPropagation();var n=b.dataset.t;
  for(var j=0;j<tb.length;j++){tb[j].classList.toggle("on",tb[j].dataset.t===n);var d=tb[j].querySelector(".dd");if(d&&tb[j]!==b)d.classList.remove("s");}
  var dd=b.querySelector(".dd");if(dd)dd.classList.toggle("s");ct=n;sc="";if(P.length)r();
 };
 var dis=b.querySelectorAll(".di");
 for(var k=0;k<dis.length;k++){(function(d){d.onclick=function(e){
  e.stopPropagation();sc=d.dataset.c;var dd=b.querySelector(".dd");if(dd)dd.classList.remove("s");
  for(var m=0;m<dis.length;m++)dis[m].classList.remove("on");d.classList.add("on");if(P.length)r();
 };})(dis[k]);}
 })(tb[i]);}
 document.addEventListener("click",function(){document.querySelectorAll(".dd").forEach(function(d){d.classList.remove("s");});});
 if(P.length)r();
}

function r(){
 var tab=T.find(function(t){return t.t===ct});
 if(!tab){document.getElementById("m").innerHTML='<div class="ld">No products.</div>';return;}
 var fp=sc?P.filter(function(p){return p.cat===sc;}):P.filter(function(p){return tab.g.some(function(g){return g.n===p.cat;});});
 var h="";
 for(var i=0;i<fp.length;i++){var p=fp[i];
  var img=p.imgs&&p.imgs.length?p.imgs[0]:"";
  h+='<div class="cd" onclick="openP(\\''+p.id+'\\')"><div class="ci" style="background-image:url('+img+')"></div><div class="cb"><div class="ct">'+p.cat+'</div><h3>'+esc(p.name)+'</h3><span class="pr">$'+p.price+'</span></div></div>';
 }
 document.getElementById("m").innerHTML=h||'<div class="ld">No products in this category.</div>';
}

function openP(id){
 pi=0;
 var p=P.find(function(x){return x.id===id;});if(!p)return;
 pc=p.imgs&&p.imgs.length?p.imgs:[];
 document.getElementById("gal").innerHTML="";
 if(pc.length){
  var img='<img src="'+pc[0]+'" id="gi">';
  var nav=(pc.length>1?'<button class="gn gl" onclick="gal(-1)">&#9664;</button><button class="gn gr" onclick="gal(1)">&#9654;</button>':"");
  var dots="";
  for(var i=0;i<pc.length;i++)dots+='<button class="dot'+(i==0?' on':"")+'" onclick="goG('+i+')"></button>';
  document.getElementById("gal").innerHTML=img+nav+'<div class="dots">'+dots+"</div>";
 }
 var spec=p.desc?p.desc.replace(/\\\\n/g,"<br>")+(p.color?"<br><strong>Color:</strong> "+p.color:"")+(p.mat?"<br><strong>Material:</strong> "+p.mat:""):"";
 var dim=p.dim?p.dim.replace(/\\\\n/g,"<br>"):"";
 document.getElementById("det").innerHTML='<div class="ct">'+p.cat+'</div><h2>'+esc(p.name)+'</h2><div class="pr">$'+p.price+'</div>'+(spec?'<div class="info">'+spec+'</div>':"")+(dim?'<div class="dim">'+dim+'</div>':"");
 document.getElementById("ov").classList.add("s");document.body.style.overflow="hidden";
}

function closeO(){document.getElementById("ov").classList.remove("s");document.body.style.overflow="";pi=0;pc=[];}

function gal(d){
 if(!pc.length)return;
 pi=(pi+d+pc.length)%pc.length;
 goG(pi);
}
function goG(i){
 pi=i;
 if(pc.length>pi){
  document.getElementById("gi").src=pc[pi];
  var dots=document.querySelectorAll(".dot");
  for(var j=0;j<dots.length;j++)dots[j].classList.toggle("on",j===pi);
 }
}
function esc(s){return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
document.addEventListener("DOMContentLoaded",initT);
"""

# Assemble HTML
TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>BunkBedWorld</title>
<style>CSS_PLACEHOLDER</style>
</head>
<body>

<div class="hdr"><h1><span>BunkBedWorld</span></h1><p>Furniture for every room</p></div>
<nav class="nav">TABS_HTML_PLACEHOLDER</nav>

<div class="ctr s" id="m"><div class="grid">SSR_PLACEHOLDER</div></div>

<div class="ov" id="ov"><div class="oc">
<button class="x" onclick="closeO()">&#10005;</button>
<div class="gal" id="gal"></div>
<div class="det" id="det"></div>
</div></div>

<div class="ftr"><p><strong>BunkBedWorld</strong> — Houston</p></div>

<script id="pd" type="application/json">DATA_PLACEHOLDER</script>
<script>
JS_PLACEHOLDER
</script>
</body>
</html>"""

HTML = (TEMPLATE
    .replace('CSS_PLACEHOLDER', CSS)
    .replace('TABS_HTML_PLACEHOLDER', TABS_HTML)
    .replace('SSR_PLACEHOLDER', SSR_HTML)
    .replace('DATA_PLACEHOLDER', data_html)
    .replace('JS_PLACEHOLDER', JS_SNIPPET))

with open(OUTPUT_FILE, 'w') as f:
    f.write(HTML)

print(f"\n✅ Built {OUTPUT_FILE} ({len(HTML)//1024} KB, {len(flat)} products)")
print(f"   Tabs: {len([t for t in TABS if sum(len(cats.get(c,[])) for c in t[1])])}")
print(f"   Products with multiple images: {sum(1 for p in flat if len(get_images(p))>1)}")
print(f"   Grid: 3 columns (responsive to 2→1)")