#!/usr/bin/env python3
"""Fix JS escape in rebuild_scraper.py - replace \' with \\' in the f-string template."""
with open('rebuild_scraper.py', 'r') as f:
    content = f.read()

# In the f-string template, \' is consumed by Python to just '
# We need \\' to produce \' in the output JavaScript
# Fix: replace ALL \' instances inside the HTML template with \\'

# Count instances of \' in the template region
import re
# Find the generate_html return string
start = content.find("return f'''")
if start == -1:
    print("Could not find template")
    exit(1)
end = content.find("'''", start + 11) + 3
template = content[start:end]

# Find all \' patterns - they're inside a triple-quoted f-string
# Replace \' with \\'
count_before = template.count("\\'")
print(f"Found {count_before} \\' patterns in template")

# Use regex to replace but only inside the template
# Actually, just do simple replace on the whole content
old = "\\'"
new = "\\\\'"
# But only replace in the f-string part, not the Python function code
full_old = old
full_new = new
total = content.count(full_old)
inside_template = template.count(full_old)
print(f"Total in file: {total}, inside template: {inside_template}")

# Replace only inside the template section
content = content[:start] + template.replace(full_old, full_new) + content[end:]

with open('rebuild_scraper.py', 'w') as f:
    f.write(content)

# Verify
with open('rebuild_scraper.py', 'r') as f:
    content = f.read()
    
for i, line in enumerate(content.split('\n')):
    if 'od(' in line and 'p.id' in line and 'card' in line:
        print(f'Fixed line {i+1}:')
        # Show what JS this produces
        # \' in file should now be \\' which f-string renders as \'
        print(f'  Python source: {repr(line.strip())}')
        # Simulate what f-string would output
        # \\' in Python source outputs \' (backslash then quote)
        print(f'  JS output:     h+=\\' + line.split("h+=")[1].replace("\\\\'", "\'").replace("\\'", "\'") if "h+=" in line else line)