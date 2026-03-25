from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
import os
import uvicorn
from dotenv import load_dotenv

# Cargar variables desde .env (solo para desarrollo local)
load_dotenv()

app = FastAPI(title="AEA Contest API - Production")

# ==========================================
# 1. CONFIGURACIÓN DE CORS (EL PUENTE)
# ==========================================
# IMPORTANTE: Reemplaza la URL de Netlify con tu URL REAL una vez que la tengas
# En tu main.py de Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://preeminent-beijinho-fd3e37.netlify.app" # <--- ESTA ES TU URL REAL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# ==========================================
# 5. ARRANQUE DEL SERVIDOR (PUERTO DINÁMICO)
# ==========================================
if __name__ == "__main__":
    # Render y Railway asignan el puerto automáticamente mediante la variable PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)