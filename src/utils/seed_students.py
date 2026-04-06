import pandas as pd
from pymongo import MongoClient

# 1. Configuración de MongoDB
MONGO_URL = "mongodb+srv://Berner:American2026Coca@american.91nzqdl.mongodb.net/contest_db"

# 2. Nombre exacto de tu archivo EXCEL
FILE_PATH = "LISTADO DE ESTUDIANTES NUMERO ACT 2042026.xlsx"

def clean_and_update_db_from_excel():
    print("🔌 Conectando a MongoDB Atlas...")
    client = MongoClient(MONGO_URL)
    db = client.contest_db
    collection = db.participants

    print(f"📂 Leyendo el archivo de Excel: {FILE_PATH}\n")
    
    count_new = 0
    count_updated = 0

    try:
        # Usamos pandas para leer el archivo Excel (.xlsx) de manera nativa
        # fillna("") convierte las celdas vacías en texto vacío en lugar de "NaN"
        df = pd.read_excel(FILE_PATH).fillna("")

        # Buscamos los nombres de las columnas (por si tienen espacios al inicio/final)
        columnas = df.columns.tolist()
        col_num = next((c for c in columnas if "N°" in str(c).upper()), None)
        col_name = next((c for c in columnas if "STUDENT" in str(c).upper()), None)
        col_cat = next((c for c in columnas if "CATEGORÍA" in str(c).upper() or "CATEGORIA" in str(c).upper()), None)

        if not col_num or not col_name or not col_cat:
            print("❌ Error: No se encontraron las columnas correctas en el Excel.")
            print(f"Columnas detectadas en tu archivo: {columnas}")
            return

        for index, row in df.iterrows():
            # Limpieza de datos
            raw_name = str(row[col_name]).strip()
            if not raw_name:
                continue # Saltamos filas vacías

            clean_name = raw_name.upper()
            clean_category = str(row[col_cat]).strip().upper()

            # Arreglar la categoría de Kid's Box para que coincida con tu frontend
            if clean_category in ["KID´S BOX", "KID'S BOX", "KIDS BOX"]:
                clean_category = "KIDS BOX"
                
            # Extraer número de orden correctamente (a veces pandas lee los números como 1.0)
            try:
                order_num = int(float(str(row[col_num]).strip()))
            except ValueError:
                order_num = 0

            # 4. Construir el documento
            participant_doc = {
                "name": clean_name,
                "category": clean_category,
                "order_number": order_num,
                "status": "waiting"  # Listo para el concurso
            }

            # 5. Insertar o Actualizar en Mongo (Evitar duplicados)
            query = {"name": clean_name, "category": clean_category}
            update = {"$set": participant_doc}
            
            result = collection.update_one(query, update, upsert=True)
            
            if result.upserted_id:
                print(f"✅ NUEVO: #{order_num} | {clean_name} | {clean_category}")
                count_new += 1
            else:
                print(f"🔄 ACTUALIZADO: #{order_num} | {clean_name} | {clean_category}")
                count_updated += 1

        print(f"\n🚀 ¡Proceso completado con éxito!")
        print(f"📊 Resumen: {count_new} estudiantes creados, {count_updated} estudiantes actualizados.")

    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo '{FILE_PATH}'. Asegúrate de que el nombre sea exacto y esté en la misma carpeta.")
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    clean_and_update_db_from_excel()