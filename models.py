from sqlalchemy import Column, Integer, String, Boolean, DateTime, DECIMAL, ForeignKey, TEXT, func
from sqlalchemy.orm import relationship
from database import Base

class TecnicoCampo(Base):
    __tablename__ = "tecnicos_campo"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hash_senha = Column(String, nullable=False)
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    
    # Define o relacionamento
    lotes_criados = relationship("LoteTora", back_populates="tecnico")

class LoteTora(Base):
    __tablename__ = "lotes_tora"
    id = Column(Integer, primary_key=True, index=True)
    id_lote_custom = Column(String, unique=True, index=True, nullable=False)
    id_tecnico_campo = Column(Integer, ForeignKey("tecnicos_campo.id"), nullable=False)
    data_hora_registro = Column(DateTime(timezone=True), server_default=func.now())
    coordenadas_gps_lat = Column(DECIMAL(10, 8), nullable=False)
    coordenadas_gps_lon = Column(DECIMAL(11, 8), nullable=False)
    numero_dof = Column(String, nullable=False)
    numero_licenca_ambiental = Column(String, nullable=False)
    especie_madeira_popular = Column(String)
    especie_madeira_cientifico = Column(String)
    volume_estimado_m3 = Column(DECIMAL(10, 2), nullable=False)
    fotos_evidencia = Column(TEXT) # No SQL, é TEXT[]

    # Define o relacionamento reverso
    tecnico = relationship("TecnicoCampo", back_populates="lotes_criados")