from sqlalchemy import Column, Integer, String, Boolean, DateTime, DECIMAL, ForeignKey, TEXT, func
from sqlalchemy.orm import relationship
from database import Base # Importa o 'Base' do nosso database.py

# --- MODELOS DE USUÁRIOS ---

class TecnicoCampo(Base):
    __tablename__ = "tecnicos_campo"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hash_senha = Column(String, nullable=False)
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamento: Um técnico cria muitos lotes de tora
    lotes_criados = relationship("LoteTora", back_populates="tecnico")

class EquipeSerraria(Base):
    __tablename__ = "equipe_serraria"
    id = Column(Integer, primary_key=True, index=True)
    nome_responsavel = Column(String, nullable=False)
    nome_serraria = Column(String)
    email = Column(String, unique=True, index=True, nullable=False)
    hash_senha = Column(String, nullable=False)
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamento: Uma equipe processa muitos lotes serrados
    lotes_processados = relationship("LoteSerrado", back_populates="equipe_serraria")

class EquipeFabrica(Base):
    __tablename__ = "equipe_fabrica"
    id = Column(Integer, primary_key=True, index=True)
    nome_responsavel = Column(String, nullable=False)
    nome_fabrica = Column(String)
    email = Column(String, unique=True, index=True, nullable=False)
    hash_senha = Column(String, nullable=False)
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamento: Uma equipe fabrica muitos produtos acabados
    produtos_fabricados = relationship("LoteProdutoAcabado", back_populates="equipe_fabrica")


# --- MODELOS DE LOTES (PRODUTOS) ---

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

    # Relacionamentos
    tecnico = relationship("TecnicoCampo", back_populates="lotes_criados")
    lotes_serrados_gerados = relationship("LoteSerrado", back_populates="lote_tora_origem")

class LoteSerrado(Base):
    __tablename__ = "lotes_serrada"
    id = Column(Integer, primary_key=True, index=True)
    id_lote_serrado_custom = Column(String, unique=True, index=True, nullable=False)
    id_lote_tora_origem = Column(Integer, ForeignKey("lotes_tora.id"), nullable=False)
    id_equipe_serraria = Column(Integer, ForeignKey("equipe_serraria.id"), nullable=False)
    data_recebimento_tora = Column(DateTime(timezone=True), nullable=False)
    data_processamento = Column(DateTime(timezone=True), server_default=func.now())
    volume_saida_m3 = Column(DECIMAL(10, 2), nullable=False)
    tipo_produto = Column(String)
    dimensoes = Column(String)
    dados_tratamento = Column(TEXT)

    # Relacionamentos
    lote_tora_origem = relationship("LoteTora", back_populates="lotes_serrados_gerados")
    equipe_serraria = relationship("EquipeSerraria", back_populates="lotes_processados")
    produtos_acabados_gerados = relationship("LoteProdutoAcabado", back_populates="lote_serrado_origem")

class LoteProdutoAcabado(Base):
    __tablename__ = "lotes_produto_acabado"
    id = Column(Integer, primary_key=True, index=True)
    id_lote_produto_custom = Column(String, unique=True, index=True, nullable=False)
    id_lote_serrado_origem = Column(Integer, ForeignKey("lotes_serrada.id"), nullable=False)
    id_equipe_fabrica = Column(Integer, ForeignKey("equipe_fabrica.id"), nullable=False)
    sku_produto = Column(String, nullable=False)
    nome_produto = Column(String, nullable=False)
    data_fabricacao = Column(DateTime(timezone=True), server_default=func.now())
    dados_acabamento = Column(TEXT)
    link_qr_code = Column(TEXT, nullable=False)

    # Relacionamentos
    lote_serrado_origem = relationship("LoteSerrado", back_populates="produtos_acabados_gerados")
    equipe_fabrica = relationship("EquipeFabrica", back_populates="produtos_fabricados")