# // Importacion de la libreria hashlib para funciones de cifrado criptografico SHA-256 //
import hashlib
# // Importacion de la libreria qrcode para la generacion automatica de imagenes QR //
import qrcode
# // Importacion del modulo io para la manipulacion de flujos de datos binarios en memoria //
import io
# // Importacion de la clase datetime para la captura de fechas y marcas de tiempo UTC //
from datetime import datetime
# // Importacion de tipos de datos opcionales y listas para la anotacion de tipos en Python //
from typing import Optional, List
# // Importacion de clases principales del framework FastAPI para la gestion de rutas e interacciones HTTP //
from fastapi import FastAPI, Depends, HTTPException, Response
# // Importacion de StreamingResponse para transmitir archivos binarios como PDF en las respuestas HTTP //
from fastapi.responses import StreamingResponse
# // Importacion de Session para la gestion de sesiones y transacciones con SQLAlchemy //
from sqlalchemy.orm import Session
# // Importacion de BaseModel desde Pydantic para la definicion de esquemas de validacion de datos //
from pydantic import BaseModel

# // Importacion de la dimension de pagina letter desde ReportLab para documentos PDF //
from reportlab.lib.pagesizes import letter # type: ignore
# // Importacion de la clase canvas desde ReportLab para renderizar texto y graficos en el PDF //
from reportlab.pdfgen import canvas # type: ignore

# // Importacion de los modelos ORM definidos en el modulo interno de la aplicacion //
import models
# // Importacion del motor de base de datos y del generador de sesiones desde el modulo database //
from backend.database import engine, get_db

# // Instruccion que crea dinamicamente las tablas en SQLite si no existen en la base de datos //
models.Base.metadata.create_all(bind=engine)

# // Inicializacion de la aplicacion FastAPI con la configuracion del titulo principal //
app = FastAPI(title="Plataforma de Operaciones Inteligentes - PyMEs")

# // Definicion de la clase de esquema Pydantic para la creacion de nuevos lotes //
class LoteCreate(BaseModel):
    # // Declaracion del campo obligatorio nombre_producto de tipo cadena de texto //
    nombre_producto: str
    # // Declaracion del campo opcional descripcion con valor por defecto asignado a None //
    descripcion: Optional[str] = None

# // Definicion de la clase de esquema Pydantic para el registro de eventos de trazabilidad //
class EventoCreate(BaseModel):
    # // Declaracion del campo obligatorio hito para definir la etapa operativa //
    hito: str
    # // Declaracion del campo obligatorio usuario para identificar al responsable //
    usuario: str
    # // Declaracion del campo opcional ubicacion para especificar el lugar del evento //
    ubicacion: Optional[str] = None

# // Definicion de la funcion auxiliar encargada de calcular el hash criptografico SHA-256 //
def calcular_hash(data: str) -> str:
    # // Codificacion de la cadena a bytes UTF-8, calculo del resumen SHA-256 y retorno en hexadecimal //
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

# // Decorador de ruta HTTP GET para la raiz del servicio //
@app.get("/")
# // Funcion controladora para verificar el funcionamiento inicial del servidor //
def read_root():
    # // Retorno de un diccionario convertido automaticamente a JSON con el mensaje de confirmacion //
    return {"mensaje": "API de la Plataforma iniciada y Base de Datos SQLite conectada"}

# ---- MÓDULO 1: TRAZABILIDAD INTELIGENTE ----

# // Decorador de ruta HTTP POST para la creacion de lotes de produccion //
@app.post("/lotes")
# // Funcion controladora para crear un lote de produccion inyectando la sesion de la base de datos //
def crear_lote(lote_data: LoteCreate, db: Session = Depends(get_db)):
    # // Creacion de la instancia del modelo Lote con los datos validados del esquema //
    nuevo_lote = models.Lote(
        # // Asignacion de la variable nombre_producto desde el objeto recibido //
        nombre_producto=lote_data.nombre_producto,
        # // Asignacion de la variable descripcion desde el objeto recibido //
        descripcion=lote_data.descripcion
    )
    # // Construccion de la cadena de texto base concatenando ID, producto y fecha de creacion //
    datos_iniciales = f"{nuevo_lote.lote_id}-{nuevo_lote.nombre_producto}-{nuevo_lote.fecha_creacion}"
    # // Generacion e insercion del hash criptografico inicial del lote //
    nuevo_lote.hash_actual = calcular_hash(datos_iniciales)
    
    # // Registro del objeto nuevo_lote dentro de la sesion actual de la base de datos //
    db.add(nuevo_lote)
    # // Ejecucion de la transaccion commit para guardar permanentemente en SQLite //
    db.commit()
    # // Recarga de la instancia para obtener los valores autogenerados por la base de datos //
    db.refresh(nuevo_lote)
    # // Retorno del objeto lote completo registrado en formato JSON //
    return nuevo_lote

