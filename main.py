from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import create_instance, create_engine, Column, Integer, Decimal, String, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SERVER_SOURCE = '' 

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
    db_host = "localhost" 

DATABASE_URL = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}"

# 4. Creamos el "equivalente" a tu objeto $connectMySql de mysqli
engine = create_engine(
    DATABASE_URL,
    pool_recycle=3600, # Evita el error "MySQL server has gone away" en la VM
    pool_pre_ping=True # Verifica que la conexión siga viva antes de usarla
)

# Creamos la fábrica de sesiones para que FastAPI interactúe con la BD
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
