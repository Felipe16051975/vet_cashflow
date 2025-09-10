import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Day, Entry, CatalogItem

# Rutas de las bases
SQLITE_URL = "sqlite:///instance/app.db"
POSTGRES_URL = os.getenv("DATABASE_URL")  # Ejemplo: "postgresql://usuario:clave@host:puerto/db"

# Engines y sesiones
sqlite_engine = create_engine(SQLITE_URL)
postgres_engine = create_engine(POSTGRES_URL)

SqliteSession = sessionmaker(bind=sqlite_engine)
PostgresSession = sessionmaker(bind=postgres_engine)

sqlite_session = SqliteSession()
postgres_session = PostgresSession()

def migrate_model(model):
    print(f"Migrando {model.__name__}...")
    rows = sqlite_session.query(model).all()
    for row in rows:
        data = {c.name: getattr(row, c.name) for c in model.__table__.columns}
        obj = model(**data)
        postgres_session.add(obj)
    postgres_session.commit()
    print(f"Listo: {len(rows)} registros migrados.")

if __name__ == "__main__":
    # Migrar en orden correcto
    migrate_model(Day)
    migrate_model(CatalogItem)
    migrate_model(Entry)
    print("¡Migración completa!")
