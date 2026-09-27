#!/usr/bin/env python3
"""Rebuild bunkbedworld index.html from data.json — SSR + inline data, no fetch dependency."""

import json

# ── Load data ──────────────────────────────────────────────────────────────────
with open("data.json") as f:
    raw = json.load(f)

# Sort by price within each category
cats = {}
for p in raw:
    c = p["cat"]
    cats.setdefault(c, []).append(p)
for c in cats:
    cats[c].sort(key=lambda x: x["price"])
flat = []
for c in sorted(cats.keys(), key=lambda x: {"Stationary Sofa & Loveseats":1,
    "Stationary Sectionals":2,"Reclining Sofa & Loveseats":3,
    "Reclining Sectionals":4,"Recliners & Lift Chairs":5,
    "Occasional Tables":6,"TV Stands":7,"Sleepers & Futons":8,
    "Accessories":9,"Office & Bookcase":10,"Beds":11,
    "Bedrooms":12,"Daybeds":13,"Mattresses":14,
    "Vanities & Mirrors":15,"Dining Rooms":16,"Barstools":17}.get(x,99)):
    flat.extend(cats[c])

# ── Tab definitions ────────────────────────────────────────────────────────────
TABS = [
    ("Living Room", [
        "Stationary Sofa & Loveseats",
        "Stationary Sectionals",
        "Reclining Sofa & Loveseats",
        "Reclining Sectionals",
        "Recliners & Lift Chairs",
        "Occasional Tables",
        "TV Stands",
        "Sleepers & Futons",
        "Accessories",
        "Office & Bookcase",
    ]),
    ("Bedroom", [
        "Beds",
        "Bedrooms",
        "Daybeds",
        "Mattresses",
        "Vanities & Mirrors",
    ]),
    ("Dining Room", [
        "Dining Rooms",
        "Barstools",
    ]),
]

def esc(s):
    if not s: return ""
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;").replace("'","&#39;")

def render_cards(prods):
    h = ""
    for p in prods:
        h += '<div class="card">'
        h += '<div class="ci" style="background-image:url(' + esc(p["img"]) + ')"></div>'
        h += '<div class="cb">'
        h += '<div class="ct">' + esc(p["cat"]) + '</div>'
        h += '<h3>' + esc(p["name"]) + '</h3>'
        h += '<span class="pr">$' + str(p["price"]) + '</span>'
        h += '</div></div>'
    return h

# SSR: render all Living Room products initially
ssr_cats = TABS[0][1]
ssr_prods = [p for p in flat if p["cat"] in ssr_cats]
ssr_html = render_cards(ssr_prods)

# Embed all data inline (no fetch needed)
data_inline = json.dumps(flat)

# Build tabs JSON for JS
tab_json = []
for tname, cnames in TABS:
    items = []
    for c in cnames:
        cnt = len(cats.get(c, []))
        if cnt > 0:
            items.append({"n": c, "c": cnt})
    total = sum(i["c"] for i in items)
    tab_json.append({"t": tname, "total": total, "g": items})

tabs_js = json.dumps(tab_json)

# ── Tab buttons HTML ───────────────────────────────────────────────────────────
tabs_html = ""
for tname, cnames in TABS:
    total = sum(len(cats.get(c, [])) for c in cnames)
    tabs_html += '<div class="tb active" data-tab="' + tname + '">'
    tabs_html += tname + '<span class="c">' + str(total) + '</span><span class="ar">&#9662;</span>'
    tabs_html += '<div class="drop">'
    for c in cnames:
        cnt = len(cats.get(c, []))
        if cnt > 0:
            tabs_html += '<div class="di" data-cat="' + c.replace('&','&amp;').replace('"','&quot;') + '">'
            tabs_html += c + '<span class="c">' + str(cnt) + '</span></div>'
    tabs_html += '</div></div>'

