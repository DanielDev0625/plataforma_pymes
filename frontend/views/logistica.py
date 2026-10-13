import bisect
import heapq
import math
from datetime import datetime, timezone

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st


BODEGAS = {
    "Barranquilla": (10.9685, -74.7813),
    "Cartagena": (10.3910, -75.4794),
    "Santa Marta": (11.2408, -74.1990),
    "Sincelejo": (9.3047, -75.3978),
    "Medellín": (6.2442, -75.5812),
    "Bogotá": (4.7110, -74.0721),
    "Cali": (3.4516, -76.5320),
}

_DORADA_BOGOTA = [
    ("La Dorada", 5.4519, -74.6652, True),
    ("Honda", 5.2089, -74.7381, True),
    ("Guaduas", 5.0689, -74.5964, False),
    ("Villeta", 5.0116, -74.4723, False),
    ("Facatativá", 4.8143, -74.3544, False),
]
_ARMENIA_CALI = [
    ("Armenia", 4.5339, -75.6811, True),
    ("La Paila", 4.3080, -76.0670, False),
    ("Tuluá", 4.0847, -76.1954, True),
    ("Buga", 3.9014, -76.2978, False),
    ("Palmira", 3.5394, -76.3036, True),
]

SEGMENTOS = {
    ("Barranquilla", "Cartagena"): [
        ("Puerto Colombia", 10.9878, -74.9547, False),
        ("Galerazamba", 10.7960, -75.2610, False),
        ("Santa Catalina", 10.6014, -75.2860, False),
    ],
    ("Barranquilla", "Santa Marta"): [
        ("Isla de Salamanca", 10.9970, -74.5200, False),
        ("Ciénaga", 11.0069, -74.2480, True),
    ],
    ("Cartagena", "Sincelejo"): [
        ("Turbaco", 10.3333, -75.4167, False),
        ("Arjona", 10.2556, -75.3446, False),
    ],
    ("Sincelejo", "Medellín"): [
        ("Sahagún", 8.9497, -75.4450, False),
        ("Planeta Rica", 8.4104, -75.5877, True),
        ("Caucasia", 7.9847, -75.1937, True),
        ("Cáceres", 7.5772, -75.3491, False),
        ("Valdivia", 7.1622, -75.4400, False),
        ("Yarumal", 6.9632, -75.4175, True),
        ("Santa Rosa de Osos", 6.6428, -75.4605, False),
    ],
    ("Barranquilla", "Bogotá"): [
        ("Isla de Salamanca", 10.9970, -74.5200, False),
        ("Ciénaga", 11.0069, -74.2480, True),
        ("Fundación", 10.5195, -74.1856, False),
        ("Bosconia", 9.9733, -73.8918, True),
        ("Aguachica", 8.3082, -73.6256, True),
        ("San Alberto", 7.7625, -73.3868, False),
        ("Barrancabermeja", 7.0653, -73.8547, True),
        ("Puerto Boyacá", 5.9750, -74.5867, False),
    ] + _DORADA_BOGOTA,
    ("Medellín", "Bogotá"): [
        ("Guarne", 6.2800, -75.4425, False),
        ("Marinilla", 6.1737, -75.3358, False),
        ("San Luis", 6.0414, -74.9936, False),
        ("Puerto Triunfo", 5.8750, -74.6416, True),
    ] + _DORADA_BOGOTA,
    ("Bogotá", "Cali"): [
        ("Fusagasugá", 4.3369, -74.3636, False),
        ("Girardot", 4.3009, -74.8036, True),
        ("Espinal", 4.1500, -74.8860, False),
        ("Ibagué", 4.4389, -75.2322, True),
        ("Cajamarca", 4.4412, -75.4281, False),
    ] + _ARMENIA_CALI,
    ("Medellín", "Cali"): [
        ("Caldas", 6.0915, -75.6359, False),
        ("La Pintada", 5.7519, -75.6064, False),
        ("Pereira", 4.8133, -75.6961, True),
    ] + _ARMENIA_CALI,
}

TIPOS_VEHICULO = ["Tractomula", "Camión sencillo", "Furgón", "Camioneta de carga", "Turbo"]

DEMO_TRANSPORTISTAS = [
    ("Carlos Ramírez", "Tractomula", "Kenworth T800", "TJK482", "300 555 0101"),
    ("Andrés Villalba", "Tractomula", "Freightliner Cascadia", "UVB215", "300 555 0102"),
    ("Luis Fernández", "Camión sencillo", "Chevrolet NPR", "WLP903", "300 555 0103"),
    ("Jorge Barrios", "Furgón", "Hino 500", "SXN640", "300 555 0104"),
]

