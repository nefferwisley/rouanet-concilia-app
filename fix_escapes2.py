import os
import glob

for root, dirs, files in os.walk('frontend/src'):
    for file in files:
        if file.endswith('.tsx'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            if r'\${' in content:
                content = content.replace(r'\${', '${')
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