CSS = """body{font-family:system-ui,-apple-system,sans-serif;background:#f8f7f4;color:#2c2c2c;margin:0}
.hdr{background:#1a1a2e;color:#fff;padding:1rem 2rem}.hdr h1{font-size:1.4rem;font-weight:800;margin:0}.hdr h1 span{color:#e8b86d;cursor:pointer}.hdr h1 span:hover{color:#f0d08a}.hdr p{font-size:.8rem;color:#999;margin:2px 0 0}
.nav{display:flex;background:#fff;border-bottom:2px solid #e0ddd8;position:sticky;top:0;z-index:10;overflow-x:auto}
.tb{position:relative;flex:1 0 auto;padding:.9rem 1.2rem;font-weight:600;font-size:.9rem;color:#777;background:none;border:none;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;display:flex;align-items:center;justify-content:center;transition:color .2s}
.tb:hover{color:#1a1a2e;background:#f8f7f4}.tb.active{color:#1a1a2e;border-bottom-color:#e8b86d;background:#f8f7f4}
.tb .c{background:#e8b86d20;color:#1a1a2e;font-size:.7rem;padding:1px 7px;border-radius:10px;margin-left:5px}
.tb .ar{margin-left:4px;font-size:.65rem;transition:transform .2s}.tb.active .ar{transform:rotate(180deg)}
.drop{display:none;position:absolute;top:100%;left:0;background:#fff;border:1px solid #e0ddd8;border-radius:0 0 10px 10px;box-shadow:0 8px 28px rgba(0,0,0,.12);min-width:220px;z-index:50;max-height:70vh;overflow-y:auto}
.drop.a{display:block}
.di{padding:.7rem 1.2rem;font-size:.85rem;color:#555;cursor:pointer;border-bottom:1px solid #f0eee8;display:flex;align-items:center;justify-content:space-between;transition:.15s}
.di:last-child{border-bottom:none}.di:hover{background:#e8b86d20;color:#1a1a2e}
.di .c{font-size:.7rem;background:#f0eee8;padding:1px 7px}
.hero{position:relative;overflow:hidden}
.hero img{width:100%;height:auto;max-height:65vh;object-fit:cover;display:block}
.hero-overlay{position:absolute;top:0;left:0;width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(26,26,46,.35);text-align:center;padding:2rem}
.hero-overlay h2{font-size:2.5rem;font-weight:800;color:#fff;margin:0;text-shadow:0 2px 8px rgba(0,0,0,.3)}
.hero-overlay p{font-size:1.1rem;color:#e8b86d;margin:.5rem 0 0;text-shadow:0 1px 4px rgba(0,0,0,.3)}
.hero-overlay .hm{font-size:.9rem;color:#f8f7f4;margin-top:1.5rem;opacity:.8}
.hero.h{display:none}
.ctr{max-width:1200px;margin:0 auto;padding:2rem 1.5rem;display:none}
.ctr.a{display:block}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1.5rem}
.card{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.06);text-decoration:none;color:inherit;display:flex;flex-direction:column;cursor:default;transition:box-shadow .15s}
.card:hover{box-shadow:0 4px 20px rgba(0,0,0,.12)}
.ci{width:100%;height:200px;background-size:cover;background-position:center;background-color:#e8e3dc;flex-shrink:0}
.cb{padding:1rem 1.2rem 1.3rem;display:flex;flex-direction:column;flex:1}
.cb .ct{font-size:.72rem;color:#e8b86d;font-weight:600;text-transform:uppercase;margin-bottom:4px;letter-spacing:.5px}
.cb h3{font-size:.95rem;color:#1a1a2e;line-height:1.3;margin:0 0 4px}
.cb .pr{font-size:1.1rem;font-weight:700;color:#1a1a2e}
.detail{max-width:800px;margin:2rem auto;padding:1.5rem;background:#fff;border-radius:12px;box-shadow:0 2px 16px rgba(0,0,0,.08);display:none;text-align:center}
.detail.a{display:block}
.ftr{background:#1a1a2e;color:#888;text-align:center;padding:2rem;font-size:.85rem}
.ld{text-align:center;padding:4rem;color:#aaa;font-size:1.1rem}
@media(max-width:600px){.hdr{padding:.8rem 1rem}.tb{padding:.7rem .8rem;font-size:.85rem}.grid{grid-template-columns:1fr;gap:1rem}.drop{min-width:160px}.hero-overlay h2{font-size:1.5rem}.hero-overlay p{font-size:.9rem}}
"""

