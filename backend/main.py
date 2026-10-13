import io
import hashlib
import qrcode
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from reportlab.lib.pagesizes import letter  
from reportlab.pdfgen import canvas

from backend import models
from backend.database import engine, get_db
from backend.logistica_routes import router as logistica_router

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Plataforma de Operaciones Inteligentes - PyMEs")

app.include_router(logistica_router)

class LoteCreate(BaseModel):
    nombre_producto: str
    descripcion: Optional[str] = None

class EventoCreate(BaseModel):
    hito: str
    usuario: str
    ubicacion: Optional[str] = None

def calcular_hash(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

@app.get("/")
def read_root():
    return {"mensaje": "API de la Plataforma iniciada y Base de Datos conectada"}

# ---- MÓDULO 1: TRAZABILIDAD INTELIGENTE ----

@app.post("/lotes")
def crear_lote(lote_data: LoteCreate, db: Session = Depends(get_db)):
    nuevo_lote = models.Lote(
        nombre_producto=lote_data.nombre_producto,
        descripcion=lote_data.descripcion
    )
    datos_iniciales = f"{nuevo_lote.lote_id}-{nuevo_lote.nombre_producto}-{nuevo_lote.fecha_creacion}"
    nuevo_lote.hash_actual = calcular_hash(datos_iniciales)
    
    db.add(nuevo_lote)
    db.commit()
    db.refresh(nuevo_lote)
    return nuevo_lote

@app.get("/lotes")
def obtener_lotes(db: Session = Depends(get_db)):
    return db.query(models.Lote).all()

@app.get("/lotes/{lote_id}")
def obtener_lote_detalle(lote_id: str, db: Session = Depends(get_db)):
    lote = db.query(models.Lote).filter(models.Lote.lote_id == lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return lote

@app.post("/lotes/{lote_id}/eventos")
def registrar_evento(lote_id: str, evento: EventoCreate, db: Session = Depends(get_db)):
    lote = db.query(models.Lote).filter(models.Lote.lote_id == lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    
    hash_anterior = lote.hash_actual
    timestamp_actual = datetime.utcnow()
    
    str_para_hash = f"{lote_id}-{evento.hito}-{evento.usuario}-{timestamp_actual}-{hash_anterior}"
    nuevo_hash = calcular_hash(str_para_hash)
    
    nuevo_evento = models.EventoTrazabilidad(
        lote_id=lote_id,
        hito=evento.hito,
        usuario=evento.usuario,
        ubicacion=evento.ubicacion,
        timestamp=timestamp_actual,
        hash_anterior=hash_anterior,
        hash_evento=nuevo_hash
    )
    
    lote.hash_actual = nuevo_hash
    lote.estado = evento.hito
    
    db.add(nuevo_evento)
    db.commit()
    db.refresh(nuevo_evento)
    return nuevo_evento

@app.get("/lotes/{lote_id}/eventos")
def obtener_historial_eventos(lote_id: str, db: Session = Depends(get_db)):
    return db.query(models.EventoTrazabilidad).filter(models.EventoTrazabilidad.lote_id == lote_id).order_by(models.EventoTrazabilidad.timestamp.asc()).all()

@app.get("/lotes/{lote_id}/qr")
def generar_qr_lote(lote_id: str):
    img = qrcode.make(lote_id)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")

@app.get("/lotes/{lote_id}/certificado_pdf")
def generar_certificado_pdf(lote_id: str, db: Session = Depends(get_db)):
    lote = db.query(models.Lote).filter(models.Lote.lote_id == lote_id).first()
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    
    eventos = db.query(models.EventoTrazabilidad).filter(models.EventoTrazabilidad.lote_id == lote_id).order_by(models.EventoTrazabilidad.timestamp.asc()).all()
    
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(100, 750, "CERTIFICADO DIGITAL DE TRAZABILIDAD")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(100, 735, "Plataforma de Operaciones Inteligentes - PyMEs")
    pdf.line(100, 725, 500, 725)
    
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(100, 695, f"Producto: {lote.nombre_producto}")
    pdf.drawString(100, 680, f"ID Lote (UUID): {lote.lote_id}")
    pdf.drawString(100, 665, f"Estado Actual: {lote.estado}")
    pdf.drawString(100, 650, f"Hash Inmutable Final: {lote.hash_actual[:25]}...")
    
    pdf.line(100, 635, 500, 635)
    pdf.drawString(100, 615, "Historial de Cadena de Custodia:")
    
    y = 590
    pdf.setFont("Helvetica", 9)
    for ev in eventos:
        pdf.drawString(110, y, f"• [{ev.timestamp.strftime('%Y-%m-%d %H:%M')}] {ev.hito} - Resp: {ev.usuario} ({ev.ubicacion or 'N/A'})")
        y -= 20
        if y < 100:
            pdf.showPage()
            y = 750
            
    pdf.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Certificado_{lote_id[:8]}.pdf"})