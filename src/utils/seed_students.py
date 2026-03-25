import pandas as pd
import asyncio
import os
from collections import Counter
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://Berner:American2026Coca@american.91nzqdl.mongodb.net/mongodb.net/contest_db")
client = AsyncIOMotorClient(MONGO_URL)
db = client.contest_db

async def seed_students(file_path):
    participants_to_insert = []
    
    try:
        # La magia está aquí: pd.read_excel lee archivos .xlsx sin importar cómo se llamen.
        # engine='openpyxl' asegura que decodifique ese formato binario "PK" correctamente.
        df = pd.read_excel(file_path, engine='openpyxl')
        
        for index, row in df.iterrows():
            if len(row) >= 3:
                col_numero = str(row.iloc[0]).strip()
                col_nombre = str(row.iloc[1]).strip()
                col_categoria = str(row.iloc[2]).strip()
                
                # A veces Pandas lee los números de Excel como "1.0", esto lo limpia a "1"
                if col_numero.endswith('.0'):
                    col_numero = col_numero[:-2]
                
                if col_numero.isdigit() and col_nombre != "nan":
                    participants_to_insert.append({
                        "order_number": int(col_numero),
                        "name": col_nombre,
                        "category": col_categoria.upper(),
                        "status": "waiting",
                        "total_score": 0
                    })
        
        await db.participants.delete_many({})
        
        if participants_to_insert:
            await db.participants.insert_many(participants_to_insert)
            print(f"✅ ¡Éxito! Se insertaron {len(participants_to_insert)} estudiantes en MongoDB Atlas.\n")
            
            categorias = [p['category'] for p in participants_to_insert]
            conteo = Counter(categorias)
            print("📊 RESUMEN POR CATEGORÍA:")
            for cat, cant in conteo.items():
                print(f" - {cat}: {cant} estudiantes")
        else:
            print("⚠️ El archivo se leyó como Excel, pero no se encontraron números válidos.")
            
    except Exception as e:
        print(f"❌ Error al leer el Excel: {e}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__)) 
    nombre_archivo = "LISTADO DE ESTUDIANTES NUMERO.xlsx"
    ruta_archivo = os.path.join(current_dir, nombre_archivo)
    
    print(f"Leyendo como Excel el archivo: {ruta_archivo}")
    asyncio.run(seed_students(ruta_archivo))