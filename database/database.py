from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL de conexión a la base de datos SQLite.
# El archivo de la base de datos se creará en el mismo directorio que este script,
# con el nombre "predicciones.db".
DATABASE_URL = "sqlite:///./predicciones.db"

# Crea el motor de SQLAlchemy.
# connect_args={"check_same_thread": False} es necesario solo para SQLite
# para permitir que múltiples hilos accedan a la base de datos (común en aplicaciones web).
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Crea una clase SessionLocal. Cada instancia de SessionLocal será una sesión de base de datos.
# La sesión en sí misma no es thread-safe. Debes crear una nueva sesión para cada conjunto de operaciones.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crea una clase Base. Las clases de modelos de SQLAlchemy heredarán de esta clase.
Base = declarative_base()

# Función para crear todas las tablas definidas por los modelos que heredan de Base.
# Esta función se llamará generalmente una vez al inicio de la aplicación.
def init_db():
    # Importa aquí todos los modelos para que sean registrados en Base.metadata
    # antes de que create_all sea llamado.
    # Ejemplo: from . import models
    # No es estrictamente necesario si los modelos ya están importados en el contexto donde Base es definido
    # y Base.metadata.create_all(bind=engine) se llama desde models.py, por ejemplo.
    # Pero es una buena práctica centralizar la creación de tablas.
    from .models import Base # Asegúrate de que tus modelos están definidos y Base es importada desde allí
    Base.metadata.create_all(bind=engine)

# Función generadora para obtener una sesión de base de datos.
# Esto se usará como una dependencia en las rutas de FastAPI (o funciones similares en Flask).
# Asegura que la sesión de la base de datos se cierre correctamente después de su uso.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Si ejecutas este archivo directamente, puedes inicializar la base de datos.
if __name__ == "__main__":
    print("Inicializando la base de datos y creando tablas (si no existen)...")
    # Para que init_db funcione correctamente si se ejecuta desde aquí,
    # asegúrate de que los modelos estén accesibles.
    # Si models.py ya llama a Base.metadata.create_all(), no necesitas llamarlo aquí de nuevo.
    # Sin embargo, si quieres un punto centralizado para la creación de tablas, este es un buen lugar.

    # Dado que models.py ya tiene su propio if __name__ == "__main__": para crear tablas,
    # podríamos simplemente indicar que se ejecute ese archivo o llamar a su función.
    # from .models import crear_tablas # Suponiendo que tienes una función así en models.py
    # crear_tablas()

    # O, si prefieres mantener la lógica de creación aquí:
    # Primero, asegúrate de que models.py (y por lo tanto Base) se ha cargado
    import models # Esto cargará models.py y su Base
    Base.metadata.create_all(bind=engine) # Usa la Base importada
    print("Base de datos inicializada.")
