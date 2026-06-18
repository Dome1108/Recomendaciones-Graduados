# %%
import sys
from pathlib import Path

import pandas as pd
import numpy as np

try:
    from IPython.display import display
except ImportError:
    def display(x):
        print(x)

BASE_DIR = Path.cwd()
SRC_DIR = BASE_DIR / "src"

if not SRC_DIR.exists():
    BASE_DIR = Path.cwd().parent
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
RUTA_GRADUADOS = BASE_DIR / "data" / "graduados.xlsx"
RUTA_SALIDA = BASE_DIR / "outputs" / "recomendaciones_maestrias_udla.xlsx"

print("Ruta base:", BASE_DIR)
print("Ruta graduados:", RUTA_GRADUADOS)
print("Ruta salida:", RUTA_SALIDA)

# %%
graduados = cargar_graduados(RUTA_GRADUADOS)

print("Filas graduados:", len(graduados))
display(graduados.head())

# %%
print("Columnas graduados:")
print(graduados.columns.tolist())

# %%
conn = conectar_sql()

print("Conexión SQL exitosa")

# %%
laboral = obtener_laboral_sql(
    conn=conn,
    identificadores=graduados["Identificador"]
)

print("Filas laborales encontradas:", len(laboral))
display(laboral.head())

# %%
base = cruzar_graduados_laboral(
    graduados=graduados,
    laboral=laboral
)

print("Filas base final:", len(base))
print(base["TieneInformacionLaboral"].value_counts(dropna=False))

columnas_preview = [
    "Identificador",
    "Estudiante",
    "CarreraHom",
    "Titulo",
    "FechaGraduacion",
    "TieneInformacionLaboral",
    "NOMEMP",
    "TIPOEMPRES",
    "OCUPAFI",
    "FECINGAFI",
    "AniosDesdeGraduacion",
    "AniosEnCargo"
]

columnas_preview = [c for c in columnas_preview if c in base.columns]

display(base[columnas_preview].head(20))

# %%
catalogo = obtener_catalogo_udla(conn)

print("Filas catálogo:", len(catalogo))
display(catalogo.head())

# %%
print("Columnas catálogo:")
print(catalogo.columns.tolist())

# %%
maestrias, catalogo_lineas = preparar_catalogo_maestrias(catalogo)

print("Maestrías detectadas:", len(maestrias))
display(catalogo_lineas.head(80))

# %%
resumen_lineas = (
    catalogo_lineas["LineaMaestria"]
    .value_counts()
    .reset_index()
)

resumen_lineas.columns = ["LineaMaestria", "Cantidad"]

display(resumen_lineas)

# %%
recomendaciones_larga, top3 = generar_recomendaciones(
    base=base,
    catalogo_lineas=catalogo_lineas
)

print("Filas recomendaciones largas:", len(recomendaciones_larga))
print("Filas Top 3:", len(top3))

display(top3.head(20))

# %%
columnas_validacion = [
    "Identificador",
    "Estudiante",
    "CarreraHom",
    "Titulo",
    "TieneInformacionLaboral",
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

display(top3[columnas_validacion].head(30))

# %%
RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)

with pd.ExcelWriter(RUTA_SALIDA, engine="openpyxl") as writer:
    base.to_excel(writer, sheet_name="Base_graduados_laboral", index=False)
    maestrias.to_excel(writer, sheet_name="Catalogo_maestrias", index=False)
    catalogo_lineas.to_excel(writer, sheet_name="Lineas_catalogo", index=False)
    recomendaciones_larga.to_excel(writer, sheet_name="Recomendaciones_larga", index=False)
    top3.to_excel(writer, sheet_name="Top3_por_graduado", index=False)

print("Archivo exportado en:")
print(RUTA_SALIDA)
