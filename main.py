from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import Dict, Any
from bson import ObjectId
import os
import uvicorn
import socketio  # <--- IMPORT PARA WEBSOCKETS
from dotenv import load_dotenv

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
        "https://english-contest.vercel.app" # El dominio exacto de tu frontend
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

class ScoreUpdateRequest(BaseModel):
    participant_name: str
    category: str
    round_number: str
    criteria_key: str
    score: int
    judge_username: str  # <--- CLAVE: Identificador único del juez para no sobreescribir

# ==========================================
# 4. ENDPOINTS (RUTAS)
# ==========================================

@app.get("/")
async def root():
    return {"message": "AEA Backend Online - Production Mode"}

# ENDPOINT DE LOGIN
@app.post("/api/login")
async def login(credenciales: LoginRequest):
    print(f"🔐 Intento de login: {credenciales.username}")
    
    usuario = await db.usuarios.find_one({"username": credenciales.username})
    
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
        
    if credenciales.password != usuario.get("password"):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
        
    return {
        "username": usuario.get("username"),
        "rol": usuario.get("role") 
    }

# ENDPOINT DE PARTICIPANTES (Actualizado para soportar 'ALL')
@app.get("/participants/{category}")
async def get_participants(category: str):
    if category.upper() == "ALL":
        # Si la categoría es ALL, traemos a todos los participantes
        cursor = db.participants.find().sort("order_number", 1)
    else:
        search_term = category.strip().upper()
        cursor = db.participants.find({"category": search_term}).sort("order_number", 1)
        
    participants = await cursor.to_list(length=500)
    
    for p in participants:
        p["_id"] = str(p["_id"])
        
    return participants

# ENDPOINT DE CATEGORÍAS
@app.get("/categories")
async def get_db_categories():
    categories = await db.participants.distinct("category")
    return categories

# ==========================================
# 4.5 ENDPOINTS DE PUNTUACIONES (COLECCIÓN 'scores')
# ==========================================

@app.put("/api/scores/{participant_id}")
async def update_score(participant_id: str, data: ScoreUpdateRequest):
    try:
        # Construimos el campo específico a actualizar dividiéndolo por juez
        # Ejemplo: scores.judge1.round_1.fase1 = 3
        field_to_update = f"scores.{data.judge_username}.{data.round_number}.{data.criteria_key}"
        
        # Guardamos en la colección 'scores' usando upsert=True
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
        
        # Emitimos evento Socket.io para que el Leaderboard se actualice en tiempo real
        await sio.emit('score_updated')
        
        return {"message": "Score saved successfully without overwriting other judges"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ENDPOINT PARA OBTENER SCORES (Actualizado para soportar 'ALL')
@app.get("/api/scores/{category}")
async def get_scores(category: str):
    if category.upper() == "ALL":
        cursor = db.scores.find()
    else:
        search_term = category.strip().upper()
        cursor = db.scores.find({"category": search_term})
        
    scores = await cursor.to_list(length=500)
    
    for s in scores:
        s["_id"] = str(s["_id"])
        
    return scores

# NUEVO ENDPOINT: REINICIAR TODAS LAS VOTACIONES (AQUÍ ESTÁ CORRECTO)
@app.delete("/api/scores/{category}")
async def reset_scores(category: str, branch: str = "COCA"):
    try:
        search_term = category.strip().upper()
        
        # Si la categoría enviada es "ALL", vaciamos toda la colección (borra todos los puntajes)
        if search_term == "ALL":
            await db.scores.delete_many({}) 
            # NOTA: Si en el futuro separas por sedes, puedes usar: 
            # await db.scores.delete_many({"branch": branch})
        else:
            await db.scores.delete_many({"category": search_term})
            
        # Emitimos un evento de socket para que las pantallas de los jueces y el admin se actualicen al instante
        await sio.emit('score_updated')
        
        return {"message": "All scores have been reset to zero successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==========================================
# 5. INTEGRACIÓN FINAL Y ARRANQUE
# ==========================================
# Envolvemos la app de FastAPI con Socket.io para que usen el mismo puerto
app = socketio.ASGIApp(sio, other_asgi_app=app)

if __name__ == "__main__":
    # Render y Railway asignan el puerto automáticamente mediante la variable PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)