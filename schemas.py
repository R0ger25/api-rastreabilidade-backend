from pydantic import BaseModel, EmailStr
from typing import List, Optional, Literal
from decimal import Decimal
import datetime

# ===================================
# ESQUEMAS DE AUTENTICAÇÃO
# ===================================

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserDisplay(BaseModel):
    id: int
    email: EmailStr
    role: Literal["tecnico", "serraria", "fabrica"]
    
    class Config:
        from_attributes = True

# ===================================
# ESQUEMAS DO LOTE DE TORA
# ===================================

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
    coordenadas_gps_lat: Decimal
    coordenadas_gps_lon: Decimal
    numero_dof: str
    numero_licenca_ambiental: str
    especie_madeira_popular: Optional[str] = None
    especie_madeira_cientifico: Optional[str] = None
    volume_estimado_m3: Decimal
    fotos_evidencia: Optional[List[str]] = None
    
    class Config:
        from_attributes = True

# ===================================
# ESQUEMAS DO LOTE SERRADO (NOVO)
# ===================================

class LoteSerradaCreate(BaseModel):
    """Schema para criar um novo lote serrado"""
    id_lote_tora_origem: int
    data_recebimento_tora: datetime.datetime
    volume_saida_m3: Decimal
    tipo_produto: Optional[str] = None
    dimensoes: Optional[str] = None
    dados_tratamento: Optional[str] = None

class LoteSerradaDisplay(BaseModel):
    """Schema para exibir um lote serrado"""
    id: int
    id_lote_serrado_custom: str
    id_lote_tora_origem: int
    id_equipe_serraria: int
    data_recebimento_tora: datetime.datetime
    data_processamento: datetime.datetime
    volume_saida_m3: Decimal
    tipo_produto: Optional[str] = None
    dimensoes: Optional[str] = None
    dados_tratamento: Optional[str] = None
    
    class Config:
        from_attributes = True

# ===================================
# ESQUEMAS DO PRODUTO ACABADO (Para futuro)
# ===================================

class LoteProdutoAcabadoCreate(BaseModel):
    """Schema para criar um produto acabado"""
    id_lote_serrado_origem: int
    sku_produto: str
    nome_produto: str
    dados_acabamento: Optional[str] = None
    link_qr_code: str

class LoteProdutoAcabadoDisplay(BaseModel):
    """Schema para exibir um produto acabado"""
    id: int
    id_lote_produto_custom: str
    id_lote_serrado_origem: int
    id_equipe_fabrica: int
    sku_produto: str
    nome_produto: str
    data_fabricacao: datetime.datetime
    dados_acabamento: Optional[str] = None
    link_qr_code: str
    
    class Config:
        from_attributes = True