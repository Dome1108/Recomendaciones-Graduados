import re
import unicodedata
import pandas as pd


def normalizar_texto(x):
    """
    Normaliza texto para facilitar cruces por palabras clave.
    Convierte a mayúsculas, elimina tildes y espacios duplicados.
    """

    if pd.isna(x):
        return ""

    x = str(x).upper().strip()
    x = unicodedata.normalize("NFKD", x)
    x = "".join([c for c in x if not unicodedata.combining(c)])
    x = re.sub(r"\s+", " ", x)

    return x
