#!/usr/bin/env python3
"""Add server-side rendering for instant first-view loading."""
with open('rebuild_scraper.py', 'r') as f:
    content = f.read()

import re

# 1️⃣ Add a helper function before generate_html that renders a product grid HTML
helper = r'''
def _render_grid_html(products, cat_names, tab_name):
    """Render the product grid HTML for a set of categories (server-side)."""
    fp = [p for p in products if p.get("cat") in cat_names]
    fp.sort(key=lambda p: p.get("price", 999999))
    
    def esc(s):
        if not s: return ''
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;').replace('\n', '<br>')
    
    def jq(s):
        return json.dumps(s)
    
    h = '<div class="subcat-bar"><label>Filter:</label>'
    h += '<select class="subcat-select" onchange="fs(this.value)">'
    h += '<option value="__all__">All ' + tab_name + '</option>'
    for i, cn in enumerate(cat_names):
        h += '<option value="c' + str(i+1) + '">' + cn + ' (' + str(sum(1 for p in fp if p.get("cat") == cn)) + ')</option>'
    h += '</select></div><div class="grid">'
    
    for p in fp:
        imgs = p.get("images") or []
        pid = p["id"]
        h += '<a class="card" onclick="event.preventDefault();od(' + "'" + pid + "'" + ')">'
        if len(imgs) == 0:
            h += '<div class="ni">No Image</div>'
        elif len(imgs) == 1:
            h += '<div class="cc"><div class="cs a" style="background-image:url(' + imgs[0].replace("'", "%27") + ')"></div></div>'
        else:
            h += '<div class="cc" id="c' + pid + '">'
            for i, img in enumerate(imgs):
                h += '<div class="cs' + (' a' if i == 0 else '') + '" style="background-image:url(' + img.replace("'", "%27") + ')"></div>'
            h += '<button class="cb" onclick="event.stopPropagation();cm(' + "'" + pid + "'" + ',-1)">\u2039</button>'
            h += '<button class="cb n" onclick="event.stopPropagation();cm(' + "'" + pid + "'" + ',1)">\u203A</button>'
            h += '<div class="cd">'
            for i in range(len(imgs)):
                h += '<span' + (' class="a"' if i == 0 else '') + ' onclick="event.stopPropagation();cg(' + "'" + pid + "'," + str(i) + ')"></span>'
            h += '</div></div>'
        h += '<div class="card-body"><div class="ct">' + esc(p.get("cat", "")) + '</div><h3>' + esc(p.get("name", "")) + '</h3><div class="pt">$' + str(p.get("price", 0)) + '</div></div></a>'
    h += '</div>'
    return h


'''

# Insert after the compute tabs section
insert_after = "    all_products = []\n    for p in products:\n        if \"cat\" in p and \"price\" in p:\n"
if insert_after in content:
    content = content.replace(insert_after, helper + "\n" + insert_after)
    print("✅ Helpers inserted")
else:
    print("❌ Cannot find insertion point")

# 2️⃣ Replace the tab nav and loading placeholder with SSR content
old_body = """<nav class="tab-nav" id="tabNav"></nav>
<div class="container" id="main"><div class="loading">Loading products...</div></div>"""

new_body = """<nav class="tab-nav" id="tabNav">{%TABS_HTML%}</nav>
<div class="container" id="main">{%LR_GRID%}</div>"""

if old_body not in content:
    print("❌ Can't find old body section to replace")
    # Try to find what's actually there
    idx = content.find('nav class="tab-nav"')
    print(f"  Found at index {idx}: {repr(content[idx:idx+100])}")
else:
    content = content.replace(old_body, new_body)
    print("✅ Body section replaced with SSR markers")

# 3️⃣ Write the modified file
with open('rebuild_scraper.py', 'w') as f:
    f.write(content)
print("Done")