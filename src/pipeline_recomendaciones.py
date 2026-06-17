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


def obtener_laboral_sql(conn, identificadores):
    """
    Consulta información laboral desde SIM_Y_ENE_26 para los identificadores del Excel.
    """

    ids = (
        pd.Series(identificadores)
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    cursor = conn.cursor()

    cursor.execute("""
    IF OBJECT_ID('tempdb..#ids_graduados') IS NOT NULL
        DROP TABLE #ids_graduados;

    CREATE TABLE #ids_graduados (
        NUMAFI VARCHAR(30)
    );
    """)

    cursor.fast_executemany = True

    cursor.executemany(
        "INSERT INTO #ids_graduados (NUMAFI) VALUES (?)",
        [(i,) for i in ids]
    )

    conn.commit()

    query = """
SELECT 
    s.NUMAFI,
    s.APENOMAFI,
    s.TIPOEMPRES,
    s.NOMEMP,
    s.OCUAFI AS OCUPAFI,
    s.SALARIO,
    s.FECINGAFI,
    s.ANIO,
    s.MES
FROM [Reportes].[dbo].[SIM_Y_ENE_26] s
INNER JOIN #ids_graduados i
    ON CAST(s.NUMAFI AS VARCHAR(30)) COLLATE SQL_Latin1_General_CP1_CI_AI
     = i.NUMAFI COLLATE SQL_Latin1_General_CP1_CI_AI;
"""

    laboral = pd.read_sql(query, conn)

    if laboral.empty:
        return laboral

    laboral["NUMAFI"] = laboral["NUMAFI"].astype(str).str.strip()

    laboral["FECINGAFI"] = pd.to_datetime(
        laboral["FECINGAFI"],
        errors="coerce",
        dayfirst=True
    )

    laboral = laboral.sort_values(
        by=["NUMAFI", "ANIO", "MES", "FECINGAFI"],
        ascending=[True, True, True, True]
    )

    laboral_unico = laboral.drop_duplicates(
        subset=["NUMAFI"],
        keep="last"
    )

    return laboral_unico


def cruzar_graduados_laboral(graduados, laboral):
    """
    Cruza Excel de graduados con información laboral de SQL.
    """

    base = graduados.merge(
        laboral,
        left_on="Identificador",
        right_on="NUMAFI",
        how="left"
    )

    hoy = pd.Timestamp.today().normalize()

    base["FechaGraduacion"] = pd.to_datetime(
        base["FechaGraduacion"],
        errors="coerce",
        dayfirst=True
    )

    base["FECINGAFI"] = pd.to_datetime(
        base["FECINGAFI"],
        errors="coerce",
        dayfirst=True
    )

    base["AniosDesdeGraduacion"] = (
        (hoy - base["FechaGraduacion"]).dt.days / 365.25
    ).round(1)

    base["AniosEnCargo"] = (
        (hoy - base["FECINGAFI"]).dt.days / 365.25
    ).round(1)

    return base


def obtener_catalogo_udla(conn):
    """
    Consulta catálogo completo de carreras UDLA.
    """

    query = """
    SELECT *
    FROM DwhOperacional..Vw_CarreraFacultadArea_new;
    """

    catalogo = pd.read_sql(query, conn)

    return catalogo


def detectar_columna_programa(catalogo):
    """
    Intenta detectar la columna donde está el nombre del programa.
    """

    posibles_columnas = [
        "CarreraHom",
        "CARRERAHOM",
        "Carrera",
        "CARRERA",
        "NombreCarrera",
        "NOMBRECARRERA",
        "Programa",
        "PROGRAMA",
        "Descripcion",
        "DESCRIPCION"
    ]

    for col in posibles_columnas:
        if col in catalogo.columns:
            return col

    raise ValueError(
        "No se pudo detectar la columna del programa. "
        f"Columnas disponibles: {catalogo.columns.tolist()}"
    )


def asignar_linea_programa(nombre_programa):
    """
    Clasifica cada maestría en una línea de recomendación.
    """

    txt = normalizar_texto(nombre_programa)

    if any(p in txt for p in ["FINANZ", "BANCA", "FINANCI", "RIESGO", "TRIBUT", "MERCADO DE VALORES"]):
        return "FINANZAS_BANCA"

    if any(p in txt for p in ["DATA", "DATOS", "ANALYTICS", "ANALITICA", "BIG DATA", "CIENCIA DE DATOS", "INTELIGENCIA ARTIFICIAL"]):
        return "ANALITICA_DATOS"

    if any(p in txt for p in ["MBA", "ADMINISTR", "DIRECCION", "GERENCIA", "NEGOCIOS", "EMPRESA"]):
        return "MBA_ADMINISTRACION"

    if "PROYECT" in txt:
        return "GESTION_PROYECTOS"

    if any(p in txt for p in ["MARKETING", "COMERCIAL", "VENTAS", "MERCAD"]):
        return "MARKETING_COMERCIAL"

    if any(p in txt for p in ["DERECHO", "LEGAL", "JURID", "COMPLIANCE", "CONSTITUCIONAL"]):
        return "DERECHO_LEGAL"

    if any(p in txt for p in ["SALUD", "HOSPITAL", "CLINIC", "SANIT", "MEDIC", "EPIDEM"]):
        return "SALUD_GESTION"

    if any(p in txt for p in ["EDUC", "DOCENC", "PEDAGOG", "ENSEN", "ENSEÑ"]):
        return "EDUCACION"

    if any(p in txt for p in ["SOFTWARE", "SISTEMAS", "INFORMAT", "CIBER", "TECNOLOG", "TRANSFORMACION DIGITAL"]):
        return "TECNOLOGIA"

    if any(p in txt for p in ["PSICO", "TALENTO", "RECURSOS HUMANOS", "HUMANO"]):
        return "PSICOLOGIA_RRHH"

    if any(p in txt for p in ["ARQUIT", "DISENO", "DISEÑO", "URBAN"]):
        return "ARQUITECTURA_DISENO"

    return "OTRAS"


def preparar_catalogo_maestrias(catalogo, col_programa=None):
    """
    Filtra programas de maestría y asigna línea de recomendación.
    """

    catalogo_txt = catalogo.copy()

    for col in catalogo_txt.columns:
        if catalogo_txt[col].dtype == "object":
            catalogo_txt[col] = catalogo_txt[col].apply(normalizar_texto)

    columnas_texto = catalogo_txt.select_dtypes(include="object").columns

    mask_maestria = catalogo_txt[columnas_texto].apply(
        lambda fila: fila.astype(str).str.contains(
            "MAESTR|MASTER|POSGRADO|POSTGRADO",
            regex=True
        ).any(),
        axis=1
    )

    maestrias = catalogo.loc[mask_maestria].copy()

    if col_programa is None:
        col_programa = detectar_columna_programa(maestrias)

    maestrias["ProgramaMaestria"] = maestrias[col_programa].astype(str)
    maestrias["LineaMaestria"] = maestrias["ProgramaMaestria"].apply(asignar_linea_programa)

    catalogo_lineas = (
        maestrias[["LineaMaestria", "ProgramaMaestria"]]
        .drop_duplicates()
        .sort_values(["LineaMaestria", "ProgramaMaestria"])
    )

    return maestrias, catalogo_lineas


def obtener_programas_por_linea(catalogo_lineas, linea, n=3):
    """
    Devuelve programas UDLA asociados a una línea de recomendación.
    """

    programas = (
        catalogo_lineas.loc[
            catalogo_lineas["LineaMaestria"] == linea,
            "ProgramaMaestria"
        ]
        .dropna()
        .drop_duplicates()
        .head(n)
        .tolist()
    )

    if len(programas) == 0:
        return "Sin programa identificado en catálogo"

    return " | ".join(programas)


def generar_recomendaciones(base, catalogo_lineas):
    """
    Genera recomendaciones Top 3 para cada graduado.
    """

    recomendaciones = []

    for _, row in base.iterrows():
        ranking = recomendar_lineas(row)

        if ranking.empty:
            continue

        ranking = ranking.head(3).copy()

        ranking["Identificador"] = row.get("Identificador", "")
        ranking["Estudiante"] = row.get("Estudiante", "")
        ranking["CarreraHom"] = row.get("CarreraHom", "")
        ranking["Titulo"] = row.get("Titulo", "")
        ranking["NOMEMP"] = row.get("NOMEMP", "")
        ranking["TIPOEMPRES"] = row.get("TIPOEMPRES", "")
        ranking["OCUPAFI"] = row.get("OCUPAFI", "")
        ranking["AniosEnCargo"] = row.get("AniosEnCargo", np.nan)
        ranking["AniosDesdeGraduacion"] = row.get("AniosDesdeGraduacion", np.nan)

        ranking["ProgramasSugeridosUDLA"] = ranking["LineaMaestria"].apply(
            lambda linea: obtener_programas_por_linea(catalogo_lineas, linea)
        )

        ranking["OrdenRecomendacion"] = range(1, len(ranking) + 1)

        recomendaciones.append(ranking)

    if len(recomendaciones) == 0:
        return pd.DataFrame(), pd.DataFrame()

    recomendaciones_larga = pd.concat(recomendaciones, ignore_index=True)

    top3 = recomendaciones_larga.pivot_table(
        index=[
            "Identificador",
            "Estudiante",
            "CarreraHom",
            "Titulo",
            "NOMEMP",
            "TIPOEMPRES",
            "OCUPAFI",
            "AniosEnCargo",
            "AniosDesdeGraduacion"
        ],
        columns="OrdenRecomendacion",
        values=["LineaMaestria", "Score", "ProgramasSugeridosUDLA"],
        aggfunc="first"
    )

    top3.columns = [f"{var}_{orden}" for var, orden in top3.columns]
    top3 = top3.reset_index()

    top3 = top3.rename(columns={
        "LineaMaestria_1": "Recomendacion_1",
        "LineaMaestria_2": "Recomendacion_2",
        "LineaMaestria_3": "Recomendacion_3",
        "ProgramasSugeridosUDLA_1": "Programas_UDLA_1",
        "ProgramasSugeridosUDLA_2": "Programas_UDLA_2",
        "ProgramasSugeridosUDLA_3": "Programas_UDLA_3",
    })

    top3["Justificacion_Recomendacion_1"] = top3.apply(
        generar_justificacion,
        axis=1
    )

    return recomendaciones_larga, top3
