import os
import uuid
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, Numeric, String, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List

# ----------------------------------------------------
# 1. CONEXIÓN 
# ----------------------------------------------------
SERVER_SOURCE = ''  

if SERVER_SOURCE == 'local':
    db_name = "pueblost_bd"
    db_user = "root"
    db_pass = ""     
    db_host = "localhost"
else:
    db_name = "u960560109_prueba"
    db_user = "u960560109_test"
    db_pass = "prueba.BD2026"
    db_host = "srv1442.hstgr.io" 

DATABASE_URL = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}"

engine = create_engine(DATABASE_URL, pool_recycle=3600, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ----------------------------------------------------
# 2. MODELOS DE BASE DE DATOS 
# ----------------------------------------------------
class PropertyDB(Base):
    __tablename__ = "properties_tb"
    prop_id = Column(Integer, primary_key=True, index=True)
    prop_uuid = Column(String(36), unique=True, nullable=False)
    prop_slug = Column(String(100), unique=True, nullable=False)
    prop_name = Column(String(150), nullable=False)
    prop_price = Column(Numeric(10, 2), nullable=True)

class SceneDB(Base):
    __tablename__ = "scenes_tb"
    sce_id = Column(Integer, primary_key=True, index=True)
    sce_prop_id = Column(Integer, ForeignKey("properties_tb".prop_id, ondelete="CASCADE"), nullable=False)
    sce_key = Column(String(50), nullable=False)
    sce_title = Column(String(100), nullable=False)
    sce_panorama_url = Column(String(500), nullable=False)

class HotspotDB(Base):
    __tablename__ = "hotspots_tb"
    hots_id = Column(Integer, primary_key=True, index=True)
    hots_scene_id = Column(Integer, ForeignKey("scenes_tb.sce_id", ondelete="CASCADE"), nullable=False)
    hots_pitch = Column(Numeric(5, 2), nullable=False)
    hots_yaw = Column(Numeric(5, 2), nullable=False)
    hots_type = Column(Enum('scene', 'info', name="hots_type_enum"), nullable=False)
    hots_text = Column(String(255), nullable=False)
    hots_target_scene_key = Column(String(50), nullable=True)

Base.metadata.create_all(bind=engine)

# ----------------------------------------------------
# 3. ESQUEMAS DE VALIDACIÓN (Pydantic)
# ----------------------------------------------------
class PropertyCreate(BaseModel):
    prop_name: str
    prop_price: float
    prop_slug: str

class SceneCreate(BaseModel):
    sce_prop_id: int
    sce_title: str
    sce_key: Optional[str] = None
    sce_panorama_url: Optional[str] = "default.jpg"

class HotspotCreate(BaseModel):
    hots_scene_id: int
    hots_title: str
    hots_type: str
    hots_pitch: float
    hots_yaw: float
    target_scene_key: Optional[str] = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------------------------------
# 4. INICIALIZACIÓN Y MIDDLEWARES
# ----------------------------------------------------
app = FastAPI(title="Administrador de Recorridos 360")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# 5. ENDPOINTS CRUD
# ----------------------------------------------------

# --- PROPIEDADES ---
@app.get("/api/properties")
def get_properties(db: Session = Depends(get_db)):
    return db.query(PropertyDB).all()

@app.post("/api/properties")
def create_property(prop: PropertyCreate, db: Session = Depends(get_db)):
    nueva = PropertyDB(
        prop_uuid=str(uuid.uuid4()),
        prop_slug=prop.prop_slug.lower().strip().replace(" ", "-"),
        prop_name=prop.prop_name,
        prop_price=prop.prop_price
    )
    try:
        db.add(nueva)
        db.commit()
        db.refresh(nueva)
        return {"status": "success", "data": nueva}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="El Slug ya existe.")

@app.delete("/api/properties/{prop_id}")
def delete_property(prop_id: int, db: Session = Depends(get_db)):
    p = db.query(PropertyDB).filter(PropertyDB.prop_id == prop_id).first()
    if not p: raise HTTPException(status_code=404)
    db.delete(p)
    db.commit()
    return {"status": "success"}

# --- ESCENAS ---
@app.get("/api/properties/{prop_id}/scenes")
def get_scenes_by_property(prop_id: int, db: Session = Depends(get_db)):
    return db.query(SceneDB).filter(SceneDB.sce_prop_id == prop_id).all()

@app.post("/api/scenes")
def create_scene(scene: SceneCreate, db: Session = Depends(get_db)):
    if not scene.sce_key:
        scene.sce_key = f"scene_{uuid.uuid4().hex[:8]}"
    nueva = SceneDB(
        sce_prop_id=scene.sce_prop_id,
        sce_key=scene.sce_key,
        sce_title=scene.sce_title,
        sce_panorama_url=scene.sce_panorama_url
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return {"status": "success", "data": nueva}

@app.delete("/api/scenes/{sce_id}")
def delete_scene(sce_id: int, db: Session = Depends(get_db)):
    s = db.query(SceneDB).filter(SceneDB.sce_id == sce_id).first()
    if not s: raise HTTPException(status_code=404)
    db.delete(s)
    db.commit()
    return {"status": "success"}

# --- HOTSPOTS ---
@app.get("/api/scenes/{sce_id}/hotspots")
def get_hotspots_by_scene(sce_id: int, db: Session = Depends(get_db)):
    hotspots = db.query(HotspotDB).filter(HotspotDB.hots_scene_id == sce_id).all()
    return [{
        "hots_id": h.hots_id,
        "hots_scene_id": h.hots_scene_id,
        "hots_title": h.hots_text,
        "hots_type": h.hots_type,
        "hots_pitch": float(h.hots_pitch),
        "hots_yaw": float(h.hots_yaw),
        "target_scene_key": h.hots_target_scene_key
    } for h in hotspots]

@app.post("/api/hotspots")
def create_hotspot(hotspot: HotspotCreate, db: Session = Depends(get_db)):
    nuevo = HotspotDB(
        hots_scene_id=hotspot.hots_scene_id,
        hots_pitch=hotspot.hots_pitch,
        hots_yaw=hotspot.hots_yaw,
        hots_type=hotspot.hots_type,
        hots_text=hotspot.hots_title,
        hots_target_scene_key=hotspot.target_scene_key if hotspot.hots_type == 'scene' else None
    )
    try:
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return {"status": "success", "id": nuevo.hots_id}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de relación de llaves foráneas.")

@app.put("/api/hotspots/{hots_id}")
def update_hotspot(hots_id: int, hotspot: HotspotCreate, db: Session = Depends(get_db)):
    db_h = db.query(HotspotDB).filter(HotspotDB.hots_id == hots_id).first()
    if not db_h: raise HTTPException(status_code=404)
    db_h.hots_scene_id = hotspot.hots_scene_id
    db_h.hots_pitch = hotspot.hots_pitch
    db_h.hots_yaw = hotspot.hots_yaw
    db_h.hots_type = hotspot.hots_type
    db_h.hots_text = hotspot.hots_title
    db_h.hots_target_scene_key = hotspot.target_scene_key if hotspot.hots_type == 'scene' else None
    db.commit()
    return {"status": "success"}

@app.delete("/api/hotspots/{hots_id}")
def delete_hotspot(hots_id: int, db: Session = Depends(get_db)):
    h = db.query(HotspotDB).filter(HotspotDB.hots_id == hots_id).first()
    if not h: raise HTTPException(status_code=404)
    db.delete(h)
    db.commit()
    return {"status": "success"}

@app.get("/admin", response_class=HTMLResponse)
def admin_panel():
    with open("admin.html", "r", encoding="utf-8") as f: return f.read()