VELOCIDAD_PROMEDIO_KMH = 55.0   
MAX_PUNTOS_MAPA = 1600          
ACTUALIZACION_SEG = 2           
FACTOR_CURVAS = 1.12            


def _haversine(a, b):
    """Distancia en km entre dos puntos (lat, lon)."""
    r = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _construir_grafo():
    grafo = {}
    for (a, b), puntos in SEGMENTOS.items():
        grafo.setdefault(a, {})[b] = list(puntos)
        grafo.setdefault(b, {})[a] = list(reversed(puntos))
    return grafo


GRAFO = _construir_grafo()


def _largo_segmento(a, b, puntos):
    cadena = [BODEGAS[a]] + [(p[1], p[2]) for p in puntos] + [BODEGAS[b]]
    return sum(_haversine(cadena[i], cadena[i + 1]) for i in range(len(cadena) - 1))


def _camino_bodegas(origen, destino):
    """Camino mas corto entre bodegas (Dijkstra sobre los corredores viales)."""
    dist = {origen: 0.0}
    previo = {}
    cola = [(0.0, origen)]
    while cola:
        d, u = heapq.heappop(cola)
        if u == destino:
            break
        if d > dist.get(u, float("inf")):
            continue
        for v, puntos in GRAFO.get(u, {}).items():
            nd = d + _largo_segmento(u, v, puntos)
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                previo[v] = u
                heapq.heappush(cola, (nd, v))
    if destino not in dist:
        return [origen, destino]
    camino = [destino]
    while camino[-1] != origen:
        camino.append(previo[camino[-1]])
    return list(reversed(camino))


def _hito_bodega(ciudad):
    lat, lon = BODEGAS[ciudad]
    return {"nombre": f"Bodega {ciudad}", "lat": lat, "lon": lon, "via": True, "bodega": True}


def _hitos_ruta(origen, destino):
    nodos = _camino_bodegas(origen, destino)
    hitos = [_hito_bodega(nodos[0])]
    for a, b in zip(nodos, nodos[1:]):
        for nombre, lat, lon, via in GRAFO[a][b]:
            if hitos[-1]["nombre"] != nombre:
                hitos.append({"nombre": nombre, "lat": lat, "lon": lon, "via": via, "bodega": False})
        hitos.append(_hito_bodega(b))
    return hitos


