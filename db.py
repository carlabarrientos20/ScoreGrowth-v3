"""
Conexiones a bases de datos para el proyecto Score Growth.

Dos fuentes:
  - Redshift (datalake): venta, CVR. Usa run_query().
  - Postgres (eiffel-ledger): sponsored products. Usa run_query_pg().

Requiere:
  - VPN de Cencosud activa.
  - Un archivo .env en la carpeta con las credenciales de ambas bases.

Cada query abre su propia conexion y la cierra al terminar. Si la conexion
falla por un corte de red (VPN, Wi-Fi, DNS), se reintenta hasta REINTENTOS
veces antes de rendirse. Los errores de SQL (query mal escrita) NO se
reintentan: fallan altiro para que se vean.

"""

import os
import time
import warnings

import redshift_connector
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# pandas avisa que solo prueba oficialmente con SQLAlchemy. Con redshift_connector
# y psycopg2 funciona bien, asi que se silencia para que no ensucie la consola.
warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")

REINTENTOS = 3            # intentos totales por query
ESPERAS_SEG = [10, 30]    # segundos de espera antes del 2do y del 3er intento

# Errores de red / conexion (no de SQL). ProgrammingError (SQL invalido) no esta aca.
ERRORES_CONEXION = (
    redshift_connector.InterfaceError,
    redshift_connector.OperationalError,
    psycopg2.InterfaceError,
    psycopg2.OperationalError,
)


def _es_error_de_conexion(e: Exception) -> bool:
    """True si el error, o el error original que pandas envolvio, es de red/conexion."""
    for _ in range(5):   # pandas envuelve el error original; se revisa la cadena
        if e is None:
            return False
        if isinstance(e, ERRORES_CONEXION):
            return True
        e = e.__cause__ or e.__context__
    return False


def _ejecutar_con_reintentos(abrir_conexion, sql: str, fuente: str) -> pd.DataFrame:
    for intento in range(1, REINTENTOS + 1):
        try:
            conn = abrir_conexion()
            try:
                return pd.read_sql(sql, conn)
            finally:
                try:
                    conn.close()
                except Exception:
                    pass   # si la conexion ya se corto, cerrarla tambien falla; da igual
        except Exception as e:
            if not _es_error_de_conexion(e) or intento == REINTENTOS:
                raise
            espera = ESPERAS_SEG[min(intento - 1, len(ESPERAS_SEG) - 1)]
            print(f"  [{fuente}] Error de conexion (intento {intento}/{REINTENTOS}): "
                  f"{type(e).__name__}. Reintentando en {espera}s... "
                  f"(revisa que la VPN siga conectada)")
            time.sleep(espera)


def get_connection():
    """Abre una conexion a Redshift."""
    return redshift_connector.connect(
        host=os.getenv("REDSHIFT_HOST"),
        port=int(os.getenv("REDSHIFT_PORT", 5439)),
        database=os.getenv("REDSHIFT_DB"),
        user=os.getenv("REDSHIFT_USER"),
        password=os.getenv("REDSHIFT_PASSWORD"),
    )


def run_query(sql: str) -> pd.DataFrame:
    """Ejecuta una consulta en Redshift y devuelve un DataFrame."""
    return _ejecutar_con_reintentos(get_connection, sql, "Redshift")


def get_connection_pg():
    """Abre una conexion a Postgres (eiffel-ledger)."""
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=int(os.getenv("PG_PORT", 5432)),
        dbname=os.getenv("PG_DB"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
    )


def run_query_pg(sql: str) -> pd.DataFrame:
    """Ejecuta una consulta en Postgres y devuelve un DataFrame."""
    return _ejecutar_con_reintentos(get_connection_pg, sql, "Postgres")


if __name__ == "__main__":
    print("Redshift:")
    print(run_query("SELECT CURRENT_DATE AS hoy"))
    print("\nPostgres:")
    print(run_query_pg("SELECT CURRENT_DATE AS hoy"))
