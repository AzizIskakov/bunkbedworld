#!/usr/bin/env python3
"""Generate index.html with SSR: Living Room products rendered directly in HTML.
Products visible instantly — no JavaScript or network fetch needed for first view.
"""
import json

with open('products.json') as f:
    products = json.load(f)

# Group by category
cats = {}
for p in products:
    cat = p.get("cat") or p.get("category")
    if not cat:
        continue
    if cat not in cats:
        cats[cat] = []
    cats[cat].append(p)
for cat in cats:
    cats[cat].sort(key=lambda p: p.get("price") or p.get("sell_price", 0))

# Tab definitions
tab_groups = [
    ("Living Room", ["Stationary Sofa & Loveseats", "Stationary Sectionals",
                     "Reclining Sofa & Loveseats", "Reclining Sectionals",
                     "Recliners & Lift Chairs", "Occasional Tables",
                     "TV Stands", "Sleepers & Futons", "Accessories",
                     "Office & Bookcase", "Sofa & Loveseat sets", "Sofas"]),
    ("Bed Room", ["Beds", "Bedrooms", "Daybeds", "Mattresses", "Vanities & Mirrors"]),
    ("Dining Room", ["Dining Rooms", "Barstools", "Barstools & Chairs"]),
    ("Bunk Beds", ["Bunk Beds"]),
]

# Build tab data
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
tjson = json.dumps(tabs)

def esc(s):
    if not s:
        return ''
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;').replace("'", '&#39;').replace('\n', '<br>'))

# Pre-render the Living Room tab product grid
lr_names = tab_groups[0][1]
lr_products = [p for p in products if p.get("cat") in lr_names]
lr_products.sort(key=lambda p: p.get("price", 999999))

def render_grid(prods, cat_names, tab_name):
    """Render product grid HTML (same logic as JS rc())"""
    h = '<div class="subcat-bar"><label>Filter:</label>'
    h += '<select class="subcat-select" onchange="fs(this.value)">'
    h += '<option value="__all__">All ' + tab_name + '</option>'
    for c in cat_names:
        cnt = sum(1 for p in prods if p.get("cat") == c)
        if cnt > 0:
            h += '<option value="' + c + '">' + c + ' (' + str(cnt) + ')</option>'
    h += '</select></div><div class="grid">'
    for p in prods:
        imgs = p.get("images") or []
        pid = p["id"]
        h += '<a class="card" onclick="event.preventDefault();od(\'' + pid + '\')">'
        if len(imgs) == 0:
            h += '<div class="ni">No Image</div>'
        elif len(imgs) == 1:
            url = imgs[0].replace("'", "%27")
            h += '<div class="cc"><div class="cs a" style="background-image:url(' + url + ')"></div></div>'
        else:
            h += '<div class="cc" id="c' + pid + '">'
            for i, img in enumerate(imgs):
                url = img.replace("'", "%27")
                h += '<div class="cs' + (' a' if i == 0 else '') + '" style="background-image:url(' + url + ')"></div>'
            h += '<button class="cb" onclick="event.stopPropagation();cm(\'' + pid + '\',-1)">‹</button>'
            h += '<button class="cb n" onclick="event.stopPropagation();cm(\'' + pid + '\',1)">›</button>'
            h += '<div class="cd">'
            for i in range(len(imgs)):
                h += '<span' + (' class="a"' if i == 0 else '') + ' onclick="event.stopPropagation();cg(\'' + pid + '\',' + str(i) + ')"></span>'
            h += '</div></div>'
        h += '<div class="card-body"><div class="ct">' + esc(p.get("cat", "")) + '</div><h3>' + esc(p.get("name", "")) + '</h3><div class="pt">$' + str(p.get("price", 0)) + '</div></div></a>'
    h += '</div>'
    return h

lr_grid_html = render_grid(lr_products, lr_names, "Living Room")

