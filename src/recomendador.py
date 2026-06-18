import pandas as pd
import numpy as np

from utils_texto import normalizar_texto
from reglas_recomendacion import (
    REGLAS_PREGRADO,
    REGLAS_SECTOR,
    REGLAS_CARGO
)


def sumar_reglas(texto, reglas, scores):
    """
    Suma puntos a cada línea de maestría cuando encuentra coincidencias
    en el texto analizado.
    """

    texto = normalizar_texto(texto)

    for palabra, linea, puntos in reglas:
        if palabra in texto:
            scores[linea] = scores.get(linea, 0) + puntos

    return scores


def puntos_experiencia(anios_cargo, linea):
    """
    Asigna puntos por años en el cargo.
    Para líneas gerenciales, más experiencia suma más.
    Para líneas técnicas, entre 1 y 5 años tiene alta afinidad.
    """

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
    """
    Genera ranking de líneas recomendadas para un graduado.
    Usa carrera, título, facultad, empresa, tipo de empresa, cargo y años en cargo.
    """

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
    """
    Genera una explicación textual para la recomendación principal.
    """

    rec = row.get("Recomendacion_1", "")
    carrera = row.get("CarreraHom", "")
    empresa = row.get("NOMEMP", "")
    cargo = row.get("OCUPAFI", "")
    estado_laboral = row.get("TieneInformacionLaboral", "")

    if estado_laboral == "Sin información laboral":
        if rec == "FINANZAS_BANCA":
            return f"Recomendación basada principalmente en su formación de pregrado en {carrera}, con afinidad hacia finanzas, banca o gestión financiera."
        if rec == "ANALITICA_DATOS":
            return f"Recomendación basada principalmente en su formación de pregrado en {carrera}, con potencial de fortalecimiento en análisis de información y toma de decisiones."
        if rec == "MBA_ADMINISTRACION":
            return f"Recomendación transversal basada en su pregrado en {carrera}, orientada a gestión, administración y desarrollo profesional."
        if rec == "GESTION_PROYECTOS":
            return f"Recomendación transversal basada en su pregrado en {carrera}, orientada a planificación y gestión de proyectos."
        if rec == "SALUD_GESTION":
            return f"Recomendación basada en su formación de pregrado en {carrera}, con orientación hacia gestión en salud."
        if rec == "DERECHO_LEGAL":
            return f"Recomendación basada en su formación de pregrado en {carrera}, con continuidad hacia áreas legales o regulatorias."

        return f"Recomendación generada principalmente por su formación académica de pregrado en {carrera}."

    if rec == "FINANZAS_BANCA":
        return f"Alta afinidad por formación en {carrera}, experiencia laboral en {empresa} y relación con análisis, banca o gestión financiera."

    if rec == "ANALITICA_DATOS":
        return f"Alta afinidad por perfil analítico, experiencia como {cargo} y potencial uso de información para toma de decisiones."

    if rec == "MBA_ADMINISTRACION":
        return "Recomendación orientada a crecimiento profesional hacia coordinación, jefatura, dirección o gestión empresarial."

    if rec == "GESTION_PROYECTOS":
        return "Recomendación transversal para fortalecer capacidades de planificación, ejecución y control de proyectos."

    if rec == "DERECHO_LEGAL":
        return "Alta afinidad por formación o experiencia relacionada con temas jurídicos, legales o regulatorios."

    if rec == "SALUD_GESTION":
        return "Alta afinidad por formación o experiencia en el sector salud, con potencial desarrollo hacia gestión sanitaria o administrativa."

    if rec == "TECNOLOGIA":
        return "Alta afinidad por experiencia o formación relacionada con software, sistemas o transformación digital."

    if rec == "MARKETING_COMERCIAL":
        return "Recomendación asociada a funciones comerciales, ventas, mercado o desarrollo de negocios."

    if rec == "EDUCACION":
        return "Recomendación asociada a trayectoria en instituciones educativas, docencia o gestión académica."

    return "Recomendación generada por coincidencia entre formación académica, sector laboral, cargo y años de experiencia."
