import cv2
import numpy as np
import requests
import streamlit as st

# Lee la URL desde los Secretos de Streamlit o usa directamente la de Render
API_URL = st.secrets.get("API_URL", "https://plataforma-pymes.onrender.com")

def show_escaner_qr():
    st.header("Escaneo y Lectura de Codigos QR")
    st.caption("Modulo de Trazabilidad Inteligente - NovaTech")

    # Obtener credenciales de la sesion automatica
    usuario = st.session_state.get("usuario_activo", "Carlos Gomez")
    ubicacion = st.session_state.get("ubicacion_estacion", "Planta Principal - Muelle 2")

    metodo_entrada = st.radio(
        "Seleccione el metodo de captura:",
        ["Cargar Imagen de QR (Archivo)", "Usar Camara Web"],
        horizontal=True
    )

    foto_capturada = None

    if metodo_entrada == "Usar Camara Web":
        foto_capturada = st.camera_input("Capturar QR con la camara")
    else:
        foto_capturada = st.file_uploader(
            "Seleccione una imagen con un codigo QR", 
            type=["png", "jpg", "jpeg"]
        )

    if foto_capturada is not None:
        bytes_data = foto_capturada.getvalue()
        imagen_array = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

        if imagen_array is not None:
            detector_qr = cv2.QRCodeDetector()
            lote_id_detectado, bbox, _ = detector_qr.detectAndDecode(imagen_array)

            if lote_id_detectado:
                st.success(f"Codigo QR detectado con exito. ID de Lote: {lote_id_detectado}")

                try:
                    res_lotes = requests.get(f"{API_URL}/lotes")
                    if res_lotes.status_code == 200 and res_lotes.json():
                        lote_encontrado = next((l for l in res_lotes.json() if l.get('lote_id') == lote_id_detectado), None)

                        if lote_encontrado:
                            st.info(f"Producto: {lote_encontrado.get('nombre_producto')} | Estado Actual: {lote_encontrado.get('estado')}")
                            
                            # Mostrar metadatos detectados automaticamente
                            st.caption(f"Registro Automatico -> Operario: **{usuario}** | Punto de Control: **{ubicacion}**")

                            with st.form("form_evento_qr"):
                                hito = st.selectbox("Nuevo Hito Operativo", [
                                    "Control de Calidad Passed", 
                                    "Empaque Completado", 
                                    "Almacenado en Bodega", 
                                    "Despachado a Transporte", 
                                    "Entregado a Cliente"
                                ])
                                
                                sub_ev = st.form_submit_button("Confirmar y Registrar Evento")
                                
                                if sub_ev:
                                    res = requests.post(f"{API_URL}/lotes/{lote_id_detectado}/eventos", json={
                                        "hito": hito,
                                        "usuario": usuario,
                                        "ubicacion": ubicacion
                                    })
                                    if res.status_code == 200:
                                        st.success("Evento registrado correctamente en la cadena de custodia.")
                                        st.rerun()
                                    else:
                                        st.error("Error al registrar el evento en la API.")
                        else:
                            st.error("El codigo QR no corresponde a ningun lote registrado en la base de datos.")
                    else:
                        st.error("No se pudo consultar la base de datos de lotes.")
                except Exception as e:
                    st.error(f"Error de conexion con la API: {e}")
            else:
                st.error("No se detecto ningun codigo QR valido en la imagen ingresada.")
        else:
            st.error("No se pudo procesar la imagen.")