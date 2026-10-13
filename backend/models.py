import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Float
from sqlalchemy.orm import relationship
from backend.database import Base

class Lote(Base):
    __tablename__ = "lotes"

    lote_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    nombre_producto = Column(String, nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    hash_actual = Column(String, nullable=True)
    estado = Column(String, default="Produccion")

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

class Transportista(Base):
    __tablename__ = "transportistas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String, nullable=False)      # nombre del conductor
    vehiculo = Column(String, nullable=False)    # tipo de vehiculo (Tractomula, Furgon, ...)
    modelo = Column(String, nullable=True)       # marca / modelo (Kenworth T800, ...)
    placa = Column(String, nullable=True)
    contacto = Column(String, nullable=True)

class ViajeLogistico(Base):
    __tablename__ = "viajes_logisticos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    origen = Column(String, nullable=False)
    destino = Column(String, nullable=False)
    transportista_id = Column(Integer, ForeignKey("transportistas.id"), nullable=False)
    estado = Column(String, default="En Ruta")
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    distancia_km = Column(Float, nullable=True)
    duracion_estimada_h = Column(Float, nullable=True)