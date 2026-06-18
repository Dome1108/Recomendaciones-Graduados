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
        "regimen": "regimen",
        "Tipo_Trabajo": "Tipo_Trabajo",
        "NotaFinalCarrera": "NotaFinalCarrera",
        "PeriodoTemporal": "PeriodoTemporal"
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
    Si no existe información laboral, conserva igual al graduado y marca el caso.
    """

    base = graduados.merge(
        laboral,
        left_on="Identificador",
        right_on="NUMAFI",
        how="left"
    )

    base["TieneInformacionLaboral"] = np.where(
        base["NUMAFI"].notna(),
        "Con información laboral",
        "Sin información laboral"
    )

    campos_laborales = ["TIPOEMPRES", "NOMEMP", "OCUPAFI"]

    for col in campos_laborales:
        if col not in base.columns:
            base[col] = "Sin información laboral"
        else:
            base[col] = base[col].fillna("Sin información laboral")

    hoy = pd.Timestamp.today().normalize()

    if "FechaGraduacion" in base.columns:
        base["FechaGraduacion"] = pd.to_datetime(
            base["FechaGraduacion"],
            errors="coerce",
            dayfirst=True
        )

        base["AniosDesdeGraduacion"] = (
            (hoy - base["FechaGraduacion"]).dt.days / 365.25
        ).round(1)
    else:
        base["AniosDesdeGraduacion"] = np.nan

    if "FECINGAFI" in base.columns:
        base["FECINGAFI"] = pd.to_datetime(
            base["FECINGAFI"],
            errors="coerce",
            dayfirst=True
        )

        base["AniosEnCargo"] = (
            (hoy - base["FECINGAFI"]).dt.days / 365.25
        ).round(1)

        base["AniosEnCargo"] = base["AniosEnCargo"].fillna(0)
    else:
        base["AniosEnCargo"] = 0

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
    Detecta la columna donde está el nombre del programa/carrera.
    """

    posibles_columnas = [
        "CarreraHomologada",
        "DesCarrera",
        "Descarrera",
        "DesCarreraUnificado",
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

    if any(p in txt for p in [
        "FINANZ", "BANCA", "FINANCI", "RIESGO", "TRIBUT",
        "MERCADO DE VALORES", "CONTABIL", "AUDITOR"
    ]):
        return "FINANZAS_BANCA"

    if any(p in txt for p in [
        "DATA", "DATOS", "ANALYTICS", "ANALITICA", "BIG DATA",
        "CIENCIA DE DATOS", "INTELIGENCIA ARTIFICIAL", "BUSINESS INTELLIGENCE"
    ]):
        return "ANALITICA_DATOS"

    if any(p in txt for p in [
        "MBA", "ADMINISTR", "DIRECCION", "GERENCIA",
        "NEGOCIOS", "EMPRESA", "EMPRESARIAL"
    ]):
        return "MBA_ADMINISTRACION"

    if "PROYECT" in txt:
        return "GESTION_PROYECTOS"

    if any(p in txt for p in [
        "MARKETING", "COMERCIAL", "VENTAS", "MERCAD",
        "PUBLICIDAD", "COMUNICACION"
    ]):
        return "MARKETING_COMERCIAL"

    if any(p in txt for p in [
        "DERECHO", "LEGAL", "JURID", "COMPLIANCE",
        "CONSTITUCIONAL", "PENAL", "PROCESAL"
    ]):
        return "DERECHO_LEGAL"

    if any(p in txt for p in [
        "SALUD", "HOSPITAL", "CLINIC", "SANIT",
        "MEDIC", "EPIDEM", "ENFERM", "ODONTO"
    ]):
        return "SALUD_GESTION"

    if any(p in txt for p in [
        "EDUC", "DOCENC", "PEDAGOG", "ENSEN", "ENSEÑ"
    ]):
        return "EDUCACION"

    if any(p in txt for p in [
        "SOFTWARE", "SISTEMAS", "INFORMAT", "CIBER",
        "TECNOLOG", "TRANSFORMACION DIGITAL"
    ]):
        return "TECNOLOGIA"

    if any(p in txt for p in [
        "PSICO", "TALENTO", "RECURSOS HUMANOS", "HUMANO"
    ]):
        return "PSICOLOGIA_RRHH"

    if any(p in txt for p in [
        "ARQUIT", "DISENO", "DISEÑO", "URBAN"
    ]):
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

    if maestrias.empty:
        raise ValueError(
            "No se detectaron maestrías en el catálogo. "
            "Revisa si el catálogo usa otra palabra distinta a MAESTRIA, MASTER, POSGRADO o POSTGRADO."
        )

    if col_programa is None:
        col_programa = detectar_columna_programa(maestrias)

    maestrias["ProgramaMaestria"] = maestrias[col_programa].astype(str)
    maestrias["LineaMaestria"] = maestrias["ProgramaMaestria"].apply(
        asignar_linea_programa
    )

    catalogo_lineas = (
        maestrias[["LineaMaestria", "ProgramaMaestria"]]
        .drop_duplicates()
        .sort_values(["LineaMaestria", "ProgramaMaestria"])
        .reset_index(drop=True)
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
    Incluye graduados con y sin información laboral.
    """

    recomendaciones = []

    for _, row in base.iterrows():
        ranking = recomendar_lineas(row)

        if ranking.empty:
            ranking = pd.DataFrame({
                "LineaMaestria": [
                    "MBA_ADMINISTRACION",
                    "GESTION_PROYECTOS",
                    "ANALITICA_DATOS"
                ],
                "Score": [35, 30, 25]
            })

        ranking = ranking.head(3).copy()

        ranking["Identificador"] = row.get("Identificador", "")
        ranking["Estudiante"] = row.get("Estudiante", "")
        ranking["CarreraHom"] = row.get("CarreraHom", "")
        ranking["Titulo"] = row.get("Titulo", "")
        ranking["NOMEMP"] = row.get("NOMEMP", "Sin información laboral")
        ranking["TIPOEMPRES"] = row.get("TIPOEMPRES", "Sin información laboral")
        ranking["OCUPAFI"] = row.get("OCUPAFI", "Sin información laboral")
        ranking["TieneInformacionLaboral"] = row.get("TieneInformacionLaboral", "Sin información laboral")
        ranking["AniosEnCargo"] = row.get("AniosEnCargo", 0)
        ranking["AniosDesdeGraduacion"] = row.get("AniosDesdeGraduacion", np.nan)

        ranking["ProgramasSugeridosUDLA"] = ranking["LineaMaestria"].apply(
            lambda linea: obtener_programas_por_linea(catalogo_lineas, linea)
        )

        ranking["OrdenRecomendacion"] = range(1, len(ranking) + 1)

        recomendaciones.append(ranking)

    if len(recomendaciones) == 0:
        return pd.DataFrame(), pd.DataFrame()

    recomendaciones_larga = pd.concat(recomendaciones, ignore_index=True)

    campos_index = [
        "Identificador",
        "Estudiante",
        "CarreraHom",
        "Titulo",
        "NOMEMP",
        "TIPOEMPRES",
        "OCUPAFI",
        "TieneInformacionLaboral",
        "AniosEnCargo",
        "AniosDesdeGraduacion"
    ]

    for col in campos_index:
        if col not in recomendaciones_larga.columns:
            recomendaciones_larga[col] = ""

    recomendaciones_larga["NOMEMP"] = recomendaciones_larga["NOMEMP"].fillna("Sin información laboral")
    recomendaciones_larga["TIPOEMPRES"] = recomendaciones_larga["TIPOEMPRES"].fillna("Sin información laboral")
    recomendaciones_larga["OCUPAFI"] = recomendaciones_larga["OCUPAFI"].fillna("Sin información laboral")
    recomendaciones_larga["TieneInformacionLaboral"] = recomendaciones_larga["TieneInformacionLaboral"].fillna("Sin información laboral")
    recomendaciones_larga["AniosEnCargo"] = recomendaciones_larga["AniosEnCargo"].fillna(0)

    top3 = recomendaciones_larga.pivot_table(
        index=campos_index,
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
