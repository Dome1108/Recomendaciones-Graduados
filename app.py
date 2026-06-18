import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px


st.set_page_config(
    page_title="Recomendador de Maestrías UDLA",
    page_icon="🎓",
    layout="wide"
)


BASE_DIR = Path(__file__).parent
SRC_DIR = BASE_DIR / "src"
sys.path.append(str(SRC_DIR))

from conexion_sql import conectar_sql


RUTA_EXCEL = BASE_DIR / "outputs" / "recomendaciones_maestrias_udla.xlsx"
TABLA_SQL = "BDD_IDM.dbo.Recomendaciones_Maestrias_Graduados"


@st.cache_data
def cargar_datos():
    try:
        conn = conectar_sql()
        query = f"""
        SELECT *
        FROM {TABLA_SQL};
        """
        top3 = pd.read_sql(query, conn)
        fuente = f"SQL: {TABLA_SQL}"
        return top3, fuente
    except Exception:
        if not RUTA_EXCEL.exists():
            return None, "Sin fuente"

        top3 = pd.read_excel(RUTA_EXCEL, sheet_name="Top3_por_graduado")
        fuente = f"Excel local: {RUTA_EXCEL}"
        return top3, fuente


def limpiar_texto(x):
    if pd.isna(x):
        return ""
    return str(x)


def formato_score(x):
    try:
        if pd.isna(x):
            return "Sin score"
        return f"{float(x):.0f}"
    except Exception:
        return str(x)


