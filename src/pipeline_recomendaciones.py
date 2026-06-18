import pandas as pd
import numpy as np

from utils_texto import normalizar_texto
from recomendador import recomendar_lineas, generar_justificacion


TABLA_RESULTADO_BDD = "BDD_IDM.dbo.Recomendaciones_Maestrias_Graduados"


def estandarizar_columnas_graduados(graduados):
    graduados = graduados.copy()

    graduados.columns = (
        graduados.columns
        .astype(str)
        .str.strip()
        .str.replace("\ufeff", "", regex=False)
    )

    mapa_columnas = {
        "IdentificacionBanner": "Identificador",
        "Identificador": "Identificador",
        "Cedula": "Identificador",
        "Cédula": "Identificador",
        "cedula": "Identificador",
        "NUMAFI": "Identificador",

        "CarreraHomologada": "CarreraHom",
        "CarreraHom": "CarreraHom",
        "DesCarrera": "CarreraHom",
        "Descarrera": "CarreraHom",
        "carrera": "CarreraHom",

        "desfacultad": "desfacultad",
        "DesFacultad": "desfacultad",
        "Facultad": "desfacultad",

        "regimen": "regimen",
        "Regimen": "regimen",
        "NivelEstudio": "NivelEstudio",
        "IdNivelEstu": "IdNivelEstu",

        "Titulo": "Titulo",
        "FechaGraduacion": "FechaGraduacion",
        "Estudiante": "Estudiante",
        "nombre": "Estudiante",
        "MailUDLA": "MailUDLA",
        "Genero": "Genero",
        "Modalidad": "Modalidad",
        "Semestre": "Semestre",
        "PeriodoTemporal": "PeriodoTemporal",
        "Tipo_Trabajo": "Tipo_Trabajo",
        "NotaFinalCarrera": "NotaFinalCarrera"
    }

    graduados = graduados.rename(columns=mapa_columnas)

    if "Identificador" not in graduados.columns:
        raise ValueError(
            "No se encontró columna de identificador en Vw_Graduados. "
            f"Columnas disponibles: {graduados.columns.tolist()}"
        )

    if "CarreraHom" not in graduados.columns:
        raise ValueError(
            "No se encontró columna de carrera en Vw_Graduados. "
            f"Columnas disponibles: {graduados.columns.tolist()}"
        )

    graduados["Identificador"] = (
        graduados["Identificador"]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )

    columnas_minimas = [
        "Estudiante",
        "MailUDLA",
        "Titulo",
        "desfacultad",
        "regimen",
        "NivelEstudio",
        "FechaGraduacion",
        "Modalidad",
        "Genero",
        "Semestre"
    ]

    for col in columnas_minimas:
        if col not in graduados.columns:
            graduados[col] = ""

    return graduados


def cargar_graduados_sql(conn):
    query = """
    SELECT *
    FROM DwhOperacional.dbo.Vw_Graduados;
    """

    graduados = pd.read_sql(query, conn)
    graduados = estandarizar_columnas_graduados(graduados)

    return graduados


def detectar_tipo_nivel(row):
    texto = " ".join([
        normalizar_texto(row.get("regimen", "")),
        normalizar_texto(row.get("NivelEstudio", "")),
        normalizar_texto(row.get("CarreraHom", "")),
        normalizar_texto(row.get("Titulo", ""))
    ])

    palabras_posgrado = [
        "POSGRADO",
        "POSTGRADO",
        "MAESTR",
        "MAGISTER",
        "ESPECIALIZ",
        "DOCTORADO",
        "PHD"
    ]

    if any(p in texto for p in palabras_posgrado):
        return "POSGRADO"

    if "PREGRADO" in texto:
        return "PREGRADO"

    return "PREGRADO"