# Pre-render tab buttons
tab_buttons_html = ""
for tname, cnames in tab_groups:
    cnt = sum(len(cats.get(cn, [])) for cn in cnames if cn in cats)
    act = ' active' if tname == 'Living Room' else ''
    tab_buttons_html += f'<button class="tab-btn{act}">{tname}<span class="bc">{cnt}</span></button>\n'

# -- JavaScript: setup nav, carousels, detail overlay, tab switching --
# Keep product data fetched on-demand for other tabs
js = '''
var P=[];
var ct=null,cn=null,ci={};
var LR_LOADED=true;

function esc(s){if(!s)return'';var d=document.createElement('div');d.appendChild(document.createTextNode(s));return d.innerHTML.replace(/\\n/g,'<br>')}
function jq(s){return JSON.stringify(s)}

function init(){
  document.querySelectorAll('.tab-btn').forEach(function(b){
    b.onclick=function(){sw(b.textContent.trim().split(' ')[0])};
  });
  sw('Living Room');
}

function sw(name){
  ct=name;cn=null;
  document.querySelectorAll('.tab-btn').forEach(function(b){
    b.classList.toggle('active',b.textContent.trim().startsWith(name));
  });
  if(ct!='Living Room'||P.length==0)rc();
}

function rc(){
  var c=document.getElementById('main');
  if(ct!='Living Room'&&P.length<100){
    c.innerHTML='<div class="loading">Loading...</div>';
    fetch('/products.json').then(function(r){return r.json()}).then(function(d){P=d;rc();}).catch(function(){c.innerHTML='<div class="loading">Failed to load.</div>'});
    return;
  }
  var tab=T.find(function(t){return t.t===ct});
  if(!tab){c.innerHTML='<div class="loading">No products found.</div>';return}
  var h='<div class="subcat-bar"><label>Filter:</label><select class="subcat-select" onchange="fs(this.value)">';
  h+='<option value="__all__">All '+ct+'</option>';
  tab.g.forEach(function(g){h+='<option value="'+g.n+'">'+g.n+' ('+g.c+')</option>'});
  h+='</select></div><div class="grid">';
  var cnames=tab.g.map(function(g){return g.n});
  var fp=P.filter(function(p){return cnames.indexOf(p.cat)>=0});
  fp.forEach(function(p){
    var imgs=p.images||[];
    h+='<a class="card" onclick="event.preventDefault();od(\\''+p.id+'\\')">';
    if(imgs.length==0){h+='<div class="ni">No Image</div>'}
    else if(imgs.length==1){h+='<div class="cc"><div class="cs a" style="background-image:url('+imgs[0]+')"></div></div>'}
    else{
      h+='<div class="cc" id="c'+p.id+'">';
      imgs.forEach(function(img,i){h+='<div class="cs'+(i==0?' a':'')+'" style="background-image:url('+img+')"></div>'});
      h+='<button class="cb" onclick="event.stopPropagation();cm(\\''+p.id+'\\',-1)">\\u2039</button>';
      h+='<button class="cb n" onclick="event.stopPropagation();cm(\\''+p.id+'\\',1)">\\u203A</button>';
      h+='<div class="cd">';
      imgs.forEach(function(img,i){h+='<span'+(i==0?' class="a"':'')+' onclick="event.stopPropagation();cg(\\''+p.id+'\\','+i+')"></span>'});
      h+='</div></div>';
    }
    h+='<div class="card-body"><div class="ct">'+p.cat+'</div><h3>'+esc(p.name)+'</h3><div class="pt">$'+p.price+'</div></div></a>';
  });
  h+='</div>';
  c.innerHTML=h;
  var sel=c.querySelector('.subcat-select');if(sel)sel.value='__all__';
  for(var k in ci)clearInterval(ci[k]);ci={};
  document.querySelectorAll('.cc').forEach(function(cc){
    var id=cc.id.slice(1);if(id&&!ci[id])ci[id]=setInterval(function(){cm(id,1)},4000);
  });
}

function cm(id,dir){
  var cc=document.getElementById('c'+id);if(!cc)return;
  var slides=cc.querySelectorAll('.cs'),dots=cc.querySelectorAll('.cd span');
  var cur=0;slides.forEach(function(s,i){if(s.classList.contains('a'))cur=i});
  if(!slides.length)return;
  slides[cur].classList.remove('a');if(dots[cur])dots[cur].classList.remove('a');
  cur=(cur+dir+slides.length)%slides.length;
  slides[cur].classList.add('a');if(dots[cur])dots[cur].classList.add('a');
}

function cg(id,idx){
  var cc=document.getElementById('c'+id);if(!cc)return;
  var slides=cc.querySelectorAll('.cs'),dots=cc.querySelectorAll('.cd span');
  slides.forEach(function(s){s.classList.remove('a')});
  dots.forEach(function(d){d.classList.remove('a')});
  slides[idx].classList.add('a');if(dots[idx])dots[idx].classList.add('a');
}

function fs(val){
  var grid=document.querySelector('.grid');if(!grid)return;
  if(val=='__all__'){grid.querySelectorAll('.card').forEach(function(c){c.style.display=''});return}
  grid.querySelectorAll('.card').forEach(function(c){
    var ct=c.querySelector('.ct');
    c.style.display=ct&&ct.textContent.trim()===val?'':'none';
  });
}

function od(id){
  if(!LR_LOADED&&P.length==0){document.getElementById('dco').innerHTML='<div class="loading" style="padding:2rem;text-align:center">Loading details...</div>';document.getElementById('ov').classList.add('a');document.body.style.overflow='hidden';var iv=setInterval(function(){if(LR_LOADED||P.length>0){clearInterval(iv);od2(id)}},200);return}
  od2(id);
}
function od2(id){
  var p=P.find(function(x){return x.id===id});if(!p)return;
  var d=document.getElementById('dco');d.innerHTML='';
  var imgs=p.images||[];
  if(imgs.length){
    d.innerHTML+='<div class="dc-car" id="dc-'+id+'">';
    imgs.forEach(function(img,i){d.innerHTML+='<div class="cs'+(i==0?' a':'')+'" style="background-image:url('+img+')"></div>'});
    if(imgs.length>1){
      d.innerHTML+='<button class="cb" onclick="event.stopPropagation();dm(\\''+id+'\\',-1)">\\u2039</button>';
      d.innerHTML+='<button class="cb n" onclick="event.stopPropagation();dm(\\''+id+'\\',1)">\\u203A</button>';
      d.innerHTML+='<div class="cd">';
      imgs.forEach(function(img,i){d.innerHTML+='<span'+(i==0?' class="a"':'')+' onclick="event.stopPropagation();dg(\\''+id+'\\','+i+')"></span>'});
      d.innerHTML+='</div>';
    }
    d.innerHTML+='</div>';
  }
  d.innerHTML+='<div class="ct">'+p.cat+'</div><h2>'+esc(p.name)+'</h2>';
  if(p.price>0)d.innerHTML+='<div class="pb">$'+p.price+'</div><br>';
  if(p.desc)d.innerHTML+='<div class="ds">'+esc(p.desc)+'</div>';
  document.getElementById('ov').classList.add('a');document.body.style.overflow='hidden';
  if(imgs.length>1){if(window.dt)clearInterval(window.dt);window.dt=setInterval(function(){dm(id,1)},4000)}
}

function dm(id,dir){
  var dc=document.getElementById('dc-'+id);if(!dc)return;
  var slides=dc.querySelectorAll('.cs'),dots=dc.querySelectorAll('.cd span');
  var cur=0;slides.forEach(function(s,i){if(s.classList.contains('a'))cur=i});
  if(!slides.length)return;
  slides[cur].classList.remove('a');if(dots[cur])dots[cur].classList.remove('a');
  cur=(cur+dir+slides.length)%slides.length;
  slides[cur].classList.add('a');if(dots[cur])dots[cur].classList.add('a');
}

function dg(id,idx){
  var dc=document.getElementById('dc-'+id);if(!dc)return;
  var slides=dc.querySelectorAll('.cs'),dots=dc.querySelectorAll('.cd span');
  slides.forEach(function(s){s.classList.remove('a')});
  dots.forEach(function(d){d.classList.remove('a')});
  slides[idx].classList.add('a');if(dots[idx])dots[idx].classList.add('a');
}

function ca(e){if(e&&e.target!==e.currentTarget)return;
  document.getElementById('ov').classList.remove('a');document.body.style.overflow='';
  if(window.dt)clearInterval(window.dt);
}
window.addEventListener('DOMContentLoaded',init);
'''

