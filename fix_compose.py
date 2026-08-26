import re

with open('docker-compose.yml', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace DATABASE_URL with the internal docker network URL
text = text.replace(
    'DATABASE_URL: ""',
    'DATABASE_URL: "postgresql://rouanet:@postgres:5432/rouanet_concilia"'
)

with open('docker-compose.yml', 'w', encoding='utf-8') as f:
    f.write(text)