def _geometria_osrm(hitos):
    """Trazado real por carretera usando el servidor publico de OSRM."""
    obligatorios = [i for i, h in enumerate(hitos) if h["bodega"]]
    opcionales = [i for i, h in enumerate(hitos) if h["via"] and not h["bodega"]]
    espacio = max(0, 14 - len(obligatorios))
    if len(opcionales) > espacio:
        paso = math.ceil(len(opcionales) / max(espacio, 1))
        opcionales = opcionales[::paso][:espacio]
    indices = sorted(obligatorios + opcionales)
    coords = ";".join(f"{hitos[i]['lon']:.5f},{hitos[i]['lat']:.5f}" for i in indices)
    resp = requests.get(
        f"https://router.project-osrm.org/route/v1/driving/{coords}",
        params={"overview": "full", "geometries": "geojson"},
        timeout=12,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok":
        raise ValueError("OSRM no devolvio una ruta")
    return [(lat, lon) for lon, lat in data["routes"][0]["geometry"]["coordinates"]]


def _simplificar(puntos, maximo=MAX_PUNTOS_MAPA):
    if len(puntos) <= maximo:
        return puntos
    paso = math.ceil(len(puntos) / maximo)
    reducidos = puntos[::paso]
    if reducidos[-1] != puntos[-1]:
        reducidos.append(puntos[-1])
    return reducidos


@st.cache_data(show_spinner=False, ttl=3600)
def obtener_ruta(origen, destino, usar_osrm=True):
    """Devuelve la ruta (puntos, km acumulados, hitos) entre dos bodegas."""
    hitos = _hitos_ruta(origen, destino)
    puntos = None
    fuente = "Ruta aproximada por puntos de referencia"

    if usar_osrm:
        try:
            geo = _geometria_osrm(hitos)
            if len(geo) > 10:
                puntos = _simplificar(geo)
                fuente = "Trazado por carretera (OpenStreetMap / OSRM)"
        except Exception:
            puntos = None

    if puntos is None:
        puntos = [(h["lat"], h["lon"]) for h in hitos]

    factor = 1.0 if fuente.startswith("Trazado") else FACTOR_CURVAS
    acumulado = [0.0]
    for i in range(1, len(puntos)):
        acumulado.append(acumulado[-1] + _haversine(puntos[i - 1], puntos[i]) * factor)


    for h in hitos:
        mejor = min(range(len(puntos)), key=lambda i: (puntos[i][0] - h["lat"]) ** 2 + (puntos[i][1] - h["lon"]) ** 2)
        h["km"] = acumulado[mejor]

    return {
        "puntos": puntos,
        "cum": acumulado,
        "hitos": hitos,
        "distancia_km": acumulado[-1],
        "fuente": fuente,
    }


def posicion_en_ruta(ruta, progreso):
    """Posicion del camion para un progreso entre 0 y 1."""
    puntos, cum = ruta["puntos"], ruta["cum"]
    objetivo = max(0.0, min(1.0, progreso)) * cum[-1]
    i = bisect.bisect_right(cum, objetivo) - 1
    i = min(max(i, 0), len(puntos) - 2)
    tramo = cum[i + 1] - cum[i]
    f = 0.0 if tramo == 0 else (objetivo - cum[i]) / tramo
    lat = puntos[i][0] + (puntos[i + 1][0] - puntos[i][0]) * f
    lon = puntos[i][1] + (puntos[i + 1][1] - puntos[i][1]) * f
    return lat, lon, objetivo, i

def _vista_mapa(ruta, centro=None):
    if centro:
        return pdk.ViewState(latitude=centro[0], longitude=centro[1], zoom=8, pitch=0)
    lats = [p[0] for p in ruta["puntos"]]
    lons = [p[1] for p in ruta["puntos"]]
    dlat = max(max(lats) - min(lats), 0.05)
    dlon = max(max(lons) - min(lons), 0.05)
    zoom_lat = math.log2(420 * 360 / (256 * dlat * 1.1))
    zoom_lon = math.log2(900 * 360 / (256 * dlon * 1.1))
    zoom = max(4.0, min(zoom_lat, zoom_lon, 9.5) - 0.3)
    return pdk.ViewState(
        latitude=(max(lats) + min(lats)) / 2,
        longitude=(max(lons) + min(lons)) / 2,
        zoom=zoom,
        pitch=0,
    )


def construir_mapa(ruta, camion=None, indice=0, etiqueta="", seguir=False):
    puntos = ruta["puntos"]
    capas = [
        pdk.Layer(
            "PathLayer",
            data=[{"path": [[lo, la] for la, lo in puntos]}],
            get_path="path",
            get_color=[96, 165, 250, 170],
            get_width=200,
            width_min_pixels=4,
        )
    ]

    if camion:
        recorrido = [[lo, la] for la, lo in puntos[: indice + 1]] + [[camion[1], camion[0]]]
        capas.append(
            pdk.Layer(
                "PathLayer",
                data=[{"path": recorrido}],
                get_path="path",
                get_color=[34, 197, 94, 255],
                get_width=200,
                width_min_pixels=5,
            )
        )

    hitos = [
        {
            "position": [h["lon"], h["lat"]],
            "color": [250, 204, 21, 255] if h["bodega"] else [226, 232, 240, 230],
            "radio": 7000 if h["bodega"] else 2500,
        }
        for h in ruta["hitos"]
    ]
    capas.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=hitos,
            get_position="position",
            get_fill_color="color",
            get_radius="radio",
            radius_min_pixels=3,
            radius_max_pixels=11,
            stroked=True,
            get_line_color=[15, 23, 42, 255],
            line_width_min_pixels=1,
        )
    )

    etiquetas = [
        {"position": [h["lon"], h["lat"]], "text": h["nombre"]}
        for h in ruta["hitos"]
        if h["bodega"] or h["via"]
    ]
    capas.append(
        pdk.Layer(
            "TextLayer",
            data=etiquetas,
            get_position="position",
            get_text="text",
            get_size=13,
            get_color=[255, 255, 255, 255],
            get_pixel_offset=[0, -16],
            background=True,
            get_background_color=[15, 23, 42, 200],
            character_set="auto",
        )
    )

    if camion:
        punto = [{"position": [camion[1], camion[0]], "text": etiqueta}]
        capas.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=punto,
                get_position="position",
                get_fill_color=[249, 115, 22, 90],
                get_radius=16000,
                radius_min_pixels=16,
                radius_max_pixels=26,
            )
        )
        capas.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=punto,
                get_position="position",
                get_fill_color=[249, 115, 22, 255],
                get_radius=6000,
                radius_min_pixels=8,
                radius_max_pixels=12,
                stroked=True,
                get_line_color=[255, 255, 255, 255],
                line_width_min_pixels=2,
            )
        )
        capas.append(
            pdk.Layer(
                "TextLayer",
                data=punto,
                get_position="position",
                get_text="text",
                get_size=14,
                get_color=[255, 255, 255, 255],
                get_pixel_offset=[0, 26],
                background=True,
                get_background_color=[234, 88, 12, 230],
                character_set="auto",
            )
        )

    centro = camion if (camion and seguir) else None
    return pdk.Deck(layers=capas, initial_view_state=_vista_mapa(ruta, centro), map_style=None)