def mostrar_card_recomendacion(numero, recomendacion, score, programas):
    recomendacion = limpiar_texto(recomendacion)
    programas = limpiar_texto(programas)
    score = formato_score(score)

    st.markdown(
        f"""
        <div style="
            border:1px solid #E5E7EB;
            border-radius:16px;
            padding:18px;
            margin-bottom:12px;
            background-color:#FFFFFF;
            box-shadow:0 2px 8px rgba(0,0,0,0.04);
            min-height:260px;
        ">
            <p style="font-size:14px;color:#6B7280;margin-bottom:6px;">Recomendación {numero}</p>
            <h3 style="margin-top:0;color:#A5133D;">{recomendacion}</h3>
            <p style="font-size:18px;"><b>Score:</b> {score}</p>
            <p><b>Programas UDLA sugeridos:</b><br>{programas}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


top3, fuente = cargar_datos()

st.title("🎓 Recomendador de Maestrías para Graduados UDLA")
st.caption("Dashboard de apoyo para consultores de ventas y admisiones.")

if top3 is None:
    st.error(
        "No se encontró información. Primero ejecuta el pipeline para cargar "
        "BDD_IDM.dbo.Recomendaciones_Maestrias_Graduados o generar el Excel local."
    )
    st.stop()

st.caption(f"Fuente de datos: {fuente}")

top3 = top3.copy()

for col in top3.columns:
    if top3[col].dtype == "object":
        top3[col] = top3[col].fillna("")

for col in ["Score_1", "Score_2", "Score_3", "AniosEnCargo", "AniosDesdeGraduacion"]:
    if col in top3.columns:
        top3[col] = pd.to_numeric(top3[col], errors="coerce")

if "TieneInformacionLaboral" not in top3.columns:
    top3["TieneInformacionLaboral"] = "Sin información laboral"

if "FuenteInformacionLaboral" not in top3.columns:
    top3["FuenteInformacionLaboral"] = "SIN_INFORMACION_LABORAL"

if "YaEstudioPosgradoUDLA" not in top3.columns:
    top3["YaEstudioPosgradoUDLA"] = "No"

if "RestriccionAcademica" not in top3.columns:
    top3["RestriccionAcademica"] = "SIN_RESTRICCION"

top3["EtiquetaBusqueda"] = (
    top3["Identificador"].astype(str)
    + " | "
    + top3["Estudiante"].astype(str)
    + " | "
    + top3["CarreraHom"].astype(str)
)


st.sidebar.header("Filtros generales")

opciones_laboral_base = ["Con información laboral", "Sin información laboral"]
opciones_laboral_extra = [
    x for x in sorted(top3["TieneInformacionLaboral"].dropna().unique())
    if x not in opciones_laboral_base
]
opciones_laboral = opciones_laboral_base + opciones_laboral_extra

estado_laboral = st.sidebar.multiselect(
    "Información laboral",
    options=opciones_laboral,
    default=opciones_laboral
)

opciones_posgrado_base = ["No", "Sí"]
opciones_posgrado_extra = [
    x for x in sorted(top3["YaEstudioPosgradoUDLA"].dropna().unique())
    if x not in opciones_posgrado_base
]
opciones_posgrado = opciones_posgrado_base + opciones_posgrado_extra

filtro_posgrado = st.sidebar.multiselect(
    "Ya estudió posgrado UDLA",
    options=opciones_posgrado,
    default=opciones_posgrado
)

carreras = st.sidebar.multiselect(
    "Carrera de pregrado",
    options=sorted(top3["CarreraHom"].dropna().unique()),
    default=[]
)

restricciones = st.sidebar.multiselect(
    "Restricción académica",
    options=sorted(top3["RestriccionAcademica"].dropna().unique()),
    default=[]
)

df_filtrado = top3.copy()

if estado_laboral:
    df_filtrado = df_filtrado[df_filtrado["TieneInformacionLaboral"].isin(estado_laboral)]

if filtro_posgrado:
    df_filtrado = df_filtrado[df_filtrado["YaEstudioPosgradoUDLA"].isin(filtro_posgrado)]

if carreras:
    df_filtrado = df_filtrado[df_filtrado["CarreraHom"].isin(carreras)]

if restricciones:
    df_filtrado = df_filtrado[df_filtrado["RestriccionAcademica"].isin(restricciones)]


col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("Graduados con recomendación", len(top3))
col2.metric("Empleo SIM", int((top3["FuenteInformacionLaboral"] == "SIM").sum()))
col3.metric("Empleo LinkedIn", int((top3["FuenteInformacionLaboral"] == "LINKEDIN").sum()))
col4.metric("Sin empleo mapeado", int((top3["TieneInformacionLaboral"] == "Sin información laboral").sum()))
col5.metric("Con posgrado UDLA previo", int((top3["YaEstudioPosgradoUDLA"] == "Sí").sum()))
col6.metric("Casos filtrados", len(df_filtrado))

st.divider()


tab_consultor, tab_resumen, tab_base = st.tabs([
    "Vista consultor",
    "Resumen general",
    "Base de recomendaciones"
])


with tab_consultor:
    st.subheader("Vista consultor")

    busqueda = st.text_input(
        "Buscar por nombre o cédula",
        placeholder="Ejemplo: 172..., Mateo, Economía"
    )

    df_busqueda = df_filtrado.copy()

    if busqueda.strip():
        b = busqueda.upper().strip()
        df_busqueda = df_busqueda[
            df_busqueda["EtiquetaBusqueda"].str.upper().str.contains(b, na=False)
        ]

    if df_busqueda.empty:
        st.warning("No hay graduados con los criterios seleccionados.")
        st.stop()

    opcion = st.selectbox(
        "Selecciona un graduado",
        options=df_busqueda["EtiquetaBusqueda"].tolist()
    )

    row = df_busqueda[df_busqueda["EtiquetaBusqueda"] == opcion].iloc[0]

    st.markdown("### Perfil académico")

    a1, a2, a3, a4 = st.columns(4)

    a1.markdown(f"**Identificador:**  \n{row.get('Identificador', '')}")
    a2.markdown(f"**Estudiante:**  \n{row.get('Estudiante', '')}")
    a3.markdown(f"**Carrera de pregrado:**  \n{row.get('CarreraHom', '')}")
    a4.markdown(f"**Título:**  \n{row.get('Titulo', '')}")

    a5, a6, a7, a8 = st.columns(4)

    a5.markdown(f"**Facultad:**  \n{row.get('desfacultad', '')}")
    a6.markdown(f"**Modalidad:**  \n{row.get('Modalidad', '')}")
    a7.markdown(f"**Años desde graduación:**  \n{row.get('AniosDesdeGraduacion', '')}")
    a8.markdown(f"**Correo UDLA:**  \n{row.get('MailUDLA', '')}")

    st.markdown("### Estado laboral")

    if row.get("TieneInformacionLaboral", "") == "Con información laboral":
        st.success("Registra información laboral.")
    else:
        st.warning("No registra información laboral en las fuentes consultadas.")

    st.markdown("### Historial de posgrado UDLA")

    if row.get("YaEstudioPosgradoUDLA", "No") == "Sí":
        st.warning(
            f"Este graduado ya registra posgrado UDLA previo: "
            f"{row.get('PosgradosUDLAPrevios', '')}"
        )
    else:
        st.success("No registra posgrado UDLA previo en la base.")

    st.markdown("### Restricción académica")

    restriccion = row.get("RestriccionAcademica", "SIN_RESTRICCION")

    if restriccion == "MEDICINA":
        st.info("Por su formación en Medicina, solo se recomiendan programas compatibles con Medicina o gestión en salud. No se muestran especialidades odontológicas.")
    elif restriccion == "ODONTOLOGIA":
        st.info("Por su formación en Odontología, solo se recomiendan programas compatibles con Odontología o gestión en salud. No se muestran especialidades médicas.")
    elif restriccion == "SALUD_GENERAL":
        st.info("Por su formación en el área de salud, se priorizan programas compatibles con gestión o desarrollo profesional en salud.")
    else:
        st.info("No aplica restricción académica específica.")

    st.markdown("### Top 3 recomendaciones")

    r1, r2, r3 = st.columns(3)

    with r1:
        mostrar_card_recomendacion(
            1,
            row.get("Recomendacion_1", "Sin recomendación"),
            row.get("Score_1", ""),
            row.get("Programas_UDLA_1", "")
        )

    with r2:
        mostrar_card_recomendacion(
            2,
            row.get("Recomendacion_2", "Sin recomendación"),
            row.get("Score_2", ""),
            row.get("Programas_UDLA_2", "")
        )

    with r3:
        mostrar_card_recomendacion(
            3,
            row.get("Recomendacion_3", "Sin recomendación"),
            row.get("Score_3", ""),
            row.get("Programas_UDLA_3", "")
        )

    st.info(row.get("Justificacion_Recomendacion_1", ""))

    scores = pd.DataFrame({
        "Recomendación": [
            row.get("Recomendacion_1", ""),
            row.get("Recomendacion_2", ""),
            row.get("Recomendacion_3", "")
        ],
        "Score": [
            row.get("Score_1", 0),
            row.get("Score_2", 0),
            row.get("Score_3", 0)
        ]
    })

    scores["Score"] = pd.to_numeric(scores["Score"], errors="coerce").fillna(0)

    fig = px.bar(
        scores,
        x="Recomendación",
        y="Score",
        text="Score",
        title="Afinidad de recomendaciones"
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis_range=[0, 100])

    st.plotly_chart(fig, use_container_width=True)


with tab_resumen:
    st.subheader("Resumen general")

    c1, c2 = st.columns(2)

    resumen_fuente = (
        top3["FuenteInformacionLaboral"]
        .value_counts()
        .reset_index()
    )
    resumen_fuente.columns = ["Fuente laboral", "Cantidad"]

    fig_fuente = px.pie(
        resumen_fuente,
        names="Fuente laboral",
        values="Cantidad",
        title="Distribución por fuente laboral"
    )

    c1.plotly_chart(fig_fuente, use_container_width=True)

    resumen_posgrado = (
        top3["YaEstudioPosgradoUDLA"]
        .value_counts()
        .reset_index()
    )
    resumen_posgrado.columns = ["Ya estudió posgrado UDLA", "Cantidad"]

    fig_posgrado = px.pie(
        resumen_posgrado,
        names="Ya estudió posgrado UDLA",
        values="Cantidad",
        title="Graduados con posgrado UDLA previo"
    )

    c2.plotly_chart(fig_posgrado, use_container_width=True)

    resumen_rec = (
        top3["Recomendacion_1"]
        .value_counts()
        .reset_index()
        .head(15)
    )
    resumen_rec.columns = ["Recomendación principal", "Cantidad"]

    fig_rec = px.bar(
        resumen_rec,
        x="Cantidad",
        y="Recomendación principal",
        orientation="h",
        text="Cantidad",
        title="Top líneas recomendadas"
    )

    fig_rec.update_layout(yaxis={"categoryorder": "total ascending"})

    st.plotly_chart(fig_rec, use_container_width=True)

    st.markdown("### Recomendaciones por carrera")

    resumen_carrera = (
        top3.groupby(["CarreraHom", "Recomendacion_1"])
        .size()
        .reset_index(name="Cantidad")
        .sort_values("Cantidad", ascending=False)
        .head(30)
    )

    fig_carrera = px.bar(
        resumen_carrera,
        x="Cantidad",
        y="CarreraHom",
        color="Recomendacion_1",
        orientation="h",
        title="Principales recomendaciones por carrera"
    )

    fig_carrera.update_layout(yaxis={"categoryorder": "total ascending"})

    st.plotly_chart(fig_carrera, use_container_width=True)


with tab_base:
    st.subheader("Base general de recomendaciones")

    columnas_tabla = [
        "Identificador",
        "Estudiante",
        "MailUDLA",
        "CarreraHom",
        "desfacultad",
        "Titulo",
        "TieneInformacionLaboral",
        "FuenteInformacionLaboral",
        "AniosDesdeGraduacion",
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

    columnas_tabla = [c for c in columnas_tabla if c in df_filtrado.columns]

    st.dataframe(
        df_filtrado[columnas_tabla],
        use_container_width=True,
        hide_index=True
    )

    csv = df_filtrado[columnas_tabla].to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="Descargar base filtrada CSV",
        data=csv,
        file_name="recomendaciones_filtradas.csv",
        mime="text/csv"
    )
