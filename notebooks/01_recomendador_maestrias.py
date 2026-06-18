# %%
import sys
from pathlib import Path
import re

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
    cargar_graduados_sql,
    preparar_graduados_pregrado_y_posgrado,
    obtener_laboral_sql,
    obtener_laboral_linkedin_sql,
    cruzar_graduados_laboral,
    obtener_catalogo_udla,
    preparar_catalogo_maestrias,
    generar_recomendaciones,
    cargar_resultado_bdd_idm,
    TABLA_RESULTADO_BDD
)

# %%
RUTA_SALIDA = BASE_DIR / "outputs" / "recomendaciones_maestrias_udla.xlsx"

print("Ruta base:", BASE_DIR)
print("Ruta salida:", RUTA_SALIDA)
print("Tabla destino:", TABLA_RESULTADO_BDD)

# %%
def limpiar_caracteres_excel(valor):
    if isinstance(valor, str):
        return re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]", "", valor)

    return valor


def limpiar_dataframe_excel(df):
    df_limpio = df.copy()

    for col in df_limpio.columns:
        if df_limpio[col].dtype == "object":
            df_limpio[col] = df_limpio[col].apply(limpiar_caracteres_excel)

    return df_limpio


def exportar_hoja_segura(writer, df, sheet_name):
    df_limpio = limpiar_dataframe_excel(df)
    df_limpio.to_excel(writer, sheet_name=sheet_name, index=False)


# %%
conn = conectar_sql()

print("Conexión SQL exitosa")

# %%
graduados_total = cargar_graduados_sql(conn)

print("Filas Vw_Graduados:", len(graduados_total))
display(graduados_total.head())

# %%
graduados_pregrado, graduados_posgrado = preparar_graduados_pregrado_y_posgrado(
    graduados_total
)

print("Filas pregrado:", len(graduados_pregrado))
print("Filas posgrado:", len(graduados_posgrado))
print(
    "Personas con posgrado UDLA previo:",
    (graduados_pregrado["YaEstudioPosgradoUDLA"] == "Sí").sum()
)

columnas_preview_graduados = [
    "Identificador",
    "Estudiante",
    "CarreraHom",
    "Titulo",
    "FechaGraduacion",
    "RestriccionAcademica",
    "YaEstudioPosgradoUDLA",
    "PosgradosUDLAPrevios"
]

columnas_preview_graduados = [
    c for c in columnas_preview_graduados
    if c in graduados_pregrado.columns
]

display(graduados_pregrado[columnas_preview_graduados].head(20))

# %%
laboral = obtener_laboral_sql(
    conn=conn,
    identificadores=graduados_pregrado["Identificador"]
)

print("Filas laborales SIM encontradas:", len(laboral))
display(laboral.head())

# %%
laboral_linkedin = obtener_laboral_linkedin_sql(
    conn=conn,
    identificadores=graduados_pregrado["Identificador"]
)

print("Filas laborales LinkedIn encontradas:", len(laboral_linkedin))
display(laboral_linkedin.head())

# %%
base = cruzar_graduados_laboral(
    graduados_pregrado=graduados_pregrado,
    laboral=laboral,
    laboral_linkedin=laboral_linkedin
)

print("Filas base final:", len(base))
print(base["TieneInformacionLaboral"].value_counts(dropna=False))
print(base["FuenteInformacionLaboral"].value_counts(dropna=False))

columnas_preview = [
    "Identificador",
    "Estudiante",
    "CarreraHom",
    "Titulo",
    "FechaGraduacion",
    "TieneInformacionLaboral",
    "FuenteInformacionLaboral",
    "NOMEMP",
    "TIPOEMPRES",
    "OCUPAFI",
    "AniosDesdeGraduacion",
    "AniosEnCargo",
    "RestriccionAcademica",
    "YaEstudioPosgradoUDLA",
    "PosgradosUDLAPrevios"
]

columnas_preview = [c for c in columnas_preview if c in base.columns]

display(base[columnas_preview].head(20))

# %%
catalogo = obtener_catalogo_udla(conn)

print("Filas catálogo:", len(catalogo))
display(catalogo.head())

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
    "FuenteInformacionLaboral",
    "YaEstudioPosgradoUDLA",
    "PosgradosUDLAPrevios",
    "RestriccionAcademica",
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
filas_cargadas = cargar_resultado_bdd_idm(
    conn=conn,
    top3=top3
)

print(f"Tabla cargada en {TABLA_RESULTADO_BDD}")
print(f"Filas cargadas: {filas_cargadas}")

# %%
RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)

with pd.ExcelWriter(RUTA_SALIDA, engine="openpyxl") as writer:
    exportar_hoja_segura(writer, graduados_total, "Vw_Graduados")
    exportar_hoja_segura(writer, graduados_pregrado, "Graduados_pregrado")
    exportar_hoja_segura(writer, graduados_posgrado, "Graduados_posgrado")
    exportar_hoja_segura(writer, laboral, "Laboral_SIM")
    exportar_hoja_segura(writer, laboral_linkedin, "Laboral_LinkedIn")
    exportar_hoja_segura(writer, base, "Base_graduados_laboral")
    exportar_hoja_segura(writer, maestrias, "Catalogo_maestrias")
    exportar_hoja_segura(writer, catalogo_lineas, "Lineas_catalogo")
    exportar_hoja_segura(writer, recomendaciones_larga, "Recomendaciones_larga")
    exportar_hoja_segura(writer, top3, "Top3_por_graduado")

print("Archivo exportado en:")
print(RUTA_SALIDA)
