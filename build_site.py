#!/usr/bin/env python3
"""Build BunkBedWorld v2 — image carousels, descriptions, robust event handling."""
import json, re, subprocess

with open('products.json.bak') as f:
    raw = json.load(f)
raw = [p for p in raw if not p.get('sold_out') and 'sell_price' in p]

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

# Build tabs JSON
tabs_json = []
for tname, cnames in TAB_DEFS:
    items = []
    for cn in cnames:
        cnt = sum(1 for p in raw if p["category"] == cn)
        if cnt > 0:
            items.append({"n": cn, "c": cnt})
    if items:
        tabs_json.append({"t": tname, "g": items})

def esc(s):
    if not s: return ''
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;").replace("\n", "<br>"))

# Build products with multiple images
products = []
for p in raw:
    img = p["image"]
    # Generate image indices from URL pattern _i{N}_
    imgs = [img]
    m = re.search(r'_i(\d+)_', img)
    if m:
        max_idx = int(m.group(1))
        if max_idx > 1:
            imgs = []
            for idx in range(1, max_idx + 1):
                new_url = img.replace(f'_i{m.group(1)}_', f'_i{idx}_')
                imgs.append(new_url)
    
    products.append({
        "id": p["id"],
        "n": p["name"],
        "imgs": imgs,
        "cat": p["category"],
        "p": p["sell_price"],
        "d": p.get("description", "").strip(),
    })

# Sort by price within category
cats = {}
for p in products:
    cats.setdefault(p["cat"], []).append(p)
for cat in cats:
    cats[cat].sort(key=lambda x: x["p"])

products_flat = []
for cat in sorted(cats.keys()):
    products_flat.extend(cats[cat])

def render_cards(prods):
    h = ""
    for p in prods:
        h += '<div class="card" data-id="' + p["id"] + '">'
        h += '<div class="ci" style="background-image:url(' + p["imgs"][0] + ')"></div>'
        h += '<div class="cb"><div class="ct">' + esc(p["cat"]) + '</div>'
        h += '<h3>' + esc(p["n"]) + '</h3>'
        h += '<span class="pr">$' + str(p["p"]) + '</span></div></div>'
    return h

SSR_PRODS = [p for p in products_flat if p["cat"] in TAB_DEFS[0][1]]
SSR_HTML = render_cards(SSR_PRODS)

# Tab buttons with dropdowns
tabs_html = ""
first = True
for tname, cnames in TAB_DEFS:
    tot = sum(1 for p in raw if p["category"] in cnames)
    act = " active" if first else ""
    first = False
    
    tabs_html += '<div class="tb' + act + '" data-tab="' + tname + '">'
    tabs_html += tname + '<span class="c">' + str(tot) + '</span><span class="ar">&#9662;</span>'
    tabs_html += '<div class="drop">'
    tabs_html += '<div class="di active" data-cat="all">' + tname + '<span class="c">' + str(tot) + '</span></div>'
    for cn in cnames:
        c_cnt = sum(1 for p in raw if p["category"] == cn)
        if c_cnt > 0:
            tabs_html += '<div class="di" data-cat="' + cn.replace('"', "&quot;") + '">'
            tabs_html += cn + '<span class="c">' + str(c_cnt) + '</span></div>'
    tabs_html += '</div></div>'

