# En backend/src/controllers/game_controller.py

async def get_next_participant(category: str):
    # Busca al estudiante de la categoría que siga esperando, ordenado por su número
    next_student = await db.participants.find_one(
        {"category": category, "status": "waiting"},
        sort=[("order_number", 1)] # 1 significa orden ascendente (1, 2, 3...)
    )
    
    if not next_student:
        return {"message": "Ya no hay más estudiantes en esta categoría."}
        
    return next_student