# %%
import sys
from pathlib import Path

import pandas as pd
import numpy as np

# Agregar carpeta src al path
BASE_DIR = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
SRC_DIR = BASE_DIR / "src"

sys.path.append(str(SRC_DIR))

from conexion_sql import conectar_sql
from pipeline_recomendaciones import (
    cargar_graduados,
    obtener_laboral_sql,
    cruzar_graduados_laboral,
    obtener_catalogo_udla,
    preparar_catalogo_maestrias,
    generar_recomendaciones
)

# %%
# Rutas del proyecto

RUTA_GRADUADOS = BASE_DIR / "data" / "graduados.xlsx"
RUTA_SALIDA = BASE_DIR / "outputs" / "recomendaciones_maestrias_udla.xlsx"

print("Ruta base:", BASE_DIR)
print("Ruta graduados:", RUTA_GRADUADOS)
print("Ruta salida:", RUTA_SALIDA)

# %%
# Cargar Excel de graduados

graduados = cargar_graduados(RUTA_GRADUADOS)

print("Filas graduados:", len(graduados))
display(graduados.head())

# %%
# Revisar columnas disponibles

graduados.columns.tolist()

# %%
# Conectar a SQL Server

conn = conectar_sql()

print("Conexión exitosa")

# %%
# Obtener información laboral desde SIM_Y_ENE_26

laboral = obtener_laboral_sql(
    conn=conn,
    identificadores=graduados["Identificador"]
)

print("Filas laborales encontradas:", len(laboral))
display(laboral.head())

# %%
# Cruzar graduados con información laboral

base = cruzar_graduados_laboral(
    graduados=graduados,
    laboral=laboral
)

print("Filas base final:", len(base))

display(
    base[
        [
            "Identificador",
            "Estudiante",
            "CarreraHom",
            "Titulo",
            "FechaGraduacion",
            "NOMEMP",
            "TIPOEMPRES",
            "OCUPAFI",
            "FECINGAFI",
            "AniosDesdeGraduacion",
            "AniosEnCargo"
        ]
    ].head()
)

# %%
# Obtener catálogo UDLA desde SQL

catalogo = obtener_catalogo_udla(conn)

print("Filas catálogo:", len(catalogo))
display(catalogo.head())

# %%
# Revisar columnas del catálogo

catalogo.columns.tolist()

# %%
# Preparar catálogo de maestrías
# Si detecta mal la columna del programa, luego la ajustamos manualmente.

maestrias, catalogo_lineas = preparar_catalogo_maestrias(catalogo)

print("Maestrías detectadas:", len(maestrias))
display(catalogo_lineas.head(50))

# %%
# Validar distribución de líneas de maestría

display(
    catalogo_lineas["LineaMaestria"]
    .value_counts()
    .reset_index()
    .rename(columns={"index": "LineaMaestria", "LineaMaestria": "Cantidad"})
)

# %%
# Generar recomendaciones

recomendaciones_larga, top3 = generar_recomendaciones(
    base=base,
    catalogo_lineas=catalogo_lineas
)

print("Filas recomendaciones largas:", len(recomendaciones_larga))
print("Filas Top 3:", len(top3))

display(top3.head())

# %%
# Validación rápida de casos

columnas_validacion = [
    "Identificador",
    "Estudiante",
    "CarreraHom",
    "Titulo",
    "NOMEMP",
    "TIPOEMPRES",
    "OCUPAFI",
    "AniosEnCargo",
    "AniosDesdeGraduacion",
    "Recomendacion_1",
    "Score_1",
    "Programas_UDLA_1",
    "Recomendacion_2",
    "Score_2",
    "Programas_UDLA_2",
    "Recomendacion_3",
    "Score_3",
    "Programas_UDLA_3",
    "Justificacion_Recomendacion_1"
]

columnas_validacion = [c for c in columnas_validacion if c in top3.columns]

display(top3[columnas_validacion].head(20))

# %%
# Exportar resultados a Excel

RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)

with pd.ExcelWriter(RUTA_SALIDA, engine="openpyxl") as writer:
    base.to_excel(writer, sheet_name="Base_graduados_laboral", index=False)
    maestrias.to_excel(writer, sheet_name="Catalogo_maestrias", index=False)
    catalogo_lineas.to_excel(writer, sheet_name="Lineas_catalogo", index=False)
    recomendaciones_larga.to_excel(writer, sheet_name="Recomendaciones_larga", index=False)
    top3.to_excel(writer, sheet_name="Top3_por_graduado", index=False)

print("Archivo exportado en:")
print(RUTA_SALIDA)