# CSS
CSS = """*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:#f8f7f4;color:#2c2c2c}
.hdr{background:#1a1a2e;color:#fff;padding:1rem 2rem}
.hdr h1{font-size:1.4rem;font-weight:800}
.hdr h1 span{color:#e8b86d}
.hdr p{font-size:.8rem;color:#999;margin-top:2px}
.nav{display:flex;background:#fff;border-bottom:2px solid #e0ddd8;position:sticky;top:0;z-index:10;overflow-x:auto}
.tb{position:relative;flex:1 0 auto;padding:.9rem 1.2rem;font-weight:600;font-size:.9rem;color:#777;background:none;border:none;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;transition:.2s;display:flex;align-items:center;justify-content:center}
.tb:hover{color:#1a1a2e;background:#f8f7f4}
.tb.active{color:#1a1a2e;border-bottom-color:#e8b86d}
.tb .c{display:inline-block;background:#e8b86d20;color:#1a1a2e;font-size:.7rem;padding:1px 7px;border-radius:10px;margin-left:5px;vertical-align:middle}
.tb .ar{margin-left:5px;font-size:.7rem;vertical-align:middle;transition:transform .2s;display:inline-block}
.tb.active .ar{transform:rotate(180deg)}
.drop{display:none;position:absolute;top:100%;left:0;background:#fff;border:1px solid #e0ddd8;border-radius:0 0 10px 10px;box-shadow:0 8px 28px rgba(0,0,0,.12);min-width:200px;z-index:50;overflow:hidden}
.drop.a{display:block}
.di{padding:.7rem 1.2rem;font-size:.85rem;color:#555;font-weight:500;cursor:pointer;white-space:nowrap;transition:.15s;border-bottom:1px solid #f0eee8;display:flex;align-items:center;justify-content:space-between}
.di:last-child{border-bottom:none}
.di:hover{background:#e8b86d20;color:#1a1a2e}
.di.active{background:#e8b86d20;color:#1a1a2e;font-weight:700}
.di .c{font-size:.7rem;background:#f0eee8;padding:1px 7px}
.di.active .c{background:#e8b86d;color:#1a1a2e}
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
.dx{position:absolute;top:1rem;right:1rem;background:none;border:none;font-size:1.5rem;cursor:pointer;color:#888;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;z-index:5}
.dx:hover{background:#f0f0f0}
.dci{width:100%;height:300px;background-size:contain;background-position:center;background-repeat:no-repeat;background-color:#e8e3dc;border-radius:12px;margin-bottom:1.5rem;position:relative}
.car{display:flex;gap:6px;justify-content:center;margin-bottom:1rem}
.car span{width:10px;height:10px;border-radius:50%;background:#ddd;cursor:pointer}
.car span.a{background:#e8b86d}
.dc .ct{font-size:.8rem;color:#e8b86d;font-weight:600;text-transform:uppercase;margin-bottom:.5rem;padding:0 60px 0 0}
.dc h2{font-size:1.4rem;color:#1a1a2e;margin-bottom:.5rem;padding:0 60px 0 0}
.dc .pb{display:inline-block;background:#e8b86d20;color:#1a1a2e;font-weight:700;font-size:1.3rem;padding:8px 24px;border-radius:8px;margin:.5rem 0}
.dc .ds{margin-top:1rem;white-space:pre-wrap;font-size:.9rem;color:#555;line-height:1.5}
.ftr{background:#1a1a2e;color:#888;text-align:center;padding:2rem;margin-top:2rem;font-size:.85rem}
.ftr strong{color:#e8b86d}
.ld{text-align:center;padding:4rem;color:#888}
@media(max-width:600px){.hdr{padding:.8rem 1rem}.tb{padding:.7rem .8rem;font-size:.85rem}.grid{grid-template-columns:1fr}.ov{padding:1rem}.dc{padding:1.5rem}.dci{height:220px}.drop{min-width:160px}}
"""

