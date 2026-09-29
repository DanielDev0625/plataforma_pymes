import requests
import streamlit as st

# Lee la URL desde los Secretos de Streamlit o usa directamente la de Render
API_URL = st.secrets.get("API_URL", "https://plataforma-pymes.onrender.com")

def show_cadena_custodia():
    st.header("Cadena de Custodia y Registro de Eventos")
    st.caption("Modulo de Trazabilidad Inteligente - NovaTech")

    try:
        res_lotes = requests.get(f"{API_URL}/lotes")
        if res_lotes.status_code == 200 and res_lotes.json():
            lotes_activos = [l for l in res_lotes.json() if l.get('estado') != "Entregado a Cliente"]
            
            if lotes_activos:
                lotes_dict = {f"{l['nombre_producto']} (ID: {l['lote_id'][:8]}...)": l['lote_id'] for l in lotes_activos}
                lote_sel = st.selectbox("Seleccione el Lote Activo", list(lotes_dict.keys()))
                
                with st.form("form_evento"):
                    hito = st.selectbox("Hito Operativo", [
                        "Control de Calidad Passed", 
                        "Empaque Completado", 
                        "Almacenado en Bodega", 
                        "Despachado a Transporte", 
                        "Entregado a Cliente"
                    ])
                    usuario = st.text_input("Usuario / Inspector Autenticado", placeholder="Ej: Juan Perez")
                    ubicacion = st.text_input("Ubicacion / Planta", placeholder="Ej: Bodega Central")
                    sub_ev = st.form_submit_button("Registrar Evento Criptografico")
                    
                    if sub_ev:
                        if usuario:
                            lote_id = lotes_dict[lote_sel]
                            res = requests.post(f"{API_URL}/lotes/{lote_id}/eventos", json={
                                "hito": hito,
                                "usuario": usuario,
                                "ubicacion": ubicacion
                            })
                            if res.status_code == 200:
                                st.success("Evento registrado correctamente!")
                                st.rerun()
                            else:
                                st.error("Error al guardar el evento en la API.")
                        else:
                            st.warning("El nombre del usuario es obligatorio.")
            else:
                st.info("No hay lotes activos pendientes por actualizar.")
        else:
            st.info("No hay lotes en la base de datos.")
    except Exception as e:
        st.error(f"Error de conexion con la API: {e}")