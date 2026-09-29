import requests
import streamlit as st

# Lee la URL desde los Secretos de Streamlit o usa directamente la de Render
API_URL = st.secrets.get("API_URL", "https://plataforma-pymes.onrender.com")

def show_registrar_lote():
    st.header("Registrar Nuevo Lote / Pedido de Produccion")
    st.caption("Modulo de Trazabilidad Inteligente - NovaTech")

    with st.form("form_crear_lote"):
        nombre = st.text_input("Nombre del Producto", placeholder="Ej: Harina de Trigo 1Kg")
        descripcion = st.text_area("Descripcion u observaciones")
        submitted = st.form_submit_button("Guardar y Generar QR")

        if submitted:
            if nombre:
                try:
                    respuesta = requests.post(
                        f"{API_URL}/lotes", 
                        json={"nombre_producto": nombre, "descripcion": descripcion}
                    )
                    if respuesta.status_code == 200:
                        data = respuesta.json()
                        st.success(f"Lote/Pedido registrado con exito! ID: {data['lote_id']}")
                    else:
                        st.error("Error al registrar el lote en el servidor backend.")
                except Exception as e:
                    st.error(f"Error de conexion con la API: {e}")
            else:
                st.warning("El nombre del producto es obligatorio.")