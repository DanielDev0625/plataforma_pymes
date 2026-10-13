from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from backend.database import Base
from backend.models import Transportista, ViajeLogistico

try:
    from backend.database import get_db
except ImportError:  # pragma: no cover
    from backend.database import SessionLocal

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()


router = APIRouter(prefix="/logistica", tags=["Logistica Inteligente"])

_esquema_listo = False


def _asegurar_esquema(db: Session):
    """Crea las tablas si faltan y agrega, sin borrar datos, cualquier columna
    del modelo que no exista todavia en la base de datos."""
    global _esquema_listo
    if _esquema_listo:
        return
    engine = db.get_bind()
    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)
    with engine.begin() as conn:
        for modelo in (Transportista, ViajeLogistico):
            tabla = modelo.__table__
            existentes = {c["name"] for c in insp.get_columns(tabla.name)}
            for col in tabla.columns:
                if col.name not in existentes:
                    tipo = col.type.compile(dialect=engine.dialect)
                    conn.execute(text(f"ALTER TABLE {tabla.name} ADD COLUMN {col.name} {tipo}"))
    _esquema_listo = True


def get_db_logistica(db: Session = Depends(get_db)):
    _asegurar_esquema(db)
    return db

class TransportistaCreate(BaseModel):
    nombre: str
    vehiculo: str
    modelo: Optional[str] = ""
    placa: Optional[str] = ""
    contacto: Optional[str] = ""


class TransportistaResponse(TransportistaCreate):
    id: int

    class Config:
        from_attributes = True


class ViajeCreate(BaseModel):
    origen: str
    destino: str
    transportista_id: int
    distancia_km: Optional[float] = None
    duracion_estimada_h: Optional[float] = None


class ViajeResponse(ViajeCreate):
    id: int
    estado: str
    fecha_inicio: Optional[str] = None
    conductor: Optional[str] = None
    vehiculo: Optional[str] = None
    modelo: Optional[str] = None
    placa: Optional[str] = None


def _viaje_a_dict(v: ViajeLogistico, t: Optional[Transportista]) -> dict:
    return {
        "id": v.id,
        "origen": v.origen,
        "destino": v.destino,
        "transportista_id": v.transportista_id,
        "distancia_km": v.distancia_km,
        "duracion_estimada_h": v.duracion_estimada_h,
        "estado": v.estado or "En Ruta",
        "fecha_inicio": v.fecha_inicio.isoformat() if v.fecha_inicio else None,
        "conductor": t.nombre if t else None,
        "vehiculo": t.vehiculo if t else None,
        "modelo": t.modelo if t else None,
        "placa": t.placa if t else None,
    }

@router.post("/transportistas", response_model=TransportistaResponse)
def crear_transportista(data: TransportistaCreate, db: Session = Depends(get_db_logistica)):
    nuevo = Transportista(
        nombre=data.nombre.strip(),
        vehiculo=data.vehiculo.strip(),
        modelo=(data.modelo or "").strip(),
        placa=(data.placa or "").strip().upper(),
        contacto=(data.contacto or "").strip(),
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.get("/transportistas", response_model=List[TransportistaResponse])
def listar_transportistas(db: Session = Depends(get_db_logistica)):
    return db.query(Transportista).order_by(Transportista.id).all()


@router.post("/viajes", response_model=ViajeResponse)
def crear_viaje(data: ViajeCreate, db: Session = Depends(get_db_logistica)):
    transportista = db.query(Transportista).filter(Transportista.id == data.transportista_id).first()
    if not transportista:
        raise HTTPException(status_code=404, detail="El transportista indicado no existe.")
    if data.origen == data.destino:
        raise HTTPException(status_code=400, detail="El origen y el destino deben ser distintos.")

    viaje = ViajeLogistico(
        origen=data.origen,
        destino=data.destino,
        transportista_id=data.transportista_id,
        estado="En Ruta",
        fecha_inicio=datetime.utcnow(),
        distancia_km=data.distancia_km,
        duracion_estimada_h=data.duracion_estimada_h,
    )
    db.add(viaje)
    db.commit()
    db.refresh(viaje)
    return _viaje_a_dict(viaje, transportista)


@router.get("/viajes", response_model=List[ViajeResponse])
def listar_viajes(db: Session = Depends(get_db_logistica)):
    viajes = db.query(ViajeLogistico).order_by(ViajeLogistico.id.desc()).all()
    transportistas = {t.id: t for t in db.query(Transportista).all()}
    return [_viaje_a_dict(v, transportistas.get(v.transportista_id)) for v in viajes]


@router.post("/viajes/{viaje_id}/reiniciar", response_model=ViajeResponse)
def reiniciar_viaje(viaje_id: int, db: Session = Depends(get_db_logistica)):
    """Vuelve a poner el camion en el origen (util para repetir la demostracion)."""
    viaje = db.query(ViajeLogistico).filter(ViajeLogistico.id == viaje_id).first()
    if not viaje:
        raise HTTPException(status_code=404, detail="Viaje no encontrado.")
    viaje.fecha_inicio = datetime.utcnow()
    viaje.estado = "En Ruta"
    db.commit()
    db.refresh(viaje)
    t = db.query(Transportista).filter(Transportista.id == viaje.transportista_id).first()
    return _viaje_a_dict(viaje, t)


@router.delete("/viajes/{viaje_id}")
def eliminar_viaje(viaje_id: int, db: Session = Depends(get_db_logistica)):
    viaje = db.query(ViajeLogistico).filter(ViajeLogistico.id == viaje_id).first()
    if not viaje:
        raise HTTPException(status_code=404, detail="Viaje no encontrado.")
    db.delete(viaje)
    db.commit()
    return {"ok": True}