def asignar_linea_programa(nombre_programa):
    txt = normalizar_texto(nombre_programa)

    if any(p in txt for p in [
        "ODONTO", "ODONTOPEDIATR", "ORTODON", "ENDODON",
        "PERIODON", "IMPLANTOLOG", "REHABILITACION ORAL",
        "REHABILITACIÓN ORAL"
    ]):
        return "SALUD_ODONTOLOGIA"

    if any(p in txt for p in [
        "MEDIC", "CARDIO", "PEDIATR", "GINECO", "TRAUMA",
        "CIRUG", "ANEST", "RADIOLOG", "DERMA", "EMERGEN",
        "MEDICINA INTERNA", "PSIQUIATR", "NEURO", "UROLOG",
        "OFTALMO", "OTORRINO"
    ]):
        return "SALUD_MEDICINA"

    if any(p in txt for p in [
        "SALUD", "HOSPITAL", "CLINIC", "CLÍNIC", "SANIT",
        "EPIDEM", "ENFERM", "FISIOTER", "TERAPIA"
    ]):
        return "SALUD_GESTION"

    if any(p in txt for p in [
        "FINANZ", "BANCA", "FINANCI", "RIESGO", "TRIBUT",
        "MERCADO DE VALORES", "CONTABIL", "AUDITOR"
    ]):
        return "FINANZAS_BANCA"

    if any(p in txt for p in [
        "DATA", "DATOS", "ANALYTICS", "ANALITICA", "ANALÍTICA",
        "BIG DATA", "CIENCIA DE DATOS", "INTELIGENCIA ARTIFICIAL",
        "BUSINESS INTELLIGENCE"
    ]):
        return "ANALITICA_DATOS"

    if any(p in txt for p in [
        "MBA", "ADMINISTR", "DIRECCION", "DIRECCIÓN", "GERENCIA",
        "NEGOCIOS", "EMPRESA", "EMPRESARIAL"
    ]):
        return "MBA_ADMINISTRACION"

    if "PROYECT" in txt:
        return "GESTION_PROYECTOS"

    if any(p in txt for p in [
        "MARKETING", "COMERCIAL", "VENTAS", "MERCAD",
        "PUBLICIDAD", "COMUNICACION", "COMUNICACIÓN"
    ]):
        return "MARKETING_COMERCIAL"

    if any(p in txt for p in [
        "DERECHO", "LEGAL", "JURID", "JURÍD", "COMPLIANCE",
        "CONSTITUCIONAL", "PENAL", "PROCESAL"
    ]):
        return "DERECHO_LEGAL"

    if any(p in txt for p in [
        "EDUC", "DOCENC", "PEDAGOG", "PEDAGÓG", "ENSEN", "ENSEÑ"
    ]):
        return "EDUCACION"

    if any(p in txt for p in [
        "SOFTWARE", "SISTEMAS", "INFORMAT", "CIBER",
        "TECNOLOG", "TRANSFORMACION DIGITAL", "TRANSFORMACIÓN DIGITAL"
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


def calcular_restriccion_academica(row):
    texto = " ".join([
        normalizar_texto(row.get("CarreraHom", "")),
        normalizar_texto(row.get("Titulo", "")),
        normalizar_texto(row.get("desfacultad", ""))
    ])

    if any(p in texto for p in ["ODONTO", "ODONTOLOG"]):
        return "ODONTOLOGIA"

    if any(p in texto for p in ["MEDICINA", "MEDICO", "MÉDICO", "MEDICA", "MÉDICA"]):
        return "MEDICINA"

    if any(p in texto for p in ["ENFERM", "FISIOTER", "SALUD"]):
        return "SALUD_GENERAL"

    return "SIN_RESTRICCION"


def lineas_permitidas_por_restriccion(restriccion):
    if restriccion == "MEDICINA":
        return ["SALUD_MEDICINA", "SALUD_GESTION"]

    if restriccion == "ODONTOLOGIA":
        return ["SALUD_ODONTOLOGIA", "SALUD_GESTION"]

    if restriccion == "SALUD_GENERAL":
        return ["SALUD_GESTION"]

    return None


def preparar_graduados_pregrado_y_posgrado(graduados):
    graduados = graduados.copy()

    graduados["TipoNivelAcademico"] = graduados.apply(detectar_tipo_nivel, axis=1)

    graduados["FechaGraduacion"] = pd.to_datetime(
        graduados["FechaGraduacion"],
        errors="coerce",
        dayfirst=True
    )

    pregrado = graduados[graduados["TipoNivelAcademico"] == "PREGRADO"].copy()
    posgrado = graduados[graduados["TipoNivelAcademico"] == "POSGRADO"].copy()

    pregrado["RestriccionAcademica"] = pregrado.apply(calcular_restriccion_academica, axis=1)

    pregrado["LlavePregrado"] = (
        pregrado["Identificador"].astype(str)
        + "|"
        + pregrado["CarreraHom"].astype(str)
        + "|"
        + pregrado["Titulo"].astype(str)
    )

    pregrado = pregrado.sort_values(
        by=["Identificador", "CarreraHom", "FechaGraduacion"],
        ascending=[True, True, False]
    )

    pregrado = pregrado.drop_duplicates(
        subset=["LlavePregrado"],
        keep="first"
    )

    if posgrado.empty:
        pregrado["YaEstudioPosgradoUDLA"] = "No"
        pregrado["PosgradosUDLAPrevios"] = "No registra"
        pregrado["LineasPosgradoPrevias"] = "No registra"
        return pregrado, posgrado

    posgrado["ProgramaPosgradoPrevio"] = posgrado["CarreraHom"].fillna("").astype(str)
    posgrado["LineaPosgradoPrevio"] = posgrado["ProgramaPosgradoPrevio"].apply(asignar_linea_programa)

    resumen_posgrado = (
        posgrado
        .groupby("Identificador")
        .agg({
            "ProgramaPosgradoPrevio": lambda x: " | ".join(sorted(set([str(v) for v in x if str(v).strip() != ""]))),
            "LineaPosgradoPrevio": lambda x: " | ".join(sorted(set([str(v) for v in x if str(v).strip() != ""])))
        })
        .reset_index()
        .rename(columns={
            "ProgramaPosgradoPrevio": "PosgradosUDLAPrevios",
            "LineaPosgradoPrevio": "LineasPosgradoPrevias"
        })
    )

    pregrado = pregrado.merge(
        resumen_posgrado,
        on="Identificador",
        how="left"
    )

    pregrado["YaEstudioPosgradoUDLA"] = np.where(
        pregrado["PosgradosUDLAPrevios"].notna(),
        "Sí",
        "No"
    )

    pregrado["PosgradosUDLAPrevios"] = pregrado["PosgradosUDLAPrevios"].fillna("No registra")
    pregrado["LineasPosgradoPrevias"] = pregrado["LineasPosgradoPrevias"].fillna("No registra")

    return pregrado, posgrado


def obtener_laboral_sql(conn, identificadores):
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
    FROM Reportes.dbo.SIM_Y_ENE_26 s
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

    laboral_unico["FuenteInformacionLaboral"] = "SIM"

    return laboral_unico


def obtener_laboral_linkedin_sql(conn, identificadores):
    """
    Lee toda la tabla de LinkedIn y filtra en Python.
    Esto evita errores de cruce por tipos de dato, collation o temp tables.
    """

    ids = (
        pd.Series(identificadores)
        .dropna()
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
        .unique()
        .tolist()
    )

    ids_set = set(ids)

    query = """
    SELECT
        CAST(cedula AS VARCHAR(30)) AS NUMAFI,
        nombre AS APENOMAFI,
        carrera AS CarreraLinkedIn,
        empresa AS NOMEMP,
        cargo AS OCUPAFI,
        tamanoEmpresa AS TamanoEmpresaLinkedIn,
        fechaIngreso AS FECINGAFI,
        paisTrabajo AS PaisTrabajoLinkedIn,
        anioGraduacion AS AnioGraduacionLinkedIn
    FROM BDD_Proyectos.mercados.EmpleabilidadLinkedin;
    """

    linkedin = pd.read_sql(query, conn)

    if linkedin.empty:
        return linkedin

    linkedin["NUMAFI"] = (
        linkedin["NUMAFI"]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )

    linkedin = linkedin[linkedin["NUMAFI"].isin(ids_set)].copy()

    if linkedin.empty:
        return linkedin

    linkedin["FECINGAFI"] = pd.to_datetime(
        linkedin["FECINGAFI"],
        errors="coerce",
        dayfirst=True
    )

    hoy = pd.Timestamp.today().normalize()

    linkedin["FechaIngresoValida"] = linkedin["FECINGAFI"]

    linkedin.loc[
        (linkedin["FechaIngresoValida"] < pd.Timestamp("1970-01-01"))
        | (linkedin["FechaIngresoValida"] > hoy + pd.DateOffset(years=1)),
        "FechaIngresoValida"
    ] = pd.NaT

    linkedin["TieneEmpresaLinkedIn"] = np.where(
        linkedin["NOMEMP"].notna() & (linkedin["NOMEMP"].astype(str).str.strip() != ""),
        1,
        0
    )

    linkedin["TieneCargoLinkedIn"] = np.where(
        linkedin["OCUPAFI"].notna() & (linkedin["OCUPAFI"].astype(str).str.strip() != ""),
        1,
        0
    )

    linkedin = linkedin.sort_values(
        by=[
            "NUMAFI",
            "FechaIngresoValida",
            "TieneEmpresaLinkedIn",
            "TieneCargoLinkedIn"
        ],
        ascending=[True, True, False, False],
        na_position="last"
    )

    linkedin_unico = linkedin.drop_duplicates(
        subset=["NUMAFI"],
        keep="first"
    ).copy()

    linkedin_unico["TIPOEMPRES"] = "LINKEDIN"
    linkedin_unico["SALARIO"] = np.nan
    linkedin_unico["ANIO"] = linkedin_unico["FECINGAFI"].dt.year
    linkedin_unico["MES"] = linkedin_unico["FECINGAFI"].dt.month
    linkedin_unico["FuenteInformacionLaboral"] = "LINKEDIN"

    columnas_salida = [
        "NUMAFI",
        "APENOMAFI",
        "TIPOEMPRES",
        "NOMEMP",
        "OCUPAFI",
        "SALARIO",
        "FECINGAFI",
        "ANIO",
        "MES",
        "FuenteInformacionLaboral",
        "TamanoEmpresaLinkedIn",
        "PaisTrabajoLinkedIn",
        "AnioGraduacionLinkedIn"
    ]

    return linkedin_unico[columnas_salida]


def cruzar_graduados_laboral(graduados_pregrado, laboral, laboral_linkedin=None):
    laboral_sim = laboral.copy()

    if not laboral_sim.empty:
        laboral_sim["FuenteInformacionLaboral"] = "SIM"
        laboral_sim["TamanoEmpresaLinkedIn"] = np.nan
        laboral_sim["PaisTrabajoLinkedIn"] = np.nan
        laboral_sim["AnioGraduacionLinkedIn"] = np.nan

    if laboral_linkedin is None:
        laboral_linkedin = pd.DataFrame()

    if not laboral_linkedin.empty:
        laboral_linkedin = laboral_linkedin.copy()
        laboral_linkedin["FuenteInformacionLaboral"] = "LINKEDIN"

    columnas_empleo = [
        "NUMAFI",
        "APENOMAFI",
        "TIPOEMPRES",
        "NOMEMP",
        "OCUPAFI",
        "SALARIO",
        "FECINGAFI",
        "ANIO",
        "MES",
        "FuenteInformacionLaboral",
        "TamanoEmpresaLinkedIn",
        "PaisTrabajoLinkedIn",
        "AnioGraduacionLinkedIn"
    ]

    for col in columnas_empleo:
        if col not in laboral_sim.columns:
            laboral_sim[col] = np.nan

        if col not in laboral_linkedin.columns:
            laboral_linkedin[col] = np.nan

    empleo_combinado = pd.concat(
        [
            laboral_sim[columnas_empleo],
            laboral_linkedin[columnas_empleo]
        ],
        ignore_index=True
    )

    if not empleo_combinado.empty:
        empleo_combinado["NUMAFI"] = (
            empleo_combinado["NUMAFI"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.strip()
        )

        empleo_combinado["PrioridadFuenteLaboral"] = empleo_combinado["FuenteInformacionLaboral"].map({
            "SIM": 1,
            "LINKEDIN": 2
        }).fillna(9)

        empleo_combinado["FECINGAFI"] = pd.to_datetime(
            empleo_combinado["FECINGAFI"],
            errors="coerce",
            dayfirst=True
        )

        empleo_combinado = empleo_combinado.sort_values(
            by=["NUMAFI", "PrioridadFuenteLaboral", "FECINGAFI"],
            ascending=[True, True, True],
            na_position="last"
        )

        empleo_preferente = empleo_combinado.drop_duplicates(
            subset=["NUMAFI"],
            keep="first"
        ).copy()
    else:
        empleo_preferente = pd.DataFrame(columns=columnas_empleo)

    base = graduados_pregrado.merge(
        empleo_preferente,
        left_on="Identificador",
        right_on="NUMAFI",
        how="left"
    )

    base["FuenteInformacionLaboral"] = base["FuenteInformacionLaboral"].fillna(
        "SIN_INFORMACION_LABORAL"
    )

    base["TieneInformacionLaboral"] = np.where(
        base["FuenteInformacionLaboral"].isin(["SIM", "LINKEDIN"]),
        "Con información laboral",
        "Sin información laboral"
    )

    campos_laborales = ["TIPOEMPRES", "NOMEMP", "OCUPAFI"]

    for col in campos_laborales:
        if col not in base.columns:
            base[col] = "Sin información laboral"
        else:
            base[col] = base[col].fillna("Sin información laboral")

    if "SALARIO" not in base.columns:
        base["SALARIO"] = np.nan

    hoy = pd.Timestamp.today().normalize()

    base["AniosDesdeGraduacion"] = (
        (hoy - base["FechaGraduacion"]).dt.days / 365.25
    ).round(1)

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
    query = """
    SELECT *
    FROM DwhOperacional.dbo.Vw_CarreraFacultadArea_new;
    """

    catalogo = pd.read_sql(query, conn)

    return catalogo


def detectar_columna_programa(catalogo):
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


def preparar_catalogo_maestrias(catalogo, col_programa=None):
    catalogo_txt = catalogo.copy()

    for col in catalogo_txt.columns:
        if catalogo_txt[col].dtype == "object":
            catalogo_txt[col] = catalogo_txt[col].apply(normalizar_texto)

    columnas_texto = catalogo_txt.select_dtypes(include="object").columns

    mask_maestria = catalogo_txt[columnas_texto].apply(
        lambda fila: fila.astype(str).str.contains(
            "MAESTR|MASTER|POSGRADO|POSTGRADO|ESPECIALIZ",
            regex=True
        ).any(),
        axis=1
    )

    maestrias = catalogo.loc[mask_maestria].copy()

    if maestrias.empty:
        raise ValueError("No se detectaron maestrías/especializaciones en el catálogo.")

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


def obtener_programas_por_linea(catalogo_lineas, linea, programas_excluir=None, n=3):
    if programas_excluir is None:
        programas_excluir = []

    programas_excluir_norm = [normalizar_texto(p) for p in programas_excluir]

    programas = (
        catalogo_lineas.loc[
            catalogo_lineas["LineaMaestria"] == linea,
            "ProgramaMaestria"
        ]
        .dropna()
        .drop_duplicates()
        .tolist()
    )

    programas_filtrados = []

    for programa in programas:
        programa_norm = normalizar_texto(programa)

        if programa_norm not in programas_excluir_norm:
            programas_filtrados.append(programa)

    programas_filtrados = programas_filtrados[:n]

    if len(programas_filtrados) == 0:
        return "Sin programa identificado en catálogo"

    return " | ".join(programas_filtrados)


def ajustar_ranking_por_posgrado_previo(ranking, lineas_previas):
    if ranking.empty:
        return ranking

    if pd.isna(lineas_previas) or str(lineas_previas).strip() in ["", "No registra"]:
        return ranking

    lineas_previas_lista = [
        x.strip()
        for x in str(lineas_previas).split("|")
        if x.strip() != ""
    ]

    ranking = ranking.copy()

    ranking["PenalizacionPosgradoPrevio"] = ranking["LineaMaestria"].apply(
        lambda x: 35 if x in lineas_previas_lista else 0
    )

    ranking["Score"] = ranking["Score"] - ranking["PenalizacionPosgradoPrevio"]
    ranking["Score"] = ranking["Score"].clip(lower=0)

    ranking = ranking[ranking["Score"] > 0].copy()

    ranking = (
        ranking
        .sort_values("Score", ascending=False)
        .reset_index(drop=True)
    )

    return ranking


def aplicar_restriccion_academica(ranking, restriccion):
    lineas_permitidas = lineas_permitidas_por_restriccion(restriccion)

    if lineas_permitidas is None:
        return ranking

    if ranking.empty:
        return ranking

    ranking = ranking[ranking["LineaMaestria"].isin(lineas_permitidas)].copy()
    ranking = ranking.sort_values("Score", ascending=False).reset_index(drop=True)

    return ranking


def completar_ranking_si_faltan(ranking, lineas_previas, restriccion):
    lineas_permitidas = lineas_permitidas_por_restriccion(restriccion)

    if lineas_permitidas is not None:
        fallback = [(linea, 60 - i * 10) for i, linea in enumerate(lineas_permitidas)]
    else:
        fallback = [
            ("MBA_ADMINISTRACION", 35),
            ("GESTION_PROYECTOS", 30),
            ("ANALITICA_DATOS", 25),
            ("MARKETING_COMERCIAL", 20),
            ("TECNOLOGIA", 20)
        ]

    ranking = ranking.copy()

    existentes = set(ranking["LineaMaestria"].tolist()) if not ranking.empty else set()

    lineas_previas_lista = []
    if not pd.isna(lineas_previas) and str(lineas_previas).strip() not in ["", "No registra"]:
        lineas_previas_lista = [
            x.strip()
            for x in str(lineas_previas).split("|")
            if x.strip() != ""
        ]

    nuevos = []

    for linea, score in fallback:
        if linea not in existentes and linea not in lineas_previas_lista:
            nuevos.append({"LineaMaestria": linea, "Score": score})

        if len(ranking) + len(nuevos) >= 3:
            break

    if nuevos:
        ranking = pd.concat([ranking, pd.DataFrame(nuevos)], ignore_index=True)

    ranking = ranking.sort_values("Score", ascending=False).reset_index(drop=True)

    return ranking.head(3)


def generar_recomendaciones(base, catalogo_lineas):
    recomendaciones = []

    for idx, row in base.iterrows():
        ranking = recomendar_lineas(row)

        restriccion = row.get("RestriccionAcademica", "SIN_RESTRICCION")

        ranking = aplicar_restriccion_academica(ranking, restriccion)

        ranking = ajustar_ranking_por_posgrado_previo(
            ranking,
            row.get("LineasPosgradoPrevias", "No registra")
        )

        if ranking.empty:
            ranking = pd.DataFrame(columns=["LineaMaestria", "Score"])

        ranking = completar_ranking_si_faltan(
            ranking,
            row.get("LineasPosgradoPrevias", "No registra"),
            restriccion
        )

        ranking = ranking.head(3).copy()

        posgrados_previos = row.get("PosgradosUDLAPrevios", "No registra")
        programas_excluir = []

        if str(posgrados_previos).strip() not in ["", "No registra"]:
            programas_excluir = [
                x.strip()
                for x in str(posgrados_previos).split("|")
                if x.strip() != ""
            ]

        ranking["RegistroID"] = idx
        ranking["Identificador"] = row.get("Identificador", "")
        ranking["Estudiante"] = row.get("Estudiante", "")
        ranking["MailUDLA"] = row.get("MailUDLA", "")
        ranking["Genero"] = row.get("Genero", "")
        ranking["CarreraHom"] = row.get("CarreraHom", "")
        ranking["desfacultad"] = row.get("desfacultad", "")
        ranking["Titulo"] = row.get("Titulo", "")
        ranking["FechaGraduacion"] = row.get("FechaGraduacion", pd.NaT)
        ranking["Modalidad"] = row.get("Modalidad", "")
        ranking["Semestre"] = row.get("Semestre", "")
        ranking["NOMEMP"] = row.get("NOMEMP", "Sin información laboral")
        ranking["TIPOEMPRES"] = row.get("TIPOEMPRES", "Sin información laboral")
        ranking["OCUPAFI"] = row.get("OCUPAFI", "Sin información laboral")
        ranking["SALARIO"] = row.get("SALARIO", np.nan)
        ranking["FECINGAFI"] = row.get("FECINGAFI", pd.NaT)
        ranking["TieneInformacionLaboral"] = row.get("TieneInformacionLaboral", "Sin información laboral")
        ranking["FuenteInformacionLaboral"] = row.get("FuenteInformacionLaboral", "SIN_INFORMACION_LABORAL")
        ranking["TamanoEmpresaLinkedIn"] = row.get("TamanoEmpresaLinkedIn", np.nan)
        ranking["PaisTrabajoLinkedIn"] = row.get("PaisTrabajoLinkedIn", np.nan)
        ranking["AnioGraduacionLinkedIn"] = row.get("AnioGraduacionLinkedIn", np.nan)
        ranking["AniosEnCargo"] = row.get("AniosEnCargo", 0)
        ranking["AniosDesdeGraduacion"] = row.get("AniosDesdeGraduacion", np.nan)
        ranking["YaEstudioPosgradoUDLA"] = row.get("YaEstudioPosgradoUDLA", "No")
        ranking["PosgradosUDLAPrevios"] = row.get("PosgradosUDLAPrevios", "No registra")
        ranking["LineasPosgradoPrevias"] = row.get("LineasPosgradoPrevias", "No registra")
        ranking["RestriccionAcademica"] = restriccion

        ranking["ProgramasSugeridosUDLA"] = ranking["LineaMaestria"].apply(
            lambda linea: obtener_programas_por_linea(
                catalogo_lineas,
                linea,
                programas_excluir=programas_excluir
            )
        )

        ranking["OrdenRecomendacion"] = range(1, len(ranking) + 1)

        recomendaciones.append(ranking)

    if len(recomendaciones) == 0:
        return pd.DataFrame(), pd.DataFrame()

    recomendaciones_larga = pd.concat(recomendaciones, ignore_index=True)

    campos_info = [
        "RegistroID",
        "Identificador",
        "Estudiante",
        "MailUDLA",
        "Genero",
        "CarreraHom",
        "desfacultad",
        "Titulo",
        "FechaGraduacion",
        "Modalidad",
        "Semestre",
        "NOMEMP",
        "TIPOEMPRES",
        "OCUPAFI",
        "SALARIO",
        "FECINGAFI",
        "TieneInformacionLaboral",
        "FuenteInformacionLaboral",
        "TamanoEmpresaLinkedIn",
        "PaisTrabajoLinkedIn",
        "AnioGraduacionLinkedIn",
        "AniosEnCargo",
        "AniosDesdeGraduacion",
        "YaEstudioPosgradoUDLA",
        "PosgradosUDLAPrevios",
        "LineasPosgradoPrevias",
        "RestriccionAcademica"
    ]

    metadata = (
        recomendaciones_larga[campos_info]
        .drop_duplicates(subset=["RegistroID"])
        .reset_index(drop=True)
    )

    top3_wide = recomendaciones_larga.pivot_table(
        index="RegistroID",
        columns="OrdenRecomendacion",
        values=["LineaMaestria", "Score", "ProgramasSugeridosUDLA"],
        aggfunc="first"
    )

    top3_wide.columns = [f"{var}_{orden}" for var, orden in top3_wide.columns]
    top3_wide = top3_wide.reset_index()

    top3 = metadata.merge(top3_wide, on="RegistroID", how="left")

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


def preparar_resultado_sql(top3):
    df = top3.copy()

    columnas_salida = [
        "Identificador",
        "Estudiante",
        "MailUDLA",
        "Genero",
        "CarreraHom",
        "desfacultad",
        "Titulo",
        "FechaGraduacion",
        "Modalidad",
        "Semestre",
        "NOMEMP",
        "TIPOEMPRES",
        "OCUPAFI",
        "SALARIO",
        "FECINGAFI",
        "TieneInformacionLaboral",
        "FuenteInformacionLaboral",
        "TamanoEmpresaLinkedIn",
        "PaisTrabajoLinkedIn",
        "AnioGraduacionLinkedIn",
        "AniosEnCargo",
        "AniosDesdeGraduacion",
        "YaEstudioPosgradoUDLA",
        "PosgradosUDLAPrevios",
        "LineasPosgradoPrevias",
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

    for col in columnas_salida:
        if col not in df.columns:
            df[col] = None

    df = df[columnas_salida].copy()

    df["FechaEjecucion"] = pd.Timestamp.now()

    columnas_finales = ["FechaEjecucion"] + columnas_salida

    df = df[columnas_finales]

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].replace({np.nan: None})
        else:
            df[col] = df[col].where(pd.notna(df[col]), None)

    return df


def cargar_resultado_bdd_idm(conn, top3):
    df = preparar_resultado_sql(top3)

    cursor = conn.cursor()

    cursor.execute(f"""
    IF OBJECT_ID(N'{TABLA_RESULTADO_BDD}', N'U') IS NOT NULL
        DROP TABLE {TABLA_RESULTADO_BDD};

    CREATE TABLE {TABLA_RESULTADO_BDD} (
        FechaEjecucion DATETIME2 NULL,
        Identificador VARCHAR(30) NULL,
        Estudiante NVARCHAR(255) NULL,
        MailUDLA NVARCHAR(255) NULL,
        Genero NVARCHAR(20) NULL,
        CarreraHom NVARCHAR(255) NULL,
        desfacultad NVARCHAR(255) NULL,
        Titulo NVARCHAR(255) NULL,
        FechaGraduacion DATE NULL,
        Modalidad NVARCHAR(100) NULL,
        Semestre NVARCHAR(50) NULL,
        NOMEMP NVARCHAR(255) NULL,
        TIPOEMPRES NVARCHAR(255) NULL,
        OCUPAFI NVARCHAR(255) NULL,
        SALARIO FLOAT NULL,
        FECINGAFI DATE NULL,
        TieneInformacionLaboral NVARCHAR(100) NULL,
        FuenteInformacionLaboral NVARCHAR(100) NULL,
        TamanoEmpresaLinkedIn NVARCHAR(100) NULL,
        PaisTrabajoLinkedIn NVARCHAR(255) NULL,
        AnioGraduacionLinkedIn NVARCHAR(50) NULL,
        AniosEnCargo FLOAT NULL,
        AniosDesdeGraduacion FLOAT NULL,
        YaEstudioPosgradoUDLA NVARCHAR(10) NULL,
        PosgradosUDLAPrevios NVARCHAR(MAX) NULL,
        LineasPosgradoPrevias NVARCHAR(MAX) NULL,
        RestriccionAcademica NVARCHAR(100) NULL,
        Recomendacion_1 NVARCHAR(100) NULL,
        Score_1 FLOAT NULL,
        Programas_UDLA_1 NVARCHAR(MAX) NULL,
        Recomendacion_2 NVARCHAR(100) NULL,
        Score_2 FLOAT NULL,
        Programas_UDLA_2 NVARCHAR(MAX) NULL,
        Recomendacion_3 NVARCHAR(100) NULL,
        Score_3 FLOAT NULL,
        Programas_UDLA_3 NVARCHAR(MAX) NULL,
        Justificacion_Recomendacion_1 NVARCHAR(MAX) NULL
    );
    """)

    conn.commit()

    columnas = df.columns.tolist()

    placeholders = ",".join(["?"] * len(columnas))
    columnas_sql = ",".join([f"[{c}]" for c in columnas])

    insert_sql = f"""
    INSERT INTO {TABLA_RESULTADO_BDD} ({columnas_sql})
    VALUES ({placeholders});
    """

    registros = []

    for _, row in df.iterrows():
        fila = []

        for col in columnas:
            valor = row[col]

            if pd.isna(valor):
                valor = None

            if isinstance(valor, pd.Timestamp):
                valor = valor.to_pydatetime()

            fila.append(valor)

        registros.append(tuple(fila))

    cursor.fast_executemany = True
    cursor.executemany(insert_sql, registros)
    conn.commit()

    return len(registros)