# JavaScript — clean, no inline onclick on cards (event delegation)
TABS_JSON_STR = json.dumps(tabs_json)
JS = """var T=""" + TABS_JSON_STR + """;
var P=[],ct='Living Room',sc='all';

function esc(s){
  if(!s)return'';
  var d=document.createElement('div');
  d.appendChild(document.createTextNode(s));
  return d.innerHTML.replace(/\\n/g,'<br>');
}

function init(){
  // Tab buttons — toggle dropdown
  var tabs=document.querySelectorAll('.tb');
  for(var i=0;i<tabs.length;i++){(function(b){
    b.onclick=function(e){
      e.stopPropagation();
      var n=b.dataset.tab;
      // Close others
      for(var j=0;j<tabs.length;j++){
        if(tabs[j]!==b){var od=tabs[j].querySelector('.drop');if(od)od.classList.remove('a');}
        tabs[j].classList.toggle('active',tabs[j].dataset.tab===n);
      }
      var dd=b.querySelector('.drop');
      if(dd)dd.classList.toggle('a');
      ct=n;
    };
    // Subcategory clicks
    var dis=b.querySelectorAll('.di');
    for(var k=0;k<dis.length;k++){(function(d){
      d.onclick=function(e){
        e.stopPropagation();
        sc=d.dataset.cat;
        var dd=b.querySelector('.drop');
        if(dd)dd.classList.remove('a');
        for(var m=0;m<dis.length;m++)dis[m].classList.remove('active');
        d.classList.add('active');
        if(P.length)rc();
      };
    })(dis[k]);}
  })(tabs[i]);}
  
  // Close dropdowns on outside click
  document.addEventListener('click',function(){
    var ads=document.querySelectorAll('.tb .drop');
    for(var j=0;j<ads.length;j++)ads[j].classList.remove('a');
  });
  
  if(P.length)rc();
}

// Card click delegation — set immediately, not inside init
(function(){
  var m=document.getElementById('m');
  if(m) m.onclick=function(e){
    var el=e.target.closest('.card');
    if(el && el.dataset.id){
      e.preventDefault();
      od(el.dataset.id);
      return false;
    }
  };
})();

fetch('/data.json').then(function(r){return r.json()}).then(function(d){P=d;init();}).catch(function(e){console.log('fetch err',e);init();});

function rc(){
  if(!P.length){setTimeout(rc,99);return;}
  var c=document.getElementById('m');
  var tab=T.find(function(t){return t.t===ct});
  if(!tab){c.innerHTML='<div class="ld">No products.</div>';return;}
  var fp;
  if(sc==='all')fp=P.filter(function(p){return tab.g.some(function(g){return g.n===p.cat})});
  else fp=P.filter(function(p){return p.cat===sc});
  var h='';
  for(var i=0;i<fp.length;i++){
    var p=fp[i];
    h+='<div class="card" data-id="'+p.id+'">';
    h+='<div class="ci" style="background-image:url('+p.imgs[0]+')"></div>';
    h+='<div class="cb"><div class="ct">'+esc(p.cat)+'</div><h3>'+esc(p.n)+'</h3><span class="pr">$'+p.p+'</span></div></div>';
  }
  c.innerHTML=h||'<div class="ld">No products in this category.</div>';
}

function od(id){
  var dco=document.getElementById('dco');
  if(!P.length){
    dco.innerHTML='<div class="ld">Loading...</div>';
    document.getElementById('ov').classList.add('a');
    document.body.style.overflow='hidden';
    setTimeout(function(){if(P.length)od(id);else ca();},500);
    return;
  }
  var p=P.find(function(x){return x.id===id});
  if(!p){dco.innerHTML='<div class="ld">Product not found.</div>';return;}
  
  var h='<div class="dci" id="dci" style="background-image:url('+p.imgs[0]+')"></div>';
  if(p.imgs.length>1){
    h+='<div class="car" id="car">';
    for(var i=0;i<p.imgs.length;i++)h+='<span'+(i===0?' class="a"':'')+' data-n="'+i+'"></span>';
    h+='</div>';
  }
  h+='<div class="ct">'+esc(p.cat)+'</div><h2>'+esc(p.n)+'</h2>';
  if(p.p>0)h+='<div class="pb">$'+p.p+'</div><br>';
  if(p.d)h+='<div class="ds">'+esc(p.d)+'</div>';
  dco.innerHTML=h;
  
  // Carousel click
  var car=document.getElementById('car');
  if(car){
    car.onclick=function(e){
      var sp=e.target.closest('span');
      if(sp && sp.dataset.n){
        var n=parseInt(sp.dataset.n);
        document.getElementById('dci').style.backgroundImage='url('+p.imgs[n]+')';
        var sps=car.querySelectorAll('span');
        for(var i=0;i<sps.length;i++)sps[i].classList.toggle('a',i===n);
      }
    };
  }
  
  document.getElementById('ov').classList.add('a');
  document.body.style.overflow='hidden';
}

function ca(e){
  if(e && e.target!==e.currentTarget)return;
  document.getElementById('ov').classList.remove('a');
  document.body.style.overflow='';
}
"""

# Write data.json with imgs array
data_json = json.dumps(products_flat, indent=2)
with open('data.json', 'w') as f:
    f.write(data_json)

# Build HTML
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>BunkBedWorld</title>
<style>""" + CSS + """</style>
</head>
<body>
<div class="hdr"><h1>BunkBed<span>World</span></h1><p>Furniture for every room</p></div>
<nav class="nav">""" + tabs_html + """</nav>
<div class="ctr" id="m"><div class="grid">""" + SSR_HTML + """</div></div>
<div class="ov" id="ov" onclick="ca(event)"><div class="dc" onclick="event.stopPropagation()"><button class="dx" onclick="ca()">&#10005;</button><div id="dco"></div></div></div>
<div class="ftr"><p><strong>BunkBedWorld</strong> — Chicago</p></div>
<script>""" + JS + """</script>
</body>
</html>"""

with open('index.html', 'w') as f:
    f.write(HTML)

print("Built: index.html (" + str(len(HTML) // 1024) + " KB), data.json (" + str(len(data_json) // 1024) + " KB, " + str(len(products_flat)) + " products)")

# Validate
result = subprocess.run(['node', '--check', '-'], input=JS.encode(), capture_output=True, timeout=5)
if result.returncode == 0:
    print("JS: valid")
else:
    print("JS: " + result.stderr.decode())

# Stats
total_imgs = sum(len(p["imgs"]) for p in products_flat)
multi_imgs = sum(1 for p in products_flat if len(p["imgs"]) > 1)
has_desc = sum(1 for p in products_flat if p["d"])
print("Stats: " + str(total_imgs) + " total images across " + str(len(products_flat)) + " products")
print("       " + str(multi_imgs) + " products with 2+ images (" + str(len(products_flat)) + " with single)")
print("       " + str(has_desc) + " products with descriptions")

for tname, cnames in TAB_DEFS:
    tot = sum(1 for p in raw if p["category"] in cnames)
    print("  " + tname + ": " + str(tot) + " products")