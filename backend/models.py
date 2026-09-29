import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class Lote(Base):
    __tablename__ = "lotes"

    lote_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    nombre_producto = Column(String, nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    hash_actual = Column(String, nullable=True)
    estado = Column(String, default="Producción")

    eventos = relationship("EventoTrazabilidad", back_populates="lote")

class EventoTrazabilidad(Base):
    __tablename__ = "eventos_trazabilidad"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lote_id = Column(String, ForeignKey("lotes.lote_id"), nullable=False)
    hito = Column(String, nullable=False)  # ej: Control de Calidad, Empaque, Despacho
    usuario = Column(String, nullable=False)
    ubicacion = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    hash_anterior = Column(String, nullable=True)
    hash_evento = Column(String, nullable=False)

    lote = relationship("Lote", back_populates="eventos")