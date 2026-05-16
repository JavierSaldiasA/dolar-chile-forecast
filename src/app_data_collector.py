import streamlit as st
import bcchapi
import pandas as pd
import numpy as np
import os
from datetime import datetime
from dotenv import load_dotenv


# =============================================================================
# DICCIONARIOS Y CONFIGURACION
# =============================================================================
FRECUENCIAS_ES_EN = {
    "Todas": None,
    "Diaria": "DAILY",
    "Mensual": "MONTHLY",
    "Trimestral": "QUARTERLY",
    "Anual": "ANNUAL"
}

FRECUENCIAS_EN_ES = {
    "DAILY": "Diaria",
    "MONTHLY": "Mensual",
    "QUARTERLY": "Trimestral",
    "ANNUAL": "Anual"
}

# Nivel de desagregacion (menor numero = mas desagregada)
FRECUENCIA_NIVEL = {
    "DAILY": 1,
    "MONTHLY": 2,
    "QUARTERLY": 3,
    "ANNUAL": 4
}

AGREGACIONES = {
    "Promedio": np.mean,
    "Mínimo": np.min,
    "Máximo": np.max,
    "Mediana": np.median,
    "Último valor": "last",
    "Suma": np.sum,
    "Primer valor": "first"
}

IMPUTACIONES = {
    "Sin imputacion (dejar NaN)": None,
    "Forward fill (ultimo valor valido)": "ffill",
    "Backward fill (proximo valor valido)": "bfill",
    "Interpolacion lineal": "linear",
    "Interpolacion polinomica (orden 2)": "polynomial",
    "Rellenar con cero": "zero",
    "Rellenar con promedio": "mean"
}

# Inicializar session_state
if 'series_seleccionadas' not in st.session_state:
    st.session_state.series_seleccionadas = []
if 'resultados_busqueda' not in st.session_state:
    st.session_state.resultados_busqueda = None
if 'ultima_busqueda' not in st.session_state:
    st.session_state.ultima_busqueda = ""
if 'busqueda_realizada' not in st.session_state:
    st.session_state.busqueda_realizada = False