# // Decorador de ruta HTTP GET para consultar el listado general de lotes //
@app.get("/lotes")
# // Funcion controladora que obtiene todos los lotes de la base de datos //
def obtener_lotes(db: Session = Depends(get_db)):
    # // Consulta ORM que extrae la totalidad de filas almacenadas en la tabla de lotes //
    return db.query(models.Lote).all()

# // Decorador de ruta HTTP GET para obtener un lote especifico mediante su identificador UUID //
@app.get("/lotes/{lote_id}")
# // Funcion controladora para recuperar un lote mediante su parámetro de ruta lote_id //
def obtener_lote_detalle(lote_id: str, db: Session = Depends(get_db)):
    # // Busqueda en la tabla lotes filtrando por el valor exacto del lote_id //
    lote = db.query(models.Lote).filter(models.Lote.lote_id == lote_id).first()
    # // Condicional para verificar si la consulta no devolvio ningun resultado //
    if not lote:
        # // Lanzamiento de excepcion de HTTP con codigo 404 notificando que no se encontro el registro //
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    # // Retorno del objeto lote encontrado //
    return lote

# // Decorador de ruta HTTP POST para agregar un evento a la cadena de custodia del lote //
@app.post("/lotes/{lote_id}/eventos")
# // Funcion controladora para registrar un nuevo evento aplicando hashing encadenado //
def registrar_evento(lote_id: str, evento: EventoCreate, db: Session = Depends(get_db)):
    # // Recuperacion del lote sobre el cual se va a agregar el nuevo hito operativo //
    lote = db.query(models.Lote).filter(models.Lote.lote_id == lote_id).first()
    # // Evaluacion de existencia del lote //
    if not lote:
        # // Notificacion de error HTTP 404 en caso de que el ID proporcionado sea inexistente //
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    
    # // Captura del valor del hash actual para usarlo como referencia del bloque previo //
    hash_anterior = lote.hash_actual
    # // Generacion de la marca de tiempo exacta de la transaccion en formato UTC //
    timestamp_actual = datetime.utcnow()
    
    # // Concatenacion de los componentes del evento para la construccion del bloque criptografico //
    str_para_hash = f"{lote_id}-{evento.hito}-{evento.usuario}-{timestamp_actual}-{hash_anterior}"
    # // Calculo del nuevo hash criptografico derivado de los datos y del hash previo //
    nuevo_hash = calcular_hash(str_para_hash)
    
    # // Instanciacion de la entidad EventoTrazabilidad con sus correspondientes valores //
    nuevo_evento = models.EventoTrazabilidad(
        # // Asignacion de la clave foranea lote_id //
        lote_id=lote_id,
        # // Asignacion del texto representativo del hito alcanzado //
        hito=evento.hito,
        # // Asignacion del nombre del usuario que registra la operacion //
        usuario=evento.usuario,
        # // Asignacion de la ubicacion fisica o planta de la operacion //
        ubicacion=evento.ubicacion,
        # // Asignacion de la marca de tiempo generada //
        timestamp=timestamp_actual,
        # // Registro del hash anterior para garantizar la inmutabilidad de la cadena //
        hash_anterior=hash_anterior,
        # // Registro del nuevo hash generado para la validacion del bloque actual //
        hash_evento=nuevo_hash
    )
    
    # // Actualizacion de la variable hash_actual dentro del modelo del lote principal //
    lote.hash_actual = nuevo_hash
    # // Actualizacion del estado operativo del lote al ultimo hito registrado //
    lote.estado = evento.hito
    
    # // Insercion del nuevo evento en la sesion ORM //
    db.add(nuevo_evento)
    # // Confirmacion de los cambios en la base de datos //
    db.commit()
    # // Actualizacion del objeto para obtener los datos definitivos persistidos //
    db.refresh(nuevo_evento)
    # // Retorno del registro del evento en la respuesta HTTP //
    return nuevo_evento

# // Decorador de ruta HTTP GET para consultar la lista de eventos pertenecientes a un lote //
@app.get("/lotes/{lote_id}/eventos")
# // Funcion controladora para recuperar la historia cronologica de custodia de un lote //
def obtener_historial_eventos(lote_id: str, db: Session = Depends(get_db)):
    # // Consulta ORM filtrada por ID de lote y ordenada cronologicamente por timestamp //
    return db.query(models.EventoTrazabilidad).filter(models.EventoTrazabilidad.lote_id == lote_id).order_by(models.EventoTrazabilidad.timestamp.asc()).all()

# // Decorador de ruta HTTP GET para generar dinamicamente el codigo QR de un lote //
@app.get("/lotes/{lote_id}/qr")
# // Funcion controladora que procesa la imagen binaria del codigo QR //
def generar_qr_lote(lote_id: str):
    # // Generacion de la matriz del codigo QR codificando la cadena del UUID del lote //
    img = qrcode.make(lote_id)
    # // Inicializacion de la variable buf como un buffer en memoria mediante BytesIO //
    buf = io.BytesIO()
    # // Guardado de la imagen generada dentro del buffer en formato PNG //
    img.save(buf, format="PNG")
    # // Reposicionamiento del puntero de lectura al inicio del buffer binario //
    buf.seek(0)
    # // Retorno de la respuesta binaria especificando el tipo de contenido como image/png //
    return Response(content=buf.getvalue(), media_type="image/png")

