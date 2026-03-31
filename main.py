from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
import os
import uvicorn
import socketio  # <--- IMPORT PARA WEBSOCKETS
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Dict, Any
from bson import ObjectId
# Cargar variables desde .env (solo para desarrollo local)
load_dotenv()

app = FastAPI(title="AEA Contest API - Production")

# ==========================================
# 1. CONFIGURACIÓN DE CORS (EL PUENTE)
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://preeminent-beijinho-fd3e37.netlify.app",
        "https://english-contest-vlyas7muk-maciasberner-1059s-projects.vercel.app", 
        "https://english-contest-gamma.vercel.app",
        "https://english-contest.vercel.app" # <--- ¡AQUÍ ESTÁ LA SOLUCIÓN! El dominio exacto de tu captura.
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1.5 CONFIGURACIÓN DE SOCKET.IO (EL ESPEJO)
# ==========================================
# Creamos el servidor asíncrono de Socket.io
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

@sio.on('connect')
async def connect(sid, environ):
    print(f"🔌 Dispositivo conectado a Socket.io: {sid}")

@sio.on('sync_state')
async def sync_state(sid, data):
    # Rebota la señal a todos los demás dispositivos (la pantalla pública)
    await sio.emit('sync_state', data, skip_sid=sid)

@sio.on('clear_state')
async def clear_state(sid):
    await sio.emit('clear_state', skip_sid=sid)

@sio.on('disconnect')
def disconnect(sid):
    print(f"❌ Dispositivo desconectado de Socket.io: {sid}")


# ==========================================
# 2. CONEXIÓN A MONGODB ATLAS
# ==========================================
# En Render, debes configurar MONGO_URL en la pestaña "Environment"
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://Berner:American2026Coca@american.91nzqdl.mongodb.net/contest_db")
client = AsyncIOMotorClient(MONGO_URL)
db = client.contest_db

# ==========================================
# 3. MODELOS DE DATOS (PYDANTIC)
# ==========================================
class LoginRequest(BaseModel):
    username: str
    password: str

# ==========================================
# 4. ENDPOINTS (RUTAS)
# ==========================================

@app.get("/")
async def root():
    return {"message": "AEA Backend Online - Production Mode"}

# ENDPOINT DE LOGIN (Sincronizado con tu colección 'usuarios')
@app.post("/api/login")
async def login(credenciales: LoginRequest):
    print(f"🔐 Intento de login: {credenciales.username}")
    
    # Buscamos al usuario en la colección 'usuarios'
    usuario = await db.usuarios.find_one({"username": credenciales.username})
    
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
        
    # Comprobación de contraseña en texto plano (según tu captura de Atlas)
    if credenciales.password != usuario.get("password"):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
        
    # Retornamos los datos que React necesita
    return {
        "username": usuario.get("username"),
        "rol": usuario.get("role")  # Nota: Usamos 'role' porque así está en tu BD
    }

# ENDPOINT DE PARTICIPANTES
@app.get("/participants/{category}")
async def get_participants(category: str):
    search_term = category.strip().upper()
    cursor = db.participants.find({"category": search_term}).sort("order_number", 1)
    participants = await cursor.to_list(length=200)
    
    for p in participants:
        p["_id"] = str(p["_id"])
        
    return participants

# ENDPOINT DE CATEGORÍAS
@app.get("/categories")
async def get_db_categories():
    categories = await db.participants.distinct("category")
    return categories

class ScoreUpdateRequest(BaseModel):
    round_number: str
    criteria_key: str
    score: int

@app.put("/api/participants/{participant_id}/score")
async def update_score(participant_id: str, data: ScoreUpdateRequest):
    try:
        # Construimos el campo a actualizar, ej: "scores.round_1.fase1"
        field_to_update = f"scores.{data.round_number}.{data.criteria_key}"
        
        resultado = await db.participants.update_one(
            {"_id": ObjectId(participant_id)},
            {"$set": {field_to_update: data.score}}
        )
        
        if resultado.modified_count == 1:
            return {"message": "Score saved successfully"}
        else:
            return {"message": "Score updated or participant not found"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    # ==========================================
# 4.5 ENDPOINTS DE PUNTUACIONES (COLECCIÓN 'scores')
# ==========================================
class ScoreUpdateRequest(BaseModel):
    participant_name: str
    category: str
    round_number: str
    criteria_key: str
    score: int

@app.put("/api/scores/{participant_id}")
async def update_score(participant_id: str, data: ScoreUpdateRequest):
    try:
        # Construimos el campo específico a actualizar (ej: scores.round_1.fase1)
        field_to_update = f"scores.{data.round_number}.{data.criteria_key}"
        
        # Guardamos en la NUEVA colección 'scores'
        # Usamos upsert=True para crearlo si es la primera vez que se califica a este alumno
        resultado = await db.scores.update_one(
            {"participant_id": participant_id},
            {
                "$set": {
                    field_to_update: data.score,
                    "participant_name": data.participant_name,
                    "category": data.category.strip().upper()
                }
            },
            upsert=True
        )
        
        return {"message": "Score saved successfully in scores collection"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/scores/{category}")
async def get_scores(category: str):
    search_term = category.strip().upper()
    cursor = db.scores.find({"category": search_term})
    scores = await cursor.to_list(length=200)
    
    for s in scores:
        s["_id"] = str(s["_id"])
        
    return scores
# ==========================================
# 5. INTEGRACIÓN FINAL Y ARRANQUE
# ==========================================
# Envolvemos la app de FastAPI con Socket.io para que usen el mismo puerto
app = socketio.ASGIApp(sio, other_asgi_app=app)

if __name__ == "__main__":
    # Render y Railway asignan el puerto automáticamente mediante la variable PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)