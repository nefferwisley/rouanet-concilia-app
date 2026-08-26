import psycopg2
from backend.config import settings
conn = psycopg2.connect(settings.database_url)
cursor = conn.cursor()
cursor.execute("SELECT id, pronac, nome FROM projetos;")
for row in cursor.fetchall():
    print(row)
