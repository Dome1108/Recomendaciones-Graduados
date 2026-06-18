import pandas as pd
import numpy as np

from utils_texto import normalizar_texto
from reglas_recomendacion import (
    REGLAS_PREGRADO,
    REGLAS_SECTOR,
    REGLAS_CARGO
)


def sumar_reglas(texto, reglas, scores):
    texto = normalizar_texto(texto)

    for palabra, linea, puntos in reglas:
        if palabra in texto:
            scores[linea] = scores.get(linea, 0) + puntos

    return scores


def puntos_experiencia(anios_cargo, linea):
    if pd.isna(anios_cargo):
        return 0

    try:
        anios_cargo = float(anios_cargo)
    except Exception:
        return 0

    if linea in ["MBA_ADMINISTRACION", "GESTION_PROYECTOS"]:
        if anios_cargo >= 5:
            return 10
        elif anios_cargo >= 3:
            return 7
        elif anios_cargo >= 1:
            return 4
        else:
            return 2

    if 1 <= anios_cargo <= 5:
        return 10
    elif anios_cargo > 5:
        return 8
    elif anios_cargo < 1:
        return 5

    return 0


def recomendar_lineas(row):
    scores = {}

    texto_pregrado = " ".join([
        normalizar_texto(row.get("CarreraHom", "")),
        normalizar_texto(row.get("Titulo", "")),
        normalizar_texto(row.get("desfacultad", ""))
    ])

    texto_sector = " ".join([
        normalizar_texto(row.get("TIPOEMPRES", "")),
        normalizar_texto(row.get("NOMEMP", ""))
    ])

    texto_cargo = normalizar_texto(row.get("OCUPAFI", ""))

    scores = sumar_reglas(texto_pregrado, REGLAS_PREGRADO, scores)
    scores = sumar_reglas(texto_sector, REGLAS_SECTOR, scores)
    scores = sumar_reglas(texto_cargo, REGLAS_CARGO, scores)

    for linea in list(scores.keys()):
        scores[linea] += puntos_experiencia(row.get("AniosEnCargo", np.nan), linea)

    scores = {k: min(v, 100) for k, v in scores.items()}

    if len(scores) == 0:
        return pd.DataFrame(columns=["LineaMaestria", "Score"])

    resultado = (
        pd.DataFrame(scores.items(), columns=["LineaMaestria", "Score"])
        .sort_values("Score", ascending=False)
        .reset_index(drop=True)
    )

    return resultado


def generar_justificacion(row):
    rec = row.get("Recomendacion_1", "")
    carrera = row.get("CarreraHom", "")
    estado_laboral = row.get("TieneInformacionLaboral", "")
    fuente_laboral = row.get("FuenteInformacionLaboral", "")
    ya_posgrado = row.get("YaEstudioPosgradoUDLA", "")
    restriccion = row.get("RestriccionAcademica", "")

    if restriccion == "MEDICINA":
        return (
            f"Recomendación restringida por formación de pregrado en {carrera}. "
            f"Se priorizan únicamente programas compatibles con Medicina o gestión en salud, "
            f"evitando cruces hacia especialidades odontológicas."
        )

    if restriccion == "ODONTOLOGIA":
        return (
            f"Recomendación restringida por formación de pregrado en {carrera}. "
            f"Se priorizan únicamente programas compatibles con Odontología o gestión en salud, "
            f"evitando cruces hacia especialidades médicas."
        )

    if restriccion == "SALUD_GENERAL":
        return (
            f"Recomendación restringida por formación de pregrado en el área de salud. "
            f"Se priorizan programas compatibles con gestión o desarrollo profesional en salud."
        )

    if ya_posgrado == "Sí":
        return (
            f"Este graduado ya registra posgrado previo en UDLA. "
            f"La recomendación prioriza alternativas complementarias a su trayectoria previa. "
            f"Línea principal sugerida: {rec}."
        )

    if estado_laboral == "Sin información laboral":
        if rec == "FINANZAS_BANCA":
            return f"Recomendación basada principalmente en su formación de pregrado en {carrera}, con afinidad hacia finanzas, banca o gestión financiera."
        if rec == "ANALITICA_DATOS":
            return f"Recomendación basada principalmente en su formación de pregrado en {carrera}, con potencial de fortalecimiento en análisis de información y toma de decisiones."
        if rec == "MBA_ADMINISTRACION":
            return f"Recomendación transversal basada en su pregrado en {carrera}, orientada a gestión, administración y desarrollo profesional."
        if rec == "GESTION_PROYECTOS":
            return f"Recomendación transversal basada en su pregrado en {carrera}, orientada a planificación y gestión de proyectos."
        if rec in ["SALUD_MEDICINA", "SALUD_ODONTOLOGIA", "SALUD_GESTION"]:
            return f"Recomendación basada principalmente en su formación de pregrado en {carrera}, con continuidad hacia programas del área de salud."
        if rec == "DERECHO_LEGAL":
            return f"Recomendación basada en su formación de pregrado en {carrera}, con continuidad hacia áreas legales o regulatorias."

        return f"Recomendación generada principalmente por su formación académica de pregrado en {carrera}."

    if fuente_laboral == "LINKEDIN":
        fuente_txt = "La información laboral proviene de LinkedIn como fuente secundaria."
    elif fuente_laboral == "SIM":
        fuente_txt = "La información laboral proviene de la fuente formal SIM."
    else:
        fuente_txt = ""

    if rec == "FINANZAS_BANCA":
        return f"Alta afinidad por formación en {carrera} y relación con análisis, banca o gestión financiera. {fuente_txt}"

    if rec == "ANALITICA_DATOS":
        return f"Alta afinidad por perfil analítico y potencial uso de información para toma de decisiones. {fuente_txt}"

    if rec == "MBA_ADMINISTRACION":
        return f"Recomendación orientada a crecimiento profesional hacia coordinación, jefatura, dirección o gestión empresarial. {fuente_txt}"

    if rec == "GESTION_PROYECTOS":
        return f"Recomendación transversal para fortalecer capacidades de planificación, ejecución y control de proyectos. {fuente_txt}"

    if rec == "DERECHO_LEGAL":
        return f"Alta afinidad por formación o experiencia relacionada con temas jurídicos, legales o regulatorios. {fuente_txt}"

    if rec in ["SALUD_MEDICINA", "SALUD_ODONTOLOGIA", "SALUD_GESTION"]:
        return f"Alta afinidad por formación o trayectoria relacionada con el área de salud. {fuente_txt}"

    if rec == "TECNOLOGIA":
        return f"Alta afinidad por experiencia o formación relacionada con software, sistemas o transformación digital. {fuente_txt}"

    if rec == "MARKETING_COMERCIAL":
        return f"Recomendación asociada a funciones comerciales, ventas, mercado o desarrollo de negocios. {fuente_txt}"

    if rec == "EDUCACION":
        return f"Recomendación asociada a trayectoria en instituciones educativas, docencia o gestión académica. {fuente_txt}"

    return "Recomendación generada por coincidencia entre formación académica, trayectoria laboral y años de experiencia."
