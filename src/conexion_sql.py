import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()


def conectar_sql():
    """
    Crea conexión a SQL Server usando variables del archivo .env.
    """

    server = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DATABASE")
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 17 for SQL Server")

    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )

    return pyodbc.connect(conn_str)
