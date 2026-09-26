#!/usr/bin/env python3
"""Fix the JS escape bug in rebuild_scraper.py's generate_html function."""
with open('rebuild_scraper.py', 'r') as f:
    content = f.read()

# The bug: inside triple-quoted f-string, \' is consumed to just '
# We need \\' to produce \' in the output JavaScript
# The fix: replace the broken pattern with correct escaping

# Line with the bug:
#   h+='<a class="card" onclick="event.preventDefault();od(\''+p.id+'\')">';
# Needs to become:
#   h+='<a class="card" onclick="event.preventDefault();od(\\''+p.id+'\\')">';

old = "od(\\'"
new = "od(\\\\'"
count = content.count(old)
print(f"Found {count} instances of '{old}' -> replacing with '{new}'")
content = content.replace(old, new)

with open('rebuild_scraper.py', 'w') as f:
    f.write(content)
print("Done. Verify:")