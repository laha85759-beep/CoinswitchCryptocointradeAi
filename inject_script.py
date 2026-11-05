with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

target = '<script src="app.js'
tag = '<script defer src="agent_3d_workforce.js?v=20261026-1"></script>\n  '

if "agent_3d_workforce.js" not in html and target in html:
    html = html.replace(target, tag + target)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Script tag inserted into index.html successfully")
else:
    print("Already inserted or target not found")
