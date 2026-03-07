import os
import re

def rgba_to_hex(match):
    r, g, b, a = match.groups()
    r = int(r.strip())
    g = int(g.strip())
    b = int(b.strip())
    try:
        a = float(a.strip())
    except ValueError:
        a = 1.0
    a_hex = format(int(round(a * 255)), '02x')
    return f"#{r:02x}{g:02x}{b:02x}{a_hex}"

def walk_and_replace(directory):
    pattern = re.compile(r"rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*([0-9.]+)\s*\)", re.IGNORECASE)
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.css') or file.endswith('.js'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = pattern.sub(rgba_to_hex, content)
                
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Updated {path}")

walk_and_replace(r"c:\Users\Carol Fernandes\Downloads\Adjustle\Frontend\src")
