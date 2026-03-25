from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class Participant(BaseModel):
    id: Optional[str] = Field(alias="_id")
    order_number: int      # <--- El número exacto de tu CSV
    name: str
    category: str          # Ej: "POWER UP 1", "LITTLE STEPS"
    status: str = "waiting" # waiting, active, finished, absent
    total_score: int = 0
# 2. Modelo del Vocabulario/Imágenes
class VocabularyItem(BaseModel):
    id: Optional[str] = Field(alias="_id")
    category: str
    round_number: int
    item_type: str # "image", "word", "scrambled", "sentence"
    content: str # La palabra en sí, o la URL/nombre de la imagen
    is_used: bool = False
    assigned_participant_id: Optional[str] = None # Para auditoría, saber a quién le tocó

# 3. Modelo del Estado del Juego en vivo
class GameSession(BaseModel):
    category_active: str
    current_round: int
    active_participant_id: Optional[str]
    current_items: List[VocabularyItem] = [] # Las 3 palabras/imágenes de su turno
    timer_seconds: int