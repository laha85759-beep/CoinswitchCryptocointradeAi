import time

version_str = f"?v={int(time.time())}"

with open('higgsfield.css', 'r', encoding='utf-8') as f:
    hf_css = f.read()

# Append to styles.css, admin.css, superadmin.css to ensure standard stylesheets include it
for fname in ['styles.css', 'admin.css', 'superadmin.css']:
    with open(fname, 'r', encoding='utf-8') as f:
        content = f.read()
    # Strip previous Higgsfield append if any
    idx = content.find('HIGGSFIELD KINETIC UI SYSTEM OVERLAY')
    if idx != -1:
        # find where that block started
        content = content[:idx-5].rstrip()
    content = content + "\n\n" + hf_css
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated {fname} with latest Higgsfield design system.")

# Now update index.html, admin.html, superadmin.html to also explicitly link <link rel="stylesheet" href="/higgsfield.css{version_str}">
# and update their main css version string to bust any browser/Cloudflare cache!

# 1. index.html
with open('index.html', 'r', encoding='utf-8') as f:
    idx_html = f.read()

import re
# Replace styles.css?v=... with fresh timestamp
idx_html = re.sub(r'href="styles\.css(?:\?[^"]*)?"', f'href="styles.css{version_str}"', idx_html)
if 'higgsfield.css' not in idx_html:
    idx_html = idx_html.replace(
        f'href="styles.css{version_str}" />',
        f'href="styles.css{version_str}" />\n  <link rel="stylesheet" href="/higgsfield.css{version_str}" />'
    )
else:
    idx_html = re.sub(r'href="/higgsfield\.css(?:\?[^"]*)?"', f'href="/higgsfield.css{version_str}"', idx_html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(idx_html)
print("Updated index.html cachebuster and higgsfield.css link.")

# 2. admin.html
with open('admin.html', 'r', encoding='utf-8') as f:
    adm_html = f.read()

adm_html = re.sub(r'href="/admin\.css(?:\?[^"]*)?"', f'href="/admin.css{version_str}"', adm_html)
if 'higgsfield.css' not in adm_html:
    adm_html = adm_html.replace(
        f'href="/admin.css{version_str}">',
        f'href="/admin.css{version_str}">\n  <link rel="stylesheet" href="/higgsfield.css{version_str}">'
    )
else:
    adm_html = re.sub(r'href="/higgsfield\.css(?:\?[^"]*)?"', f'href="/higgsfield.css{version_str}"', adm_html)

with open('admin.html', 'w', encoding='utf-8') as f:
    f.write(adm_html)
print("Updated admin.html cachebuster and higgsfield.css link.")

# 3. superadmin.html
with open('superadmin.html', 'r', encoding='utf-8') as f:
    spr_html = f.read()

spr_html = re.sub(r'href="/superadmin\.css(?:\?[^"]*)?"', f'href="/superadmin.css{version_str}"', spr_html)
if 'higgsfield.css' not in spr_html:
    spr_html = spr_html.replace(
        f'href="/superadmin.css{version_str}">',
        f'href="/superadmin.css{version_str}">\n  <link rel="stylesheet" href="/higgsfield.css{version_str}">'
    )
else:
    spr_html = re.sub(r'href="/higgsfield\.css(?:\?[^"]*)?"', f'href="/higgsfield.css{version_str}"', spr_html)

with open('superadmin.html', 'w', encoding='utf-8') as f:
    f.write(spr_html)
print("Updated superadmin.html cachebuster and higgsfield.css link.")