# JavaScript inline — no fetch dependency, uses embedded data
JS_FUNC = r"""
var T=""" + tabs_js + r""";
var ct='Living Room',sc='',P=[];
function init(){
  var tabs=document.querySelectorAll('.tb');
  for(var i=0;i<tabs.length;i++)(function(b){
    b.onclick=function(e){
      e.stopPropagation();var n=b.dataset.tab;
      for(var j=0;j<tabs.length;j++){
        if(tabs[j]!==b){var od=tabs[j].querySelector('.drop');if(od)od.classList.remove('a');}
        tabs[j].classList.toggle('active',tabs[j].dataset.tab===n);
      }
      var dd=b.querySelector('.drop');if(dd)dd.classList.toggle('a');ct=n;sc='';if(P.length)rc();
    };
    var dis=b.querySelectorAll('.di');
    for(var k=0;k<dis.length;k++)(function(d){
      d.onclick=function(e){
        e.stopPropagation();sc=d.dataset.cat;ct=b.dataset.tab;
        var dd=b.querySelector('.drop');if(dd)dd.classList.remove('a');
        for(var m=0;m<dis.length;m++)dis[m].classList.remove('active');d.classList.add('active');
        if(P.length)rc();
      };
    })(dis[k]);
  })(tabs[i]);
}
function rc(){
  var tab=T.find(function(t){return t.t===ct});if(!tab){document.getElementById('m').innerHTML='<div class="ld">No products.</div>';return;}
  var fp;
  if(sc){fp=P.filter(function(p){return p.cat===sc;});}
  else{fp=P.filter(function(p){return tab.g.some(function(g){return g.n===p.cat;});});}
  var h='';
  for(var i=0;i<fp.length;i++){var p=fp[i];
    h+='<div class="card"><div class="ci" style="background-image:url('+p.img+')"></div>';
    h+='<div class="cb"><div class="ct">'+p.cat+'</div><h3>'+esc(p.name)+'</h3><span class="pr">$'+p.price+'</span></div></div>';
  }
  document.getElementById('m').innerHTML=h||'<div class="ld">No products in this category.</div>';
  document.getElementById('hero').className='hero h';
}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
"""

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>BunkBedWorld</title>
<style>""" + CSS + """</style>
</head>
<body>
<div class="hdr"><h1><span>BunkBedWorld</span></h1><p>Furniture for every room</p></div>
<nav class="nav">""" + tabs_html + """</nav>
<div class="hero" id="hero">
  <img src="/images/hero-banner.jpg" alt="">
  <div class="hero-overlay">
    <h2>Affordable Furniture &amp; Mattresses</h2>
    <p>Quality pieces for every room in your home</p>
    <div class="hm">Select a category above to browse our collection</div>
  </div>
</div>
<div class="ctr a" id="m"><div class="grid">""" + ssr_html + """</div></div>
<div class="detail" id="d"></div>
<div class="ftr"><p><strong>BunkBedWorld</strong> — Houston</p></div>
<script id="pd" type="application/json">""" + data_inline + """</script>
<script>
""" + JS_FUNC + """
P = JSON.parse(document.getElementById('pd').textContent);
init();
</script>
</body>
</html>"""

with open("index.html", "w") as f:
    f.write(HTML)

print(f"Done: index.html ({len(HTML)//1024} KB) — {len(flat)} products inline, SSR Living Room grid")