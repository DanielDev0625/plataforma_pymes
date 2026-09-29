import os
import streamlit as st

# Importar las vistas de los modulos
from views.cadena_custodia import show_cadena_custodia
from views.escaner_qr import show_escaner_qr
from views.lotes_proceso import show_lotes_proceso
from views.pedidos_entregados import show_pedidos_entregados
from views.registrar_lote import show_registrar_lote

# Configuracion inicial de la pagina
st.set_page_config(
    page_title="NovaTech - Plataforma PyMEs",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar variables de sesion si no existen
if "usuario_activo" not in st.session_state:
    st.session_state["usuario_activo"] = "Carlos Gomez"

if "ubicacion_estacion" not in st.session_state:
    st.session_state["ubicacion_estacion"] = "Planta Principal - Muelle 2"

# ---- BARRA LATERAL (SIDEBAR) ----
logo_path = os.path.join("assets", "logo.png")
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
else:
    st.sidebar.title("NovaTech")

st.sidebar.markdown("---")

# CONFIGURACION DE SESION / ESTACION
st.sidebar.markdown("### Perfil de Estacion")
st.session_state["usuario_activo"] = st.sidebar.text_input(
    "Operario Activo", 
    value=st.session_state["usuario_activo"]
)
st.session_state["ubicacion_estacion"] = st.sidebar.text_input(
    "Punto de Control", 
    value=st.session_state["ubicacion_estacion"]
)

st.sidebar.markdown("---")

# MODULO 1: TRAZABILIDAD INTELIGENTE
st.sidebar.markdown("### Trazabilidad Inteligente")
opcion_trazabilidad = st.sidebar.radio(
    "Selecciona una subseccion:",
    [
        "Escaner QR (Lectura Rapida)",
        "Registrar Nuevo Lote",
        "Cadena de Custodia",
        "Lotes en Proceso",
        "Pedidos Entregados"
    ],
    key="nav_trazabilidad"
)

st.sidebar.markdown("---")

# ESPACIO PARA FUTUROS MODULOS
st.sidebar.markdown("### Gestion de Inventario")
st.sidebar.caption("Proximamente...")

st.sidebar.markdown("### Analitica y Reportes")
st.sidebar.caption("Proximamente...")


# ---- ENRUTADOR DE PAGINAS ----
if opcion_trazabilidad == "Escaner QR (Lectura Rapida)":
    show_escaner_qr()
elif opcion_trazabilidad == "Registrar Nuevo Lote":
    show_registrar_lote()
elif opcion_trazabilidad == "Cadena de Custodia":
    show_cadena_custodia()
elif opcion_trazabilidad == "Lotes en Proceso":
    show_lotes_proceso()
elif opcion_trazabilidad == "Pedidos Entregados":
    show_pedidos_entregados()