def _estirar(funcion, *args, **kwargs):
    """Ancho completo compatible con versiones nuevas y viejas de Streamlit."""
    try:
        return funcion(*args, width="stretch", **kwargs)
    except Exception:
        return funcion(*args, use_container_width=True, **kwargs)


def _fmt_horas(horas):
    minutos = int(round(horas * 60))
    return f"{minutos // 60} h {minutos % 60:02d} min"


def _fmt_segundos(segundos):
    segundos = max(0, int(segundos))
    return f"{segundos // 60:02d}:{segundos % 60:02d}"


def _parse_fecha(valor):
    if not valor:
        return datetime.now(timezone.utc)
    dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _api_get(API_URL, ruta):
    try:
        res = requests.get(f"{API_URL}{ruta}", timeout=20)
        if res.status_code == 200:
            return True, res.json()
        return False, f"Error {res.status_code}: {res.text}"
    except Exception as e:
        return False, str(e)


def _api_post(API_URL, ruta, payload=None):
    try:
        res = requests.post(f"{API_URL}{ruta}", json=payload, timeout=30)
        if res.status_code in (200, 201):
            return True, res.json()
        return False, f"Error {res.status_code}: {res.text}"
    except Exception as e:
        return False, str(e)


def _etiqueta_transportista(t):
    return f"{t.get('nombre')} - {t.get('vehiculo')} {t.get('modelo') or ''} ({t.get('placa') or 'sin placa'})".replace("  ", " ")

def _panel_seguimiento(viaje, demo_seg, seguir, usar_osrm):
    ruta = obtener_ruta(viaje["origen"], viaje["destino"], usar_osrm)
    inicio = _parse_fecha(viaje.get("fecha_inicio"))
    transcurrido = max(0.0, (datetime.now(timezone.utc) - inicio).total_seconds())
    progreso = min(1.0, transcurrido / demo_seg)
    entregado = progreso >= 1.0

    lat, lon, km, indice = posicion_en_ruta(ruta, progreso)
    total = ruta["distancia_km"]
    restante = max(0.0, total - km)
    velocidad = 0 if entregado else 62 + 9 * math.sin(transcurrido / 4) + 4 * math.sin(transcurrido / 1.7)
    proximos = [h for h in ruta["hitos"] if h["km"] > km + 0.5]
    proximo = proximos[0] if proximos else None

    placa = viaje.get("placa") or "Camion"
    if entregado:
        st.success(f"Entregado en Bodega {viaje['destino']}.")
    else:
        st.info(f"En ruta: Bodega {viaje['origen']} a Bodega {viaje['destino']}")

    _estirar(
        st.pydeck_chart,
        construir_mapa(ruta, camion=(lat, lon), indice=indice, etiqueta=placa, seguir=seguir),
        height=520,
    )

    st.progress(progreso, text=f"Avance del viaje: {progreso * 100:.0f}%")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Velocidad", f"{velocidad:.0f} km/h")
    m2.metric("Recorrido", f"{km:,.0f} km")
    m3.metric("Restante", f"{restante:,.0f} km")
    m4.metric("ETA real estimada", "Llegó" if entregado else _fmt_horas(restante / VELOCIDAD_PROMEDIO_KMH))

    d1, d2, d3 = st.columns(3)
    d1.markdown(f"**Conductor:** {viaje.get('conductor') or 'N/A'}")
    d2.markdown(f"**Vehiculo:** {viaje.get('vehiculo') or ''} {viaje.get('modelo') or ''}".strip())
    d3.markdown(f"**Placa:** {viaje.get('placa') or 'N/A'}")

    if proximo and not entregado:
        st.markdown(f"**Proximo punto de control:** {proximo['nombre']} (a {proximo['km'] - km:,.0f} km)")

    st.caption(
        f"Ultima senal GPS (simulada): {datetime.now().strftime('%H:%M:%S')} | "
        f"Demo: faltan {_fmt_segundos(demo_seg - transcurrido)} para la llegada | {ruta['fuente']}"
    )