# =============================================================================
# CONFIGURACION DE PAGINA
# =============================================================================
st.set_page_config(
    page_title="BCCH Data Collector Pro",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1f4e79; text-align: center; margin-bottom: 1rem; }
    .sub-header { font-size: 1.2rem; color: #555; text-align: center; margin-bottom: 2rem; }
    .stButton>button { background-color: #1f4e79; color: white; border-radius: 8px; padding: 0.5rem 2rem; }
    .stButton>button:hover { background-color: #2e6ea5; }
    .seleccion-badge { background-color: #e8f4f8; border-left: 4px solid #1f4e79; padding: 0.5rem 1rem; margin: 0.3rem 0; border-radius: 4px; }
    .info-box { 
        background-color: #e3f2fd; 
        border-left: 4px solid #1976d2; 
        color: #0d47a1;
        border-radius: 8px; 
        padding: 1rem; 
        margin: 1rem 0; 
    }
    .info-box b { color: #0d47a1; }
    .warning-box {
        background-color: #fff3e0;
        border-left: 4px solid #f57c00;
        color: #e65100;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #e8f5e9;
        border-left: 4px solid #388e3c;
        color: #1b5e20;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================
def obtener_credenciales():
    load_dotenv()
    return os.getenv("BCCH_EMAIL"), os.getenv("BCCH_PASSWORD")


def aplicar_imputacion(df, metodo):
    """
    Aplica metodo de imputacion a un DataFrame.
    """
    if metodo is None:
        return df
    
    df_result = df.copy()
    
    if metodo == "ffill":
        df_result = df_result.ffill()
    elif metodo == "bfill":
        df_result = df_result.bfill()
    elif metodo == "linear":
        df_result = df_result.interpolate(method="linear")
    elif metodo == "polynomial":
        df_result = df_result.interpolate(method="polynomial", order=2)
    elif metodo == "zero":
        df_result = df_result.fillna(0)
    elif metodo == "mean":
        df_result = df_result.fillna(df_result.mean())
    
    return df_result

def detectar_frecuencia_por_id(series_id):
    """
    Detecta la frecuencia de una serie a partir de la ultima letra del ID.
    
    Parameters:
        series_id (str): ID de la serie (ej: "F073.TCO.PRE.Z.D")
    
    Returns:
        str: Frecuencia en ingles (DAILY, MONTHLY, etc.) o "UNKNOWN" si no se reconoce
    """
    if not series_id or not isinstance(series_id, str):
        return "DAILY"  # Default por seguridad
    
    # Obtener la ultima letra (ignorando espacios)
    ultima_letra = series_id.strip()[-1].upper()
    
    mapeo = {
        "D": "DAILY",
        "M": "MONTHLY",
        "Q": "QUARTERLY",
        "A": "ANNUAL",
    }
    
    return mapeo.get(ultima_letra, "DAILY")

def determinar_modo_operacion(series_seleccionadas, frecuencia_salida_es):
    """
    Determina si se necesita agregacion, imputacion o ambas.
    
    Returns:
        tuple: (necesita_agregacion, necesita_imputacion, mensaje)
    """
    if frecuencia_salida_es == "Original (sin cambios)":
        return False, False, "Sin cambios de frecuencia"
    
    # Obtener nivel de frecuencia de salida
    freq_salida_en = FRECUENCIAS_ES_EN[frecuencia_salida_es]
    nivel_salida = FRECUENCIA_NIVEL[freq_salida_en]
    
    # Obtener niveles de las series seleccionadas
    niveles_series = []
    for serie in series_seleccionadas:
        freq_orig = serie.get("frecuencia_original", "DAILY")
        if freq_orig in FRECUENCIA_NIVEL:
            niveles_series.append(FRECUENCIA_NIVEL[freq_orig])
    
    if not niveles_series:
        # Si no conocemos las frecuencias (IDs directos o CSV), ofrecer todo
        return True, True, "Modo manual: selecciona agregacion, imputacion o ambas segun necesites"
    
    nivel_min = min(niveles_series)  # Mas desagregada
    nivel_max = max(niveles_series)  # Menos desagregada
    
    if nivel_salida <= nivel_min:
        # Salida igual o mas desagregada que la serie mas desagregada
        # Solo imputacion (para las series menos desagregadas)
        return False, True, f"Frecuencia de salida mas desagregada. Se ofrece imputacion para series con frecuencia menor."
    
    elif nivel_salida >= nivel_max:
        # Salida igual o menos desagregada que la serie menos desagregada
        # Solo agregacion (para las series mas desagregadas)
        return True, False, f"Frecuencia de salida menos desagregada. Se ofrece agregacion para series con frecuencia mayor."
    
    else:
        # Salida intermedia
        # Ambas: agregar las mas desagregadas, imputar las menos desagregadas
        return True, True, f"Frecuencia de salida intermedia. Se ofrece agregacion para series mas desagregadas e imputacion para las menos desagregadas."


# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown('<div style="text-align: center;"><h2>🏛️ BCCH</h2><p style="color: #888; font-size: 0.9rem;">Data Collector Pro</p></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.header("🔐 Credenciales")
    
    use_env = st.checkbox("Usar archivo .env", value=True, key="chk_env")
    
    if use_env:
        email, password = obtener_credenciales()
        if email:
            st.success("✅ Credenciales cargadas desde .env")
        else:
            st.warning("⚠️ No se encontraron credenciales en .env")
            email = st.text_input("Email", key="email_env")
            password = st.text_input("Contraseña", type="password", key="pass_env")
    else:
        email = st.text_input("Email", key="email_manual")
        password = st.text_input("Contraseña", type="password", key="pass_manual")
    
    st.markdown("---")
    
    # Mostrar series seleccionadas en sidebar
    if st.session_state.series_seleccionadas:
        st.subheader(f"📋 Series en carrito ({len(st.session_state.series_seleccionadas)})")
        for i, serie in enumerate(st.session_state.series_seleccionadas):
            st.markdown(
                f'<div class="seleccion-badge" style="color: #666;">'
                f'<b>{serie["nombre"]}</b><br>'
                f'<small>{serie["id"]}</small>'
                f'</div>',
                unsafe_allow_html=True
            )
        
        col_limpiar = st.columns([1])
        with col_limpiar[0]:
            if st.button("🗑️ Limpiar todo", use_container_width=True, key="btn_limpiar_sidebar"):
                st.session_state.series_seleccionadas = []
                st.rerun()
    
    st.markdown("---")
    st.info("💡 Tip: Crea un archivo .env con BCCH_EMAIL y BCCH_PASSWORD")


# =============================================================================
# HEADER
# =============================================================================
st.markdown('<div class="main-header">🏛️ BCCH Data Collector Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Herramienta profesional para descargar datos del Banco Central de Chile</div>', unsafe_allow_html=True)
st.markdown("---")


# =============================================================================
# TABS PRINCIPALES
# =============================================================================
tab1, tab2 = st.tabs(["🔍 Buscar y Seleccionar", "⬇️ Descargar Datos"])


# =============================================================================
# TAB 1: BUSCAR Y SELECCIONAR
# =============================================================================
with tab1:
    st.header("Buscar Series del Banco Central")
    
    # Formulario de busqueda
    col1, col2 = st.columns([3, 1])
    
    with col1:
        busqueda = st.text_input(
            "Palabra clave",
            placeholder="Ej: Tipo de Cambio, Cobre, IPC, TPM, UF...",
            key="input_busqueda"
        )
    
    with col2:
        frecuencia_filtro_es = st.selectbox(
            "Filtrar por frecuencia",
            options=list(FRECUENCIAS_ES_EN.keys()),
            key="filtro_freq"
        )
    
    # Botones de accion
    col_b1, col_b2 = st.columns([1, 1])
    with col_b1:
        buscar_btn = st.button("🔍 Buscar", use_container_width=True, key="btn_buscar")
    with col_b2:
        if st.button("🗑️ Limpiar resultados", use_container_width=True, key="btn_limpiar_busqueda"):
            st.session_state.resultados_busqueda = None
            st.session_state.ultima_busqueda = ""
            st.session_state.busqueda_realizada = False
            st.rerun()
    
    # Ejecutar busqueda SOLO cuando se presiona el boton
    if buscar_btn and busqueda.strip():
        with st.spinner("Buscando en el Banco Central..."):
            try:
                siete = bcchapi.Siete(email, password)
                resultados = siete.buscar(busqueda.strip())
                
                # Aplicar filtro de frecuencia
                frecuencia_en = FRECUENCIAS_ES_EN[frecuencia_filtro_es]
                if frecuencia_en:
                    resultados = resultados[resultados["frequencyCode"] == frecuencia_en]
                
                # Guardar en session state
                st.session_state.resultados_busqueda = resultados
                st.session_state.ultima_busqueda = busqueda.strip()
                st.session_state.busqueda_realizada = True
                
            except Exception as e:
                st.error(f"❌ Error en la busqueda: {e}")
                st.info("Verifica tus credenciales y que el termino de busqueda sea valido")
                st.session_state.resultados_busqueda = None
                st.session_state.busqueda_realizada = False
    
    # Mostrar resultados si existen en session_state
    if st.session_state.busqueda_realizada and st.session_state.resultados_busqueda is not None:
        resultados = st.session_state.resultados_busqueda
        total = len(resultados)
        
        if total == 0:
            st.warning(f"⚠️ No se encontraron resultados para '{st.session_state.ultima_busqueda}' con frecuencia '{frecuencia_filtro_es}'")
        else:
            # Mensaje de exito
            st.success(f"✅ Se encontraron **{total} series** para '{st.session_state.ultima_busqueda}'")
            
            # Metricas
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
            freq_counts = resultados["frequencyCode"].value_counts().to_dict()
            
            with col_m1:
                st.metric("Total", total)
            with col_m2:
                st.metric("Diarias", freq_counts.get("DAILY", 0))
            with col_m3:
                st.metric("Mensuales", freq_counts.get("MONTHLY", 0))
            with col_m4:
                st.metric("Trimestrales", freq_counts.get("QUARTERLY", 0))
            with col_m5:
                st.metric("Anuales", freq_counts.get("ANNUAL", 0))
            
            # Preparar dataframe para data_editor
            display_df = resultados[["seriesId", "frequencyCode", "spanishTitle"]].copy()
            display_df["Frecuencia"] = display_df["frequencyCode"].map(FRECUENCIAS_EN_ES)
            display_df["Titulo"] = display_df["spanishTitle"].apply(
                lambda x: x[:80] + "..." if len(str(x)) > 80 else x
            )
            display_df["Seleccionar"] = False
            
            editor_df = display_df[["Seleccionar", "seriesId", "Frecuencia", "Titulo"]].copy()
            editor_df.columns = ["Seleccionar", "Series ID", "Frecuencia", "Titulo"]
            
            # Instrucciones
            st.markdown('<div class="info-box">✅ <b>Instrucciones:</b> Marca las series en la tabla (columna "Seleccionar"), luego presiona <b>"Agregar al carrito"</b> abajo.</div>', unsafe_allow_html=True)
            
            # Data editor
            st.subheader("Resultados de la busqueda")
            
            edited_df = st.data_editor(
                editor_df,
                column_config={
                    "Seleccionar": st.column_config.CheckboxColumn(
                        "✓",
                        help="Marca para seleccionar esta serie",
                        default=False
                    ),
                    "Series ID": st.column_config.TextColumn("Series ID", disabled=True, width="medium"),
                    "Frecuencia": st.column_config.TextColumn("Frecuencia", disabled=True, width="small"),
                    "Titulo": st.column_config.TextColumn("Titulo", disabled=True, width="large")
                },
                hide_index=True,
                use_container_width=True,
                key="editor_series",
                num_rows="fixed"
            )
            
            # Botones de accion debajo de la tabla
            st.markdown("---")
            col_a1, col_a2, col_a3 = st.columns([1, 1, 1])
            
            with col_a1:
                if st.button("➕ Agregar al carrito", use_container_width=True, key="btn_agregar"):
                    seleccionadas = edited_df[edited_df["Seleccionar"] == True]
                    
                    if len(seleccionadas) == 0:
                        st.warning("⚠️ No has seleccionado ninguna serie en la tabla")
                    else:
                        # Agregar a session_state global (evitando duplicados)
                        existentes = {s["id"] for s in st.session_state.series_seleccionadas}
                        nuevas_agregadas = 0
                        
                        for _, row in seleccionadas.iterrows():
                            sid = row["Series ID"]
                            if sid not in existentes:
                                st.session_state.series_seleccionadas.append({
                                    "id": sid,
                                    "nombre": row["Titulo"][:35],
                                    "frecuencia_original": FRECUENCIAS_ES_EN.get(row["Frecuencia"], "DAILY")
                                })
                                nuevas_agregadas += 1
                        
                        if nuevas_agregadas > 0:
                            st.success(f"✅ Agregadas {nuevas_agregadas} series al carrito. Total: {len(st.session_state.series_seleccionadas)}")
                        else:
                            st.info("ℹ️ Todas las series seleccionadas ya estaban en el carrito")
            
            with col_a2:
                if st.button("📥 Ir a descargar", use_container_width=True, key="btn_ir_descargar"):
                    seleccionadas = edited_df[edited_df["Seleccionar"] == True]
                    existentes = {s["id"] for s in st.session_state.series_seleccionadas}
                    nuevas = 0
                    
                    for _, row in seleccionadas.iterrows():
                        sid = row["Series ID"]
                        if sid not in existentes:
                            st.session_state.series_seleccionadas.append({
                                "id": sid,
                                "nombre": row["Titulo"][:35],
                                "frecuencia_original": FRECUENCIAS_ES_EN.get(row["Frecuencia"], "DAILY")
                            })
                            nuevas += 1
                    
                    st.success(f"✅ {nuevas} series agregadas. Ve a la pestaña '⬇️ Descargar Datos' para continuar")
                    st.info("💡 Cambia a la pestaña 'Descargar Datos' arriba")
            
            with col_a3:
                if st.button("💾 Guardar busqueda en CSV", use_container_width=True, key="btn_guardar_csv"):
                    os.makedirs("data/raw", exist_ok=True)
                    nombre = f"busqueda_{st.session_state.ultima_busqueda.replace(' ', '_').replace(',', '')}.csv"
                    ruta = os.path.join("data", "raw", nombre)
                    resultados.to_csv(ruta, index=False)
                    st.success(f"💾 Busqueda guardada en: `{ruta}`")


# =============================================================================
# TAB 2: DESCARGAR DATOS
# =============================================================================
with tab2:
    st.header("Descargar Series Seleccionadas")
    
    # ============================================================
    # SECCION 1: SERIES EN CARRITO
    # ============================================================
    if not st.session_state.series_seleccionadas:
        st.info("ℹ️ No hay series en el carrito. Usa las opciones de arriba para agregar series.")
    else:
        st.success(f"✅ Tienes **{len(st.session_state.series_seleccionadas)}** series listas para descargar")
        
        # Mostrar series en el carrito
        st.subheader("📋 Series en el carrito")
        
        series_para_eliminar = []
        
        for i, serie in enumerate(st.session_state.series_seleccionadas):
            col_s1, col_s2, col_s3, col_s4 = st.columns([3, 2, 2, 1])
            
            with col_s1:
                st.code(serie["id"])
            
            with col_s2:
                nuevo_nombre = st.text_input(
                    "Nombre corto",
                    value=serie["nombre"],
                    key=f"nombre_{serie['id']}_{i}",
                    label_visibility="collapsed"
                )
                serie["nombre"] = nuevo_nombre
            
            with col_s3:
                st.caption(f"Frec: {FRECUENCIAS_EN_ES.get(serie['frecuencia_original'], serie['frecuencia_original'])}")
            
            with col_s4:
                if st.button("❌", key=f"del_{serie['id']}_{i}", help="Eliminar del carrito"):
                    series_para_eliminar.append(i)
        
        # Eliminar las marcadas
        if series_para_eliminar:
            for idx in sorted(series_para_eliminar, reverse=True):
                st.session_state.series_seleccionadas.pop(idx)
            st.rerun()
        
        st.markdown("---")

    # ============================================================
    # SECCION 2: AGREGAR SERIES POR ID DIRECTO
    # ============================================================
    with st.expander("➕ Agregar series por ID directo", expanded=False):
        st.info("Ingresa Series ID directamente sin necesidad de buscar. Puedes agregar multiples separando por comas o saltos de linea.")
        
        col_id1, col_id2 = st.columns([3, 1])
        
        with col_id1:
            ids_directos = st.text_area(
                "Series ID (uno por linea o separados por coma)",
                placeholder="F073.TCO.PRE.Z.D\nF022.TPM.TIN.D\nF049.COBR.PRE.Z.D",
                height=100,
                key="ids_directos"
            )
        
        with col_id2:
            st.markdown("**Frecuencia Detectada**")
        
        if st.button("➕ Agregar IDs al carrito", use_container_width=True, key="btn_add_ids"):
            if not ids_directos.strip():
                st.warning("Ingresa al menos un Series ID")
            else:
                # Parsear IDs
                ids_lista = [id.strip() for id in ids_directos.replace(",", "\n").split("\n") if id.strip()]
                existentes = {s["id"] for s in st.session_state.series_seleccionadas}
                nuevas = 0
                
                for sid in ids_lista:
                    if sid not in existentes:
                        st.session_state.series_seleccionadas.append({
                            "id": sid,
                            "nombre": "",
                            "frecuencia_original": detectar_frecuencia_por_id(sid)
                        })
                        nuevas += 1
                
                if nuevas > 0:
                    st.success(f"✅ Agregadas {nuevas} series por ID directo")
                    st.rerun()
                else:
                    st.info("Todas las series ya estaban en el carrito")
    
    # ============================================================
    # SECCION 3: CARGAR DESDE CSV
    # ============================================================
    with st.expander("📁 Cargar desde archivo CSV", expanded=False):
        archivo_cargado = st.file_uploader("Sube un CSV con Series ID y Nombre ", type=["csv"], key="uploader_csv")
        if archivo_cargado is not None:
            df_cargado = pd.read_csv(archivo_cargado)
            st.write("Columnas encontradas:")
            st.dataframe(df_cargado.head(), use_container_width=True)
            
            # Detectar columna de Series ID
            posibles_cols = [c for c in df_cargado.columns]
            col_id_csv = st.selectbox("Columna con Series ID", options=df_cargado.columns, index=0 if not posibles_cols else df_cargado.columns.get_loc(posibles_cols[0]))
            
            # Detectar columna de Nombre
            col_nombre_csv = st.selectbox("Columna con Nombre de las series", options=df_cargado.columns, index=1 if not posibles_cols else df_cargado.columns.get_loc(posibles_cols[1]))
            
            
            if st.button("➕ Agregar desde CSV", key="btn_add_csv"):
                ids_csv = df_cargado[col_id_csv].astype(str).tolist()
                name_csv = df_cargado[col_nombre_csv].astype(str).tolist()
                existentes = {s["id"] for s in st.session_state.series_seleccionadas}
                nuevas = 0
                
                for sid in ids_csv:
                    sid = sid.strip()
                    if sid and sid not in existentes:
                        st.session_state.series_seleccionadas.append({
                            "id": sid,
                            "nombre": name_csv[ids_csv.index(sid)] if sid in ids_csv else (sid.split(".")[-1] if "." in sid else sid[:20]),
                            "frecuencia_original": detectar_frecuencia_por_id(sid)
                        })
                        nuevas += 1
                
                st.success(f"✅ Agregadas {nuevas} series desde CSV")
                st.rerun()
    
        st.markdown("---")
        
    # ============================================================
    # OPCIONES DE DESCARGA
    # ============================================================
    st.subheader("⚙️ Opciones de descarga")
        
    # Fila 1: Fechas y frecuencia
    col_o1, col_o2, col_o3 = st.columns(3)
        
    with col_o1:
        fecha_desde = st.date_input(
            "Desde",
            value=pd.to_datetime("2020-01-01"),
            key="fecha_desde"
        )
        
    with col_o2:
        fecha_hasta = st.date_input(
            "Hasta",
            value=pd.to_datetime("today"),
            key="fecha_hasta"
        )
        
    with col_o3:
        frecuencia_descarga = st.selectbox(
            "Frecuencia de salida",
            options=["Original (sin cambios)", "Diaria", "Mensual", "Trimestral", "Anual"],
            key="freq_salida",
            help="Si eliges diferente a 'Original', se aplicara agregacion o imputacion segun corresponda"
        )
        
    # Fila 2: Formato de salida y tipo de archivo
    col_o4, col_o5 = st.columns(2)
        
    with col_o4:
        formato_salida = st.selectbox(
            "Formato de salida",
            options=["CSV", "Excel (.xlsx)"],
            key="formato_salida"
        )
        
    with col_o5:
        tipo_archivo = st.selectbox(
            "Tipo de archivo",
            options=["Unico (todas las series juntas)", "Separados (un archivo por serie)"],
            key="tipo_archivo"
        )
        
    # ============================================================
    # DETERMINAR MODO DE OPERACION
    # ============================================================
    if frecuencia_descarga != "Original (sin cambios)":
        necesita_agregacion, necesita_imputacion, mensaje_modo = determinar_modo_operacion(
            st.session_state.series_seleccionadas,
            frecuencia_descarga
        )
            
        st.markdown("---")
            
        # Mostrar mensaje del modo
        if necesita_agregacion and necesita_imputacion:
            st.markdown(f'<div class="warning-box">⚙️ <b>Modo mixto:</b> {mensaje_modo}</div>', unsafe_allow_html=True)
        elif necesita_agregacion:
            st.markdown(f'<div class="info-box">📊 <b>Modo agregacion:</b> {mensaje_modo}</div>', unsafe_allow_html=True)
        elif necesita_imputacion:
            st.markdown(f'<div class="success-box">🩹 <b>Modo imputacion:</b> {mensaje_modo}</div>', unsafe_allow_html=True)
            
        # ============================================================
        # CONFIGURACION DE AGREGACION (si aplica)
        # ============================================================
        if necesita_agregacion:
            st.subheader("📊 Configuracion de agregacion")
                
            col_a1, col_a2 = st.columns(2)
                
            with col_a1:
                agregacion = st.selectbox(
                    "Funcion de agregacion",
                    options=list(AGREGACIONES.keys()),
                    key="agg_select",
                    help="Como agrupar los datos al pasar a una frecuencia menos desagregada"
                )
                
            with col_a2:
                # Variacion con saltos de linea en el help
                variacion = st.number_input(
                    "Variación (en periodos)",
                    min_value=0,
                    max_value=24,
                    value=0,
                    key="var_input",
                    help="""Mensual:
  0 = Sin variacion
  1 = Variacion mensual
  12 = Variacion anual

Trimestral:
  0 = Sin variacion
  1 = Variacion trimestral
  4 = Variacion anual

Anual:
  0 = Sin variacion
  1 = Variacion anual"""
                    )
                
            # Observado por serie
            st.subheader("📋 Observado por serie")
            usar_misma = st.checkbox("Usar la misma agregacion para todas", value=True, key="chk_misma_agg")
                
            observado_dict = {}
            for serie in st.session_state.series_seleccionadas:
                if usar_misma:
                    observado_dict[serie["nombre"]] = AGREGACIONES[agregacion]
                else:
                    agg_individual = st.selectbox(
                        f"{serie['nombre']}",
                        options=list(AGREGACIONES.keys()),
                        key=f"agg_{serie['id']}"
                    )
                    observado_dict[serie["nombre"]] = AGREGACIONES[agg_individual]
        else:
            variacion = 0
            agregacion = None
            observado_dict = None
            
        # ============================================================
        # CONFIGURACION DE IMPUTACION (si aplica)
        # ============================================================
        if necesita_imputacion:
            st.subheader("🩹 Configuracion de imputacion")
                
            imputacion = st.selectbox(
                "Metodo de imputacion de NaN",
                options=list(IMPUTACIONES.keys()),
                key="imputacion",
                help="Como rellenar valores faltantes cuando se pasa a una frecuencia mas desagregada"
            )
        else:
            imputacion = "Sin imputacion (dejar NaN)"
    else:
        variacion = 0
        agregacion = None
        observado_dict = {}
        imputacion = "Sin imputacion (dejar NaN)"
        
    st.markdown("---")
        
    # ============================================================
    # BOTON DE DESCARGA PRINCIPAL
    # ============================================================
    if st.button("⬇️ DESCARGAR TODAS", use_container_width=True, key="btn_descargar_todas"):
        with st.spinner(f"Descargando {len(st.session_state.series_seleccionadas)} series desde el Banco Central..."):
            try:
                siete = bcchapi.Siete(email, password)
                    
                series_ids = [s["id"] for s in st.session_state.series_seleccionadas]
                nombres = [s["nombre"] for s in st.session_state.series_seleccionadas]
                    
                # Preparar parametros
                kwargs = {
                    "series": series_ids,
                    "nombres": nombres,
                    "desde": fecha_desde.strftime("%Y-%m-%d"),
                    "hasta": fecha_hasta.strftime("%Y-%m-%d")
                }
                    
                # Agregar parametros de agregacion si aplica
                if frecuencia_descarga != "Original (sin cambios)":
                    freq_map = {"Diaria": "D", "Mensual": "M", "Trimestral": "Q", "Anual": "A"}
                    kwargs["frecuencia"] = freq_map[frecuencia_descarga]
                    kwargs["variacion"] = int(variacion)
                    if observado_dict and len(observado_dict) > 0:
                        kwargs["observado"] = observado_dict
                    else:
                        kwargs["observado"] = {s["nombre"]: "last" for s in st.session_state.series_seleccionadas}
                    
                # Ejecutar descarga
                df = siete.cuadro(**kwargs)
                    
                df = df.reset_index()
                df = df.rename(columns={"index": "date"})
                    
                # Aplicar imputacion si se selecciono
                metodo_imputacion = IMPUTACIONES[imputacion]
                if metodo_imputacion is not None:
                    date_col = df["date"].copy()
                    df_numeric = df.drop(columns=["date"])
                        
                    nan_antes = df_numeric.isna().sum().sum()
                    df_numeric = aplicar_imputacion(df_numeric, metodo_imputacion)
                    nan_despues = df_numeric.isna().sum().sum()
                        
                    df = pd.concat([date_col, df_numeric], axis=1)
                        
                    if nan_antes > 0:
                        st.info(f"🩹 Imputacion aplicada: {nan_antes} NaN -> {nan_despues} NaN restantes")
                    
                # Resultados
                st.success("🎉 ¡Descarga exitosa!")
                    
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                with col_r1:
                    st.metric("Filas descargadas", len(df))
                with col_r2:
                    st.metric("Series", len(series_ids))
                with col_r3:
                    st.metric("Desde", str(df["date"].min())[:10])
                with col_r4:
                    st.metric("Hasta", str(df["date"].max())[:10])
                    
                # Vista previa
                st.subheader("👁️ Vista previa")
                st.dataframe(df.head(20), use_container_width=True)
                    
                # Estadisticas
                st.subheader("📈 Estadisticas rapidas")
                st.dataframe(df.describe(), use_container_width=True)
                    
                # ============================================================
                # GUARDAR Y EXPORTAR
                # ============================================================
                os.makedirs("data/raw", exist_ok=True)
                    
                if tipo_archivo == "Unico (todas las series juntas)":
                    if formato_salida == "CSV":
                        ruta = os.path.join("data", "raw", "descarga_multiple.csv")
                        df.to_csv(ruta, index=False)
                        st.success(f"💾 Guardado en: `{ruta}`")
                            
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Descargar CSV",
                            csv,
                            "descarga_multiple.csv",
                            "text/csv",
                            key="btn_download_csv"
                        )
                    else:
                        ruta = os.path.join("data", "raw", "descarga_multiple.xlsx")
                        df.to_excel(ruta, index=False, engine='openpyxl')
                        st.success(f"💾 Guardado en: `{ruta}`")
                            
                        with open(ruta, "rb") as f:
                            st.download_button(
                                "📥 Descargar Excel",
                                f,
                                "descarga_multiple.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="btn_download_xlsx"
                            )
                    
                else:
                    st.subheader("📁 Archivos separados")
                        
                    for i, serie in enumerate(st.session_state.series_seleccionadas):
                        col_f1, col_f2 = st.columns([3, 1])
                            
                        df_serie = df[["date", serie["nombre"]]].copy()
                            
                        with col_f1:
                            if formato_salida == "CSV":
                                nombre_archivo = f"{serie['nombre']}.csv"
                                ruta_serie = os.path.join("data", "raw", nombre_archivo)
                                df_serie.to_csv(ruta_serie, index=False)
                                st.write(f"📄 {nombre_archivo}")
                            else:
                                nombre_archivo = f"{serie['nombre']}.xlsx"
                                ruta_serie = os.path.join("data", "raw", nombre_archivo)
                                df_serie.to_excel(ruta_serie, index=False, engine='openpyxl')
                                st.write(f"📊 {nombre_archivo}")
                            
                        with col_f2:
                            if formato_salida == "CSV":
                                csv_serie = df_serie.to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    "📥",
                                    csv_serie,
                                    nombre_archivo,
                                    "text/csv",
                                    key=f"dl_csv_{serie['id']}_{i}"
                                )
                            else:
                                with open(ruta_serie, "rb") as f:
                                    st.download_button(
                                        "📥",
                                        f,
                                        nombre_archivo,
                                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key=f"dl_xlsx_{serie['id']}_{i}"
                                    )
                        
                    st.success(f"💾 {len(st.session_state.series_seleccionadas)} archivos guardados en data/raw/")
                    
            except Exception as e:
                st.error(f"❌ Error en descarga: {e}")
                st.info("Tip: Verifica que los Series ID sean correctos, las fechas validas, y que las credenciales funcionen")


# =============================================================================
# FOOTER
# =============================================================================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888; font-size: 0.9rem;'>"
    "BCCH Data Collector Pro | Proyecto Dolar Chile Forecast | 2025"
    "</div>",
    unsafe_allow_html=True
)