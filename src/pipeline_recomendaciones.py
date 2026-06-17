import pandas as pd
import numpy as np

from utils_texto import normalizar_texto
from recomendador import recomendar_lineas, generar_justificacion


def cargar_graduados(ruta_excel):
    """
    Carga la base de graduados desde Excel y estandariza nombres de columnas.
    """

    graduados = pd.read_excel(ruta_excel)

    graduados.columns = (
        graduados.columns
        .astype(str)
        .str.strip()
        .str.replace("\ufeff", "", regex=False)
    )

    # Estandarizar nombres de columnas del Excel
    mapa_columnas = {
        "IdentificacionBanner": "Identificador",
        "CarreraHomologada": "CarreraHom",
        "desfacultad": "desfacultad",
        "Titulo": "Titulo",
        "FechaGraduacion": "FechaGraduacion",
        "Estudiante": "Estudiante",
        "MailUDLA": "MailUDLA",
        "Genero": "Genero",
        "Modalidad": "Modalidad",
        "Semestre": "Semestre",
        "regimen": "regimen"
    }

    graduados = graduados.rename(columns=mapa_columnas)

    if "Identificador" not in graduados.columns:
        raise ValueError(
            "No se encontró la columna de identificador. "
            f"Columnas disponibles: {graduados.columns.tolist()}"
        )

    graduados["Identificador"] = (
        graduados["Identificador"]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )

    return graduados