def _crear_panel(auto):
    """Usa st.fragment para refrescar solo el mapa cada pocos segundos."""
    if hasattr(st, "fragment"):
        try:
            return st.fragment(run_every=ACTUALIZACION_SEG if auto else None)(_panel_seguimiento)
        except TypeError:
            pass
    return _panel_seguimiento


def show_logistica(API_URL):
    st.header("Modulo de Logistica Inteligente")
    st.markdown("Gestion de transportistas, optimizacion de rutas y seguimiento de entregas.")

    tab1, tab2, tab3 = st.tabs(["Transportistas", "Viajes y Rutas", "Seguimiento en Vivo"])


    with tab1:
        st.subheader("Registro de Conductores y Vehiculos")

        mensaje = st.session_state.pop("flash_transportista", None)
        if mensaje:
            st.success(mensaje)

        with st.form("form_transportista", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre del Conductor")
            contacto = c2.text_input("Telefono / Contacto")
            c3, c4, c5 = st.columns(3)
            vehiculo = c3.selectbox("Tipo de Vehiculo", TIPOS_VEHICULO)
            modelo = c4.text_input("Marca / Modelo", placeholder="Ej: Kenworth T800")
            placa = c5.text_input("Placa", placeholder="Ej: TJK482", max_chars=7)
            enviar = st.form_submit_button("Registrar Transportista")

            if enviar:
                if nombre.strip() and placa.strip():
                    ok, resp = _api_post(API_URL, "/logistica/transportistas", {
                        "nombre": nombre,
                        "vehiculo": vehiculo,
                        "modelo": modelo,
                        "placa": placa.upper().replace(" ", ""),
                        "contacto": contacto,
                    })
                    if ok:
                        st.session_state["flash_transportista"] = "Transportista registrado con exito."
                        st.rerun()
                    else:
                        st.error(f"No se pudo registrar: {resp}")
                else:
                    st.warning("El nombre del conductor y la placa son obligatorios.")

        st.markdown("### Transportistas Activos")
        ok, transportistas = _api_get(API_URL, "/logistica/transportistas")
        if not ok:
            st.warning(f"No se pudieron cargar los transportistas: {transportistas}")
            transportistas = []
        elif transportistas:
            df = pd.DataFrame(transportistas).reindex(
                columns=["id", "nombre", "vehiculo", "modelo", "placa", "contacto"]
            )
            df.columns = ["ID", "Conductor", "Vehiculo", "Modelo", "Placa", "Contacto"]
            _estirar(st.dataframe, df.fillna(""), hide_index=True)
            st.caption(f"{len(df)} transportista(s) registrados.")
        else:
            st.info("No hay transportistas registrados todavia.")

        with st.expander("Datos de demostracion"):
            st.caption("Registra 4 conductores de ejemplo con vehiculo, modelo y placa (omite las placas que ya existan).")
            if st.button("Cargar conductores de demostracion"):
                existentes = {(t.get("placa") or "").upper() for t in transportistas}
                creados = 0
                for n, v, m, p, c in DEMO_TRANSPORTISTAS:
                    if p in existentes:
                        continue
                    ok_d, _ = _api_post(API_URL, "/logistica/transportistas", {
                        "nombre": n, "vehiculo": v, "modelo": m, "placa": p, "contacto": c,
                    })
                    creados += int(ok_d)
                st.session_state["flash_transportista"] = f"Se cargaron {creados} conductor(es) de demostracion."
                st.rerun()

    with tab2:
        st.subheader("Planificacion y Optimizacion de Rutas (Viajes)")

        ok_t, lista_t = _api_get(API_URL, "/logistica/transportistas")
        if not ok_t:
            st.error(f"No se pudo consultar los transportistas: {lista_t}")
            lista_t = []

        ciudades = list(BODEGAS.keys())
        col_o, col_d = st.columns(2)
        origen = col_o.selectbox(
            "Bodega de Origen", ciudades, format_func=lambda c: f"Bodega {c}", key="viaje_origen"
        )
        destinos = [c for c in ciudades if c != origen]
        destino = col_d.selectbox(
            "Bodega de Destino", destinos, format_func=lambda c: f"Bodega {c}", key="viaje_destino"
        )

        if lista_t:
            transportista = st.selectbox(
                "Conductor y Vehiculo asignado",
                lista_t,
                format_func=_etiqueta_transportista,
                key="viaje_transportista",
            )
        else:
            transportista = None
            st.warning("Primero registra un conductor en la pestana Transportistas (o carga los de demostracion).")

        usar_osrm = st.checkbox(
            "Trazar por carreteras reales (requiere internet)", value=True, key="usar_osrm"
        )

        ruta = obtener_ruta(origen, destino, usar_osrm)
        duracion_h = ruta["distancia_km"] / VELOCIDAD_PROMEDIO_KMH
        p1, p2, p3 = st.columns(3)
        p1.metric("Distancia", f"{ruta['distancia_km']:,.0f} km")
        p2.metric("Duracion estimada", _fmt_horas(duracion_h))
        p3.metric("Puntos de control", len(ruta["hitos"]))
        st.caption(ruta["fuente"])

        _estirar(st.pydeck_chart, construir_mapa(ruta), height=420)

        if st.button("Crear Viaje Logistico", type="primary", disabled=transportista is None):
            ok_v, resp = _api_post(API_URL, "/logistica/viajes", {
                "origen": origen,
                "destino": destino,
                "transportista_id": transportista["id"],
                "distancia_km": round(ruta["distancia_km"], 1),
                "duracion_estimada_h": round(duracion_h, 2),
            })
            if ok_v:
                st.success(
                    f"Viaje #{resp['id']} creado: Bodega {origen} a Bodega {destino}. "
                    "Abre la pestana Seguimiento en Vivo para ver el camion."
                )
            else:
                st.error(f"No se pudo crear el viaje: {resp}")

    with tab3:
        st.subheader("Seguimiento de Entregas")

        ok_s, viajes = _api_get(API_URL, "/logistica/viajes")
        if not ok_s:
            st.warning(f"Esperando conexion con el servicio de logistica: {viajes}")
        elif not viajes:
            st.info("No hay viajes en curso registrados. Crea uno en la pestana Viajes y Rutas.")
        else:
            por_id = {v["id"]: v for v in viajes}
            viaje_id = st.selectbox(
                "Viaje a monitorear",
                list(por_id.keys()),
                format_func=lambda i: (
                    f"Viaje #{i}: {por_id[i]['origen']} a {por_id[i]['destino']} "
                    f"- {por_id[i].get('conductor') or 'sin conductor'} ({por_id[i].get('placa') or 'sin placa'})"
                ),
                key="seg_viaje",
            )

            k1, k2, k3, k4 = st.columns(4)
            demo_min = k1.selectbox(
                "Duracion de la demo", [1, 2, 5, 10], index=1,
                format_func=lambda m: f"{m} min", key="seg_demo",
            )
            auto = k2.checkbox("Actualizar en vivo", value=True, key="seg_auto")
            seguir = k3.checkbox("Seguir al camion", value=False, key="seg_seguir")
            if k4.button("Reiniciar viaje"):
                ok_r, resp = _api_post(API_URL, f"/logistica/viajes/{viaje_id}/reiniciar")
                if ok_r:
                    st.rerun()
                else:
                    st.error(f"No se pudo reiniciar: {resp}")

            if not hasattr(st, "fragment"):
                st.caption(
                    "Tu version de Streamlit no actualiza el mapa sola. Usa el boton "
                    "Actualizar posicion o ejecuta: pip install -U streamlit"
                )
                st.button("Actualizar posicion")

            panel = _crear_panel(auto)
            panel(por_id[viaje_id], demo_min * 60, seguir, st.session_state.get("usar_osrm", True))

            with st.expander("Todos los viajes"):
                df_v = pd.DataFrame(viajes)
                df_v["Ruta"] = df_v["origen"] + " a " + df_v["destino"]
                df_v = df_v.reindex(
                    columns=["id", "Ruta", "conductor", "placa", "distancia_km", "estado", "fecha_inicio"]
                )
                df_v.columns = ["ID", "Ruta", "Conductor", "Placa", "Distancia (km)", "Estado", "Inicio (UTC)"]
                _estirar(st.dataframe, df_v.fillna(""), hide_index=True)