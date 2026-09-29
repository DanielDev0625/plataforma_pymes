import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

def renderizar_tarjeta_lote(lote):
    with st.expander(f"{lote.get('nombre_producto', 'Lote')} | Estado: {lote.get('estado', 'N/A')}"):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**ID Unico:** `{lote.get('lote_id')}`")
            st.write(f"**Hash Inmutable Actual:** `{lote.get('hash_actual')}`")
            
            try:
                res_ev = requests.get(f"{API_URL}/lotes/{lote['lote_id']}/eventos")
                if res_ev.status_code == 200 and res_ev.json():
                    st.write("**Historial de Cadena de Custodia:**")
                    for ev in res_ev.json():
                        st.caption(f"{ev.get('timestamp', '')[:16]} - {ev.get('hito')} | Resp: {ev.get('usuario')} | Hash: `{ev.get('hash_evento', '')[:16]}...`")
            except Exception as e:
                st.error(f"Error al cargar el historial de eventos: {e}")
            
            st.markdown(f"[Descargar Certificado PDF]({API_URL}/lotes/{lote['lote_id']}/certificado_pdf)")
            
        with col2:
            try:
                st.image(f"{API_URL}/lotes/{lote['lote_id']}/qr", caption="QR de Verificacion", width=140)
            except Exception:
                st.caption("QR no disponible")

def show_lotes_proceso():
    st.header("Lotes Activos en Cadena de Suministro")
    st.caption("Modulo de Trazabilidad Inteligente - NovaTech")

    try:
        res = requests.get(f"{API_URL}/lotes")
        if res.status_code == 200 and res.json():
            activos = [l for l in res.json() if l.get('estado') != "Entregado a Cliente"]
            if activos:
                for lote in activos:
                    renderizar_tarjeta_lote(lote)
            else:
                st.info("No hay lotes en proceso actualmente.")
        else:
            st.info("No hay lotes registrados en la base de datos.")
    except Exception as e:
        st.error(f"Error de conexion con la API: {e}")