import requests
import streamlit as st
from views.lotes_proceso import renderizar_tarjeta_lote

# Lee la URL desde los Secretos de Streamlit o usa directamente la de Render
API_URL = st.secrets.get("API_URL", "https://plataforma-pymes.onrender.com")

def show_pedidos_entregados():
    st.header("Historico de Pedidos Entregados")
    st.caption("Modulo de Trazabilidad Inteligente - NovaTech")

    try:
        res = requests.get(f"{API_URL}/lotes")
        if res.status_code == 200 and res.json():
            entregados = [l for l in res.json() if l.get('estado') == "Entregado a Cliente"]
            if entregados:
                for lote in entregados:
                    renderizar_tarjeta_lote(lote)
            else:
                st.info("Aun no hay pedidos marcados como 'Entregado a Cliente'.")
        else:
            st.info("No hay lotes registrados en la base de datos.")
    except Exception as e:
        st.error(f"Error de conexion con la API: {e}")