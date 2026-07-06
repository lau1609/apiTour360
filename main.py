import os
import uuid
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, Numeric, String, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ----------------------------------------------------
# 1. CONEXIÓN 
# ----------------------------------------------------
SERVER_SOURCE = ''  # Cambia a 'production' o usa os.getenv en Coolify

if SERVER_SOURCE == 'local':
    root_path = 'https://localhost/atlastest/'
    db_name = "pueblost_bd"
    db_user = "root"
    db_pass = ""     
    db_host = "localhost"
else:
    root_path = 'https://sichitur.org/' 
    db_name = "u960560109_prueba"
    db_user = "u960560109_test"
    db_pass = "prueba.BD2026"
    db_host = "srv1442.hstgr.io" 

DATABASE_URL = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}"

engine = create_engine(
    DATABASE_URL,
    pool_recycle=3600, 
    pool_pre_ping=True
)

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

class HotspotDB(Base):
    __tablename__ = "hotspots_tb"
    
    hots_id = Column(Integer, primary_key=True, index=True)
    hots_scene_id = Column(Integer, nullable=False)
    hots_pitch = Column(Numeric(5, 2), nullable=False)
    hots_yaw = Column(Numeric(5, 2), nullable=False)

    hots_type = Column(Enum('scene', 'info', name="hots_type_enum"), nullable=False)
    hots_text = Column(String(255), nullable=False)
    hots_target_scene_key = Column(String(50), nullable=True)

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Error creando tablas: {e}")
    
# Crear tablas automáticamente en la base de datos si no existen
Base.metadata.create_all(bind=engine)

# ----------------------------------------------------
# 3. ESQUEMAS DE VALIDACIÓN (Pydantic)
# ----------------------------------------------------
class PropertyCreate(BaseModel):
    prop_name: str
    prop_price: float
    prop_slug: str

class HotspotCreate(BaseModel):
    prop_id: int
    hots_title: str
    hots_type: str
    hots_pitch: float
    hots_yaw: float
    target_prop_id: int = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------------------------------
# 4. INICIALIZACIÓN DE FASTAPI Y MIDDLEWARES
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
# 5. ENDPOINTS DE LA API (Datos)
# ----------------------------------------------------

@app.get("/api/properties")
def get_properties(db: Session = Depends(get_db)):
    return db.query(PropertyDB).all()

@app.post("/api/properties")
def create_property(prop: PropertyCreate, db: Session = Depends(get_db)):
    nuevo_uuid = str(uuid.uuid4())
    
    nueva_propiedad = PropertyDB(
        prop_uuid=nuevo_uuid,
        prop_slug=prop.prop_slug.lower().strip().replace(" ", "-"),
        prop_name=prop.prop_name,
        prop_price=prop.prop_price
    )
    try:
        db.add(nueva_propiedad)
        db.commit()
        db.refresh(nueva_propiedad)
        return {"status": "success", "data": nueva_propiedad}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="El identificador único (Slug) o Nombre ya existe.")

# --- NUEVOS ENDPOINTS PARA HOTSPOTS ---

# 1. Enlistar todos los Hotspots de una propiedad específica
@app.get("/api/properties/{prop_id}/hotspots")
def get_hotspots_by_property(prop_id: int, db: Session = Depends(get_db)):
    hotspots = db.query(HotspotDB).filter(HotspotDB.hots_scene_id == prop_id).all()
    
    # Formateamos la respuesta para que el JS la lea directamente sin modificar sus llaves
    respuesta_js = []
    for h in hotspots:
        respuesta_js.append({
            "hots_id": h.hots_id,
            "prop_id": h.hots_scene_id,
            "hots_title": h.hots_text,
            "hots_type": h.hots_type,
            "hots_pitch": float(h.hots_pitch),
            "hots_yaw": float(h.hots_yaw),
            "target_prop_id": int(h.hots_target_scene_key) if h.hots_target_scene_key else None
        })
    return respuesta_js

# 2. Guardar un nuevo Hotspot
@app.post("/api/hotspots")
def create_hotspot(hotspot: HotspotCreate, db: Session = Depends(get_db)):
    nuevo_hotspot = HotspotDB(
        hots_scene_id=hotspot.prop_id,
        hots_pitch=hotspot.hots_pitch,
        hots_yaw=hotspot.hots_yaw,
        hots_type=hotspot.hots_type,
        hots_text=hotspot.hots_title,
        hots_target_scene_key=str(hotspot.target_prop_id) if hotspot.target_prop_id else None
    )
    db.add(nuevo_hotspot)
    db.commit()
    db.refresh(nuevo_hotspot)
    return {"status": "success", "message": "Hotspot guardado perfectamente", "id": nuevo_hotspot.hots_id}

# 3. Editar/Actualizar un Hotspot existente
@app.put("/api/hotspots/{hots_id}")
def update_hotspot(hots_id: int, hotspot: HotspotCreate, db: Session = Depends(get_db)):
    db_hotspot = db.query(HotspotDB).filter(HotspotDB.hots_id == hots_id).first()
    if not db_hotspot:
        raise HTTPException(status_code=404, detail="Hotspot no encontrado")
    
    db_hotspot.hots_scene_id = hotspot.prop_id
    db_hotspot.hots_pitch = hotspot.hots_pitch
    db_hotspot.hots_yaw = hotspot.hots_yaw
    db_hotspot.hots_type = hotspot.hots_type
    db_hotspot.hots_text = hotspot.hots_title
    db_hotspot.hots_target_scene_key = str(hotspot.target_prop_id) if hotspot.target_prop_id else None
    
    db.commit()
    db.refresh(db_hotspot)
    return {"status": "success", "message": "Hotspot actualizado perfectamente"}

# ----------------------------------------------------
# 6. RUTAS DE INTERFAZ GRÁFICA (Vistas HTML)
# ----------------------------------------------------

@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard():
    with open("dashboard.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/admin", response_class=HTMLResponse)
def admin_panel():
    with open("admin.html", "r", encoding="utf-8") as f:
        return f.read()
