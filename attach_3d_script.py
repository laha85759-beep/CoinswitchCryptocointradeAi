path = 'c:/Users/karth/Downloads/CoinswitchCryptocointradeAi-main/CoinswitchCryptocointradeAi-main/index.html'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

target = '<script defer src="agent_3d_workforce.js'
replacement = '<script defer src="universe_3d_engine.js?v=3d-2026"></script>\n  <script defer src="agent_3d_workforce.js'

if target in text:
    text = text.replace(target, replacement, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("universe_3d_engine.js attached to index.html successfully!")
else:
    print("Target already present or not found")