# // Decorador de ruta HTTP GET para generar y transmitir el certificado digital en PDF //
@app.get("/lotes/{lote_id}/certificado_pdf")
# // Funcion controladora encargada de la maquetacion y exportacion del reporte PDF //
def generar_certificado_pdf(lote_id: str, db: Session = Depends(get_db)):
    # // Busqueda del registro de lote por identificador unico //
    lote = db.query(models.Lote).filter(models.Lote.lote_id == lote_id).first()
    # // Validacion de existencia del registro en la base de datos //
    if not lote:
        # // Lanzamiento de excepcion HTTP 404 si el lote no existe //
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    
    # // Consulta ORM para obtener la secuencia cronologica de eventos del lote //
    eventos = db.query(models.EventoTrazabilidad).filter(models.EventoTrazabilidad.lote_id == lote_id).order_by(models.EventoTrazabilidad.timestamp.asc()).all()
    
    # // Creacion del objeto buffer binario en memoria para almacenar el PDF //
    buffer = io.BytesIO()
    # // Instanciacion del lienzo Canvas de ReportLab pasando el buffer y tamaño de hoja letter //
    pdf = canvas.Canvas(buffer, pagesize=letter)
    
    # // Asignacion de tipografia Helvetica-Bold de tamano 16 para el titulo superior //
    pdf.setFont("Helvetica-Bold", 16)
    # // Escritura del titulo en la coordenada horizontal 100 y vertical 750 //
    pdf.drawString(100, 750, "CERTIFICADO DIGITAL DE TRAZABILIDAD")
    # // Asignacion de tipografia Helvetica regular de tamano 10 para el subtitulo //
    pdf.setFont("Helvetica", 10)
    # // Escritura del nombre de la plataforma en la coordenada Y 735 //
    pdf.drawString(100, 735, "Plataforma de Operaciones Inteligentes - PyMEs")
    # // Dibujo de linea horizontal de separacion desde X=100 hasta X=500 en Y=725 //
    pdf.line(100, 725, 500, 725)
    
    # // Asignacion de tipografia Helvetica-Bold tamano 11 para la seccion de datos //
    pdf.setFont("Helvetica-Bold", 11)
    # // Escritura de la linea descriptiva con el nombre del producto //
    pdf.drawString(100, 695, f"Producto: {lote.nombre_producto}")
    # // Escritura de la linea con el UUID identificador del lote //
    pdf.drawString(100, 680, f"ID Lote (UUID): {lote.lote_id}")
    # // Escritura de la linea con el estado operativo actual del lote //
    pdf.drawString(100, 665, f"Estado Actual: {lote.estado}")
    # // Escritura de la linea con la muestra truncada del hash criptografico //
    pdf.drawString(100, 650, f"Hash Inmutable Final: {lote.hash_actual[:25]}...")
    
    # // Dibujo de segunda linea divisoria horizontal en Y=635 //
    pdf.line(100, 635, 500, 635)
    # // Escritura del titulo del encabezado del historial de custodia //
    pdf.drawString(100, 615, "Historial de Cadena de Custodia:")
    
    # // Declaracion e inicializacion de la variable de posicion vertical y en 590 //
    y = 590
    # // Asignacion de tipografia Helvetica regular tamano 9 para los detalles //
    pdf.setFont("Helvetica", 9)
    # // Estructura de bucle para recorrer cada uno de los eventos recuperados //
    for ev in eventos:
        # // Renderizado de texto formateado con fecha, hito, usuario y ubicacion del evento //
        pdf.drawString(110, y, f"• [{ev.timestamp.strftime('%Y-%m-%d %H:%M')}] {ev.hito} - Resp: {ev.usuario} ({ev.ubicacion or 'N/A'})")
        # // Decremento del valor de la coordenada Y para mover el cursor a la siguiente linea //
        y -= 20
        # // Condicional de control de salto de pagina si Y alcanza el margen inferior //
        if y < 100:
            # // Creacion e impresion de una nueva pagina vacia en el documento PDF //
            pdf.showPage()
            # // Reestablecimiento del puntero vertical Y a la posicion superior 750 //
            y = 750
            
    # // Cierre y finalizacion de la estructura del documento PDF en el lienzo //
    pdf.save()
    # // Reubicacion del puntero de lectura del buffer al inicio del stream binario //
    buffer.seek(0)
    # // Retorno de la respuesta con flujo StreamingResponse y cabecera HTTP de descarga de archivo //
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Certificado_{lote_id[:8]}.pdf"})