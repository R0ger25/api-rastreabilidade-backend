from pydantic import BaseModel, EmailStr
from typing import List, Optional, Literal
from decimal import Decimal
import datetime

# --- Esquemas de Autenticação (Corretos) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- Esquema de Usuário (CORRIGIDO) ---
# Renomeado para UserDisplay e simplificado para
# funcionar com todos os 3 tipos de usuário.
class UserDisplay(BaseModel):
    id: int
    email: EmailStr
    role: Literal["tecnico", "serraria", "fabrica"]
    # O 'role' dirá ao frontend qual tipo de usuário está logado
    
    class Config:
        from_attributes = True # Nome correto para Pydantic v2

# --- Esquemas do Lote de Tora (Opcional para Login) ---
# (Pode manter se você for adicionar o endpoint de criar lote depois)

class LoteToraCreate(BaseModel):
    coordenadas_gps_lat: Decimal
    coordenadas_gps_lon: Decimal
    numero_dof: str
    numero_licenca_ambiental: str
    especie_madeira_popular: Optional[str] = None
    especie_madeira_cientifico: Optional[str] = None
    volume_estimado_m3: Decimal
    fotos_evidencia: Optional[List[str]] = None

class LoteToraDisplay(BaseModel):
    id: int
    id_lote_custom: str
    id_tecnico_campo: int
    data_hora_registro: datetime.datetime
    
    class Config:
        from_attributes = True