js = js.replace("PARSED_TABS", tjson)

CSS = """*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,'Inter',sans-serif;background:#f8f7f4;color:#2c2c2c}
.header{background:#1a1a2e;color:#fff;padding:1.2rem 2rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap}
.logo{font-size:1.6rem;font-weight:800} .logo span{color:#e8b86d}
.hero{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:3rem 2rem;text-align:center}
.hero h1{font-size:2.4rem;font-weight:800;margin-bottom:.5rem} .hero h1 span{color:#e8b86d}
.hero p{color:#b0b0c0;max-width:600px;margin:0 auto}
.tab-nav{display:flex;background:#fff;border-bottom:2px solid #e0ddd8;position:sticky;top:0;z-index:10;overflow-x:auto}
.tab-btn{flex:1 0 auto;padding:.9rem 1.2rem;font-weight:600;font-size:.95rem;color:#777;background:none;border:none;cursor:pointer;border-bottom:3px solid transparent;white-space:nowrap;transition:.2s}
.tab-btn:hover{color:#1a1a2e;background:#f8f7f4}
.tab-btn.active{color:#1a1a2e;border-bottom-color:#e8b86d}
.tab-btn .bc{display:inline-block;background:#e8b86d20;color:#1a1a2e;font-size:.7rem;padding:1px 7px;border-radius:10px;margin-left:5px}
.container{max-width:1200px;margin:0 auto;padding:2rem 1.5rem}
.subcat-bar{display:flex;align-items:center;gap:10px;margin-bottom:1rem;flex-wrap:wrap}
.subcat-bar label{font-weight:600;color:#555}
.subcat-select{padding:8px 16px;border:2px solid #ddd;border-radius:8px;font-size:.95rem;font-weight:500;min-width:200px;cursor:pointer}
.subcat-select:focus{outline:none;border-color:#e8b86d}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1.5rem}
.card{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.06);cursor:pointer;color:inherit;text-decoration:none;transition:transform .25s,box-shadow .25s}
.card:hover{transform:translateY(-4px);box-shadow:0 8px 28px rgba(0,0,0,.1)}
.card-body{padding:1rem 1.2rem 1.3rem}
.card-body .ct{font-size:.72rem;color:#e8b86d;font-weight:600;text-transform:uppercase;margin-bottom:2px}
.card-body h3{font-size:.95rem;color:#1a1a2e;line-height:1.3;margin-bottom:2px}
.card-body .pt{font-size:1.1rem;font-weight:700;color:#1a1a2e;margin-top:5px}
.cc{position:relative;width:100%;height:200px;overflow:hidden;background:#e8e3dc}
.cs{position:absolute;top:0;left:0;width:100%;height:100%;background-size:cover;background-position:center;opacity:0;transition:opacity .5s}
.cs.a{opacity:1}
.cb{position:absolute;top:50%;transform:translateY(-50%);background:rgba(0,0,0,.4);color:#fff;border:none;width:30px;height:60px;cursor:pointer;font-size:1.2rem;z-index:2;transition:.2s}
.cb:hover{background:rgba(0,0,0,.7)} .cb.n{right:0}
.cd{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);display:flex;gap:5px;z-index:2}
.cd span{width:8px;height:8px;border-radius:50%;background:rgba(255,255,255,.5);cursor:pointer;transition:.2s}
.cd span.a{background:#e8b86d}
.ov{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.6);z-index:100;justify-content:center;align-items:center;padding:2rem}
.ov.a{display:flex}
.dc{background:#fff;border-radius:16px;max-width:800px;width:100%;max-height:90vh;overflow-y:auto;padding:2rem;position:relative;box-shadow:0 20px 60px rgba(0,0,0,.3)}
.dx{position:absolute;top:1rem;right:1rem;background:none;border:none;font-size:1.5rem;cursor:pointer;color:#888;width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center}
.dx:hover{background:#f0f0f0}
.dc-car{position:relative;width:100%;max-height:400px;overflow:hidden;border-radius:12px;margin-bottom:1.5rem;background:#e8e3dc}
.dc-car .cs{height:400px;background-size:contain;background-repeat:no-repeat}
.dc h2{font-size:1.4rem;color:#1a1a2e;margin-bottom:.5rem}
.dc .ct{font-size:.8rem;color:#e8b86d;font-weight:600;text-transform:uppercase;margin-bottom:.8rem}
.dc .pb{display:inline-block;background:#e8b86d20;color:#1a1a2e;font-weight:700;font-size:1.3rem;padding:8px 24px;border-radius:8px;margin:.5rem 0}
.dc .ds{margin-top:.8rem;white-space:pre-wrap;font-size:.9rem;color:#555;line-height:1.5}
.footer{background:#1a1a2e;color:#888;text-align:center;padding:2rem;margin-top:2rem}
.footer strong{color:#e8b86d}
.ni{width:100%;height:200px;background:#e8e3dc;display:flex;align-items:center;justify-content:center;color:#aaa}
.loading{text-align:center;padding:4rem;color:#888}
@media(max-width:600px){.hero h1{font-size:1.8rem}.tab-btn{padding:.7rem .8rem;font-size:.85rem}.grid{grid-template-columns:1fr}.ov{padding:1rem}.dc{padding:1.5rem}}"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>BunkBedWorld</title>
<style>{CSS}</style>
</head>
<body>
<div class="header"><div class="logo">BunkBed<span>World</span></div><div class="tagline">Furniture for every room</div></div>
<div class="hero"><h1>Your Home, <span>Done Right</span></h1><p>From cozy living rooms to bunk beds — find furniture that fits your space and budget.</p></div>
<nav class="tab-nav" id="tabNav">{tab_buttons_html}</nav>
<div class="container" id="main">{lr_grid_html}</div>
<div class="ov" id="ov" onclick="ca(event)"><div class="dc" onclick="event.stopPropagation()"><button class="dx" onclick="ca()">&#10005;</button><div id="dco"></div></div></div>
<div class="footer"><p><strong>BunkBedWorld</strong> — founded in Chicago, built for your home.</p></div>
<script>{js}</script>
</body>
</html>"""

with open('index.html', 'w') as f:
    f.write(html)
print(f"✅ index.html generated: {len(html)} bytes ({len(html)/1024:.0f} KB)")
print(f"   SSR Living Room grid: {len(lr_grid_html)} bytes")
print(f"   Tab buttons: {len(tab_buttons_html)} bytes")
print(f"   JavaScript: {len(js)} bytes")
print(f"   CSS: {len(CSS)} bytes")

# Validate JS
import subprocess
result = subprocess.run(
    ['node', '-e', f'try{{new Function({repr(js)})}}catch(e){{console.log("JS error:",e.message)}}'],
    capture_output=True, text=True
)
if result.stdout.strip():
    print(f"   {result.stdout.strip()}")
else:
    print("   ✅ JS syntax OK")