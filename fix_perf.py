#!/usr/bin/env python3
"""Server-side render the Living Room tab for instant loading."""
with open('rebuild_scraper.py', 'r') as f:
    content = f.read()

# Step 1: Replace the no-script placeholder with SSR content
# The current code has: <div class="container" id="main"><div class="loading">Loading products...</div></div>
# We'll replace this with: a call to embed the pre-rendered grid

old = """<nav class="tab-nav" id="tabNav"></nav>
<div class="container" id="main"><div class="loading">Loading products...</div></div>"""

new = """<nav class="tab-nav" id="tabNav">{%TABS_HTML%}</nav>
<div class="container" id="main">{%LR_GRID%}</div>"""

if old in content:
    content = content.replace(old, new)
    print("✅ Replaced loading placeholder with SSR markers")
else:
    print("❌ Could not find old placeholder")

# Step 2: Update the JS - remove fetch, add on-demand loading for other tabs
old_js = """<script>
var P=[],T={tjson};
var ct=null,cn=null,ci={{} };

fetch('/products.json').then(function(r){{return r.json()}}).then(function(d){{P=d;init();}}).catch(function(){{document.getElementById('main').innerHTML='<div class="loading">Failed to load products.</div>'}});

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
}}"""

# Wait, there are spaces between the braces. Let me check the actual content
import re
# Find the start of script section
script_start = content.find('<script>')
script_content = content[script_start:script_start+1200]
print(f"\nScript start (first 500 chars): {repr(script_content[:500])}")