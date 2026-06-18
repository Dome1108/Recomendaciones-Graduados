import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path


st.set_page_config(
    page_title="Recomendador de Maestrías UDLA",
    page_icon="🎓",
    layout="wide"
)


BASE_DIR = Path(__file__).parent
RUTA_EXCEL = BASE_DIR / "outputs" / "recomendaciones_maestrias_udla.xlsx"


@st.cache_data
def cargar_datos():
    if not RUTA_EXCEL.exists():
        return None, None, None, None

    top3 = pd.read_excel(RUTA_EXCEL, sheet_name="Top3_por_graduado")
    recomendaciones_larga = pd.read_excel(RUTA_EXCEL, sheet_name="Recomendaciones_larga")
    base = pd.read_excel(RUTA_EXCEL, sheet_name="Base_graduados_laboral")
    catalogo_lineas = pd.read_excel(RUTA_EXCEL, sheet_name="Lineas_catalogo")

    return top3, recomendaciones_larga, base, catalogo_lineas


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


top3, recomendaciones_larga, base, catalogo_lineas = cargar_datos()

st.title("🎓 Recomendador de Maestrías para Graduados UDLA")
st.caption("Dashboard de apoyo para consultores de ventas y admisiones.")

if top3 is None:
    st.error(
        "No se encontró el archivo de resultados. Primero ejecuta el pipeline para generar "
        "`outputs/recomendaciones_maestrias_udla.xlsx`."
    )
    st.stop()


top3 = top3.copy()

for col in top3.columns:
    if top3[col].dtype == "object":
        top3[col] = top3[col].fillna("")

if "TieneInformacionLaboral" not in top3.columns:
    top3["TieneInformacionLaboral"] = top3["NOMEMP"].apply(
        lambda x: "Sin información laboral"
        if limpiar_texto(x).strip() in ["", "Sin información laboral"]
        else "Con información laboral"
    )

for col in ["Score_1", "Score_2", "Score_3", "AniosEnCargo", "AniosDesdeGraduacion"]:
    if col in top3.columns:
        top3[col] = pd.to_numeric(top3[col], errors="coerce")

top3["EtiquetaBusqueda"] = (
    top3["Identificador"].astype(str)
    + " | "
    + top3["Estudiante"].astype(str)
    + " | "
    + top3["CarreraHom"].astype(str)
)


st.sidebar.header("Filtros")

estado_laboral = st.sidebar.multiselect(
    "Información laboral",
    options=sorted(top3["TieneInformacionLaboral"].dropna().unique()),
    default=sorted(top3["TieneInformacionLaboral"].dropna().unique())
)

carreras = st.sidebar.multiselect(
    "Carrera de pregrado",
    options=sorted(top3["CarreraHom"].dropna().unique()),
    default=[]
)

recomendaciones_disponibles = sorted(
    pd.concat([
        top3.get("Recomendacion_1", pd.Series(dtype=str)),
        top3.get("Recomendacion_2", pd.Series(dtype=str)),
        top3.get("Recomendacion_3", pd.Series(dtype=str))
    ]).dropna().astype(str).unique()
)

filtro_recomendacion = st.sidebar.multiselect(
    "Línea recomendada",
    options=recomendaciones_disponibles,
    default=[]
)

busqueda = st.sidebar.text_input(
    "Buscar graduado",
    placeholder="Nombre, cédula o carrera"
)


df_filtrado = top3.copy()

if estado_laboral:
    df_filtrado = df_filtrado[df_filtrado["TieneInformacionLaboral"].isin(estado_laboral)]

if carreras:
    df_filtrado = df_filtrado[df_filtrado["CarreraHom"].isin(carreras)]

if filtro_recomendacion:
    df_filtrado = df_filtrado[
        df_filtrado["Recomendacion_1"].isin(filtro_recomendacion)
        | df_filtrado["Recomendacion_2"].isin(filtro_recomendacion)
        | df_filtrado["Recomendacion_3"].isin(filtro_recomendacion)
    ]

if busqueda.strip():
    b = busqueda.upper().strip()
    df_filtrado = df_filtrado[
        df_filtrado["EtiquetaBusqueda"].str.upper().str.contains(b, na=False)
    ]


col1, col2, col3, col4 = st.columns(4)

col1.metric("Graduados con recomendación", len(top3))
col2.metric(
    "Con información laboral",
    int((top3["TieneInformacionLaboral"] == "Con información laboral").sum())
)
col3.metric(
    "Sin información laboral",
    int((top3["TieneInformacionLaboral"] == "Sin información laboral").sum())
)
col4.metric("Casos filtrados", len(df_filtrado))


st.divider()


tab1, tab2, tab3 = st.tabs([
    "Consulta individual",
    "Resumen general",
    "Base de recomendaciones"
])


with tab1:
    st.subheader("Consulta individual del graduado")

    if df_filtrado.empty:
        st.warning("No hay graduados con los filtros seleccionados.")
        st.stop()

    opcion = st.selectbox(
        "Selecciona un graduado",
        options=df_filtrado["EtiquetaBusqueda"].tolist()
    )

    row = df_filtrado[df_filtrado["EtiquetaBusqueda"] == opcion].iloc[0]

    st.markdown("### Perfil del graduado")

    p1, p2, p3, p4 = st.columns(4)

    p1.markdown(f"**Identificador:**  \n{row.get('Identificador', '')}")
    p2.markdown(f"**Estudiante:**  \n{row.get('Estudiante', '')}")
    p3.markdown(f"**Pregrado:**  \n{row.get('CarreraHom', '')}")
    p4.markdown(f"**Título:**  \n{row.get('Titulo', '')}")

    p5, p6, p7, p8 = st.columns(4)

    p5.markdown(f"**Estado laboral:**  \n{row.get('TieneInformacionLaboral', '')}")
    p6.markdown(f"**Empresa:**  \n{row.get('NOMEMP', '')}")
    p7.markdown(f"**Cargo/Ocupación:**  \n{row.get('OCUPAFI', '')}")
    p8.markdown(f"**Años en cargo:**  \n{row.get('AniosEnCargo', '')}")

    st.info(row.get("Justificacion_Recomendacion_1", ""))

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


with tab2:
    st.subheader("Resumen general")

    c1, c2 = st.columns(2)

    resumen_estado = (
        top3["TieneInformacionLaboral"]
        .value_counts()
        .reset_index()
    )
    resumen_estado.columns = ["Estado laboral", "Cantidad"]

    fig_estado = px.pie(
        resumen_estado,
        names="Estado laboral",
        values="Cantidad",
        title="Distribución por información laboral"
    )

    c1.plotly_chart(fig_estado, use_container_width=True)

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

    c2.plotly_chart(fig_rec, use_container_width=True)

    st.markdown("### Recomendaciones por carrera")

    if "CarreraHom" in top3.columns and "Recomendacion_1" in top3.columns:
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


with tab3:
    st.subheader("Base general de recomendaciones")

    columnas_tabla = [
        "Identificador",
        "Estudiante",
        "CarreraHom",
        "Titulo",
        "TieneInformacionLaboral",
        "NOMEMP",
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
