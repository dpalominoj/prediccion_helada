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
    # Se importa Base desde el módulo models en el mismo paquete (directorio)
    from . import models
    models.Base.metadata.create_all(bind=engine)

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
# Esto es útil para la configuración inicial o pruebas.
if __name__ == "__main__":
    print("Inicializando la base de datos y creando tablas (si no existen)...")
    # Llama a init_db para asegurar que las tablas se creen usando la lógica centralizada.
    # init_db() ya se encarga de importar models y llamar a Base.metadata.create_all(bind=engine).
    init_db()
    print("Base de datos inicializada.")
