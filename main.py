from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import create_instance, create_engine, Column, Integer, Decimal, String, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# 1. Configuración de Base de Datos MySQL
# Cambia 'usuario', 'contraseña' y 'nombre_base_datos' por tus credenciales reales
DATABASE_URL = "mysql+pymysql://usuario:contraseña@localhost/tour_virtual_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Modelo SQLAlchemy para la tabla hotspots_tb
class HotspotDB(Base):
    __tablename__ = "hotspots_tb"
    
    hots_id = Column(Integer, primary_key=True, index=True)
    hots_scene_id = Column(Integer, nullable=False)
    hots_pitch = Column(Decimal(5, 2), nullable=False)
    hots_yaw = Column(Decimal(5, 2), nullable=False)
    hots_type = Column(Enum('scene', 'info'), nullable=False)
    hots_text = Column(String(255), nullable=False)
    hots_target_scene_key = Column(String(50), nullable=True)

# 3. Esquema de validación Pydantic para recibir datos desde el Front
class HotspotCreate(BaseModel):
    hots_scene_id: int
    hots_pitch: float
    hots_yaw: float
    hots_type: str
    hots_text: str
    hots_target_scene_key: str = None

# Dependencia para obtener la sesión de BD en cada petición
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. Inicializar FastAPI
app = FastAPI(title="Administrador de Recorridos 360")

# Habilitar CORS para que el Front pueda comunicarse sin bloqueos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint API: Guardar nuevo Hotspot
@app.post("/api/hotspots")
def create_hotspot(hotspot: HotspotCreate, db: Session = Depends(get_db)):
    nuevo_hotspot = HotspotDB(
        hots_scene_id=hotspot.hots_scene_id,
        hots_pitch=hotspot.hots_pitch,
        hots_yaw=hotspot.hots_yaw,
        hots_type=hotspot.hots_type,
        hots_text=hotspot.hots_text,
        hots_target_scene_key=hotspot.hots_target_scene_key
    )
    db.add(nuevo_hotspot)
    db.commit()
    db.refresh(nuevo_hotspot)
    return {"status": "success", "message": "Hotspot guardado perfectamente", "id": nuevo_hotspot.hots_id}

# Endpoint para servir la interfaz del Administrador (Herramienta de captura)
@app.get("/admin", response_class=HTMLResponse)
def admin_panel():
    with open("admin.html", "r", encoding="utf-8") as f:
        return f.read()
