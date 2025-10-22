from pydantic import BaseModel, EmailStr
from typing import List, Optional
from decimal import Decimal
import datetime

# --- Esquemas de Autenticação ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- Esquemas do Técnico de Campo ---
class TecnicoDisplay(BaseModel):
    id: int
    nome: str
    email: EmailStr
    
    class Config:
        from_attributes = True

# --- Esquemas do Lote de Tora ---
class LoteToraCreate(BaseModel):
    # O que o técnico envia pelo formulário
    coordenadas_gps_lat: Decimal
    coordenadas_gps_lon: Decimal
    numero_dof: str
    numero_licenca_ambiental: str
    especie_madeira_popular: Optional[str] = None
    especie_madeira_cientifico: Optional[str] = None
    volume_estimado_m3: Decimal
    fotos_evidencia: Optional[List[str]] = None

class LoteToraDisplay(BaseModel):
    # O que a API retorna após o sucesso
    id: int
    id_lote_custom: str
    id_tecnico_campo: int
    data_hora_registro: datetime.datetime
    
    class Config:
        from_attributes = True