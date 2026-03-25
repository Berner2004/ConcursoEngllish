import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://Berner:American2026Coca@american.91nzqdl.mongodb.net/mongodb.net/contest_db")
client = AsyncIOMotorClient(MONGO_URL)
db = client.contest_db

async def seed_base_data():
    # 1. Colección de Categorías (Extraídas de tus PDFs)
    categorias = [
        {"nombre": "POWER UP 1", "edad": "6-7 años", "nivel": "Básico inicial", "rondas": 3, "modalidad": "Competitiva"},
        {"nombre": "POWER UP 3", "edad": "Variada", "nivel": "Básico alto", "rondas": 3, "modalidad": "Competitiva"},
        {"nombre": "AMERICAN THINK STARTERS", "edad": "Teenagers", "nivel": "A1", "rondas": 4, "modalidad": "Competitiva"},
        {"nombre": "LITTLE STEPS", "edad": "4-5 años", "nivel": "Inicial", "rondas": 3, "modalidad": "Participativa"},
        {"nombre": "KID'S BOX 1", "edad": "6-7 años", "nivel": "Básico", "rondas": 3, "modalidad": "Participativa"}
    ]

    # 2. Colección de Usuarios (Admin y Jueces)
    usuarios = [
        {"username": "admin_principal", "role": "admin", "nombre_real": "Administrador General"},
        {"username": "juez_1", "role": "juez", "nombre_real": "Juez Calificador 1"},
        {"username": "juez_2", "role": "juez", "nombre_real": "Juez Calificador 2"}
    ]

    # Limpiar colecciones previas para evitar duplicados
    await db.categorias.delete_many({})
    await db.usuarios.delete_many({})

    # Insertar datos
    await db.categorias.insert_many(categorias)
    await db.usuarios.insert_many(usuarios)

    print("✅ Categorías y Usuarios (Jueces/Admin) cargados exitosamente en MongoDB.")

if __name__ == "__main__":
    asyncio.run(seed_base_data())