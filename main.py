import os
import datetime
from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from jose import jwt, JWTError

# Importa de todos os nossos outros arquivos
from database import get_db
import models
import schemas
import auth
from auth import SECRET_KEY, ALGORITHM

# Importa módulo blockchain
try:
    import blockchain
    BLOCKCHAIN_ENABLED = True
    print("✅ Módulo blockchain carregado com sucesso!")
except Exception as e:
    BLOCKCHAIN_ENABLED = False
    print(f"⚠️ Blockchain desabilitada: {e}")

# Importa o CORS
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="API Rastreabilidade com Blockchain",
    description="Sistema completo de rastreamento desde a extração até o produto final",
    version="3.0.0"
)

# --- Configuração do CORS ---
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5500",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5500",
    "https://app-rastreabilidade.onrender.com",
    "*"  # Permite todos (remover em produção)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos durante desenvolvimento
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependências de Segurança ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Função genérica: Decodifica o token e retorna o objeto do usuário
    de QUALQUER tabela (Técnico, Serraria ou Fábrica).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    # Procura o usuário em todas as 3 tabelas
    user = db.query(models.TecnicoCampo).filter(models.TecnicoCampo.email == token_data.email).first()
    if user:
        return user
    user = db.query(models.EquipeSerraria).filter(models.EquipeSerraria.email == token_data.email).first()
    if user:
        return user
    user = db.query(models.EquipeFabrica).filter(models.EquipeFabrica.email == token_data.email).first()
    if user:
        return user
    
    raise credentials_exception

# ===================================
# ENDPOINTS - AUTENTICAÇÃO
# ===================================

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(
    username: str = Form(...),  # OAuth2 usa 'username', mas vamos aceitar email
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint de login que autentica usuários de qualquer tipo (técnico, serraria, fábrica).
    Retorna um token JWT válido.
    """
    user = None
    
    # 1. Tenta como Técnico
    user_tecnico = db.query(models.TecnicoCampo).filter(models.TecnicoCampo.email == username).first()
    if user_tecnico and auth.verificar_senha(password, user_tecnico.hash_senha):
        user = user_tecnico

    # 2. Tenta como Serraria
    if not user:
        user_serraria = db.query(models.EquipeSerraria).filter(models.EquipeSerraria.email == username).first()
        if user_serraria and auth.verificar_senha(password, user_serraria.hash_senha):
            user = user_serraria
            
    # 3. Tenta como Fábrica
    if not user:
        user_fabrica = db.query(models.EquipeFabrica).filter(models.EquipeFabrica.email == username).first()
        if user_fabrica and auth.verificar_senha(password, user_fabrica.hash_senha):
            user = user_fabrica

    # 4. Se não encontrou em nenhuma
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 5. Se encontrou, cria o token
    access_token = auth.criar_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=schemas.UserDisplay)
def read_users_me(current_user = Depends(get_current_user)):
    """
    Retorna id, email e ROLE do usuário logado.
    """
    role = "desconhecido"
    
    if isinstance(current_user, models.TecnicoCampo):
        role = "tecnico"
    elif isinstance(current_user, models.EquipeSerraria):
        role = "serraria"
    elif isinstance(current_user, models.EquipeFabrica):
        role = "fabrica"
    
    return {"id": current_user.id, "email": current_user.email, "role": role}

# ===================================
# DEPENDÊNCIAS - VERIFICAÇÃO DE ROLE
# ===================================

def get_current_tecnico(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.TecnicoCampo:
    credentials_exception = HTTPException(
        status_code=401, 
        detail="Não autorizado: Apenas Técnicos de Campo podem acessar esta rota."
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.TecnicoCampo).filter(models.TecnicoCampo.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_serraria(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.EquipeSerraria:
    credentials_exception = HTTPException(
        status_code=401, 
        detail="Não autorizado: Apenas a Equipe da Serraria pode acessar esta rota."
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.EquipeSerraria).filter(models.EquipeSerraria.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_fabrica(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.EquipeFabrica:
    credentials_exception = HTTPException(
        status_code=401, 
        detail="Não autorizado: Apenas a Equipe da Fábrica pode acessar esta rota."
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.EquipeFabrica).filter(models.EquipeFabrica.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# ===================================
# ENDPOINTS - TÉCNICO (LOTES DE TORA)
# ===================================

@app.post("/lotes_tora/", response_model=schemas.LoteToraDisplay, status_code=status.HTTP_201_CREATED)
def create_lote_tora(
    lote: schemas.LoteToraCreate, 
    db: Session = Depends(get_db), 
    current_user: models.TecnicoCampo = Depends(get_current_tecnico)
):
    """
    Cria um novo Lote de Tora. Requer login de Técnico de Campo.
    REGISTRA NA BLOCKCHAIN automaticamente.
    """
    today_str = datetime.date.today().strftime("%Y%m%d")
    count_today = db.query(models.LoteTora).filter(
        models.LoteTora.id_lote_custom.like(f"TORA-{today_str}-%")
    ).count()
    new_id_custom = f"TORA-{today_str}-{str(count_today + 1).zfill(3)}"

    db_lote = models.LoteTora(
        **lote.model_dump(),
        id_lote_custom=new_id_custom,
        id_tecnico_campo=current_user.id
    )
    
    try:
        # 1. Salvar no banco de dados centralizado
        db.add(db_lote)
        db.commit()
        db.refresh(db_lote)
        
        print(f"✅ Lote {new_id_custom} salvo no banco de dados")
        
        # 2. Registrar na blockchain
        if BLOCKCHAIN_ENABLED:
            try:
                tx_hash = blockchain.registrar_lote_tora_blockchain(
                    id_lote_custom=db_lote.id_lote_custom,
                    coordenadas_lat=float(lote.coordenadas_gps_lat),
                    coordenadas_lon=float(lote.coordenadas_gps_lon),
                    numero_dof=lote.numero_dof,
                    numero_licenca=lote.numero_licenca_ambiental,
                    especie=lote.especie_madeira_popular or "Não informada",
                    volume_m3=float(lote.volume_estimado_m3)
                )
                
                if tx_hash:
                    print(f"✅ Lote {new_id_custom} registrado na blockchain: {tx_hash}")
                else:
                    print(f"⚠️ Lote {new_id_custom} salvo no BD, mas falhou na blockchain")
                    
            except Exception as blockchain_error:
                print(f"⚠️ Erro ao registrar na blockchain: {blockchain_error}")
                # Não falha o endpoint se blockchain der erro
        
        return db_lote
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao salvar no banco: {e}")


@app.get("/lotes_tora/", response_model=List[schemas.LoteToraDisplay])
def listar_lotes_tora(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Lista todos os lotes de tora.
    Técnicos veem apenas os seus. Serraria e Fábrica veem todos.
    """
    if isinstance(current_user, models.TecnicoCampo):
        lotes = db.query(models.LoteTora).filter(
            models.LoteTora.id_tecnico_campo == current_user.id
        ).all()
    else:
        lotes = db.query(models.LoteTora).all()
    
    return lotes


@app.get("/lotes_tora/{lote_id}", response_model=schemas.LoteToraDisplay)
def obter_lote_tora(
    lote_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Obtém detalhes de um lote de tora específico.
    """
    lote = db.query(models.LoteTora).filter(models.LoteTora.id == lote_id).first()
    
    if not lote:
        raise HTTPException(status_code=404, detail="Lote de tora não encontrado")
    
    if isinstance(current_user, models.TecnicoCampo) and lote.id_tecnico_campo != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado a este lote")
    
    return lote

# ===================================
# ENDPOINTS - SERRARIA (LOTES SERRADOS)
# ===================================

@app.post("/lotes_serrada/", response_model=schemas.LoteSerradaDisplay, status_code=status.HTTP_201_CREATED)
def create_lote_serrado(
    lote: schemas.LoteSerradaCreate,
    db: Session = Depends(get_db),
    current_user: models.EquipeSerraria = Depends(get_current_serraria)
):
    """
    Cria um novo lote serrado a partir de um lote de tora.
    REGISTRA NA BLOCKCHAIN automaticamente.
    """
    # 1. Verificar se o lote de tora existe
    lote_tora = db.query(models.LoteTora).filter(
        models.LoteTora.id == lote.id_lote_tora_origem
    ).first()
    
    if not lote_tora:
        raise HTTPException(
            status_code=404,
            detail=f"Lote de tora com ID {lote.id_lote_tora_origem} não encontrado"
        )
    
    # 2. Calcular volume já processado
    lotes_ja_processados = db.query(models.LoteSerrado).filter(
        models.LoteSerrado.id_lote_tora_origem == lote.id_lote_tora_origem
    ).all()
    
    volume_processado = sum(float(ls.volume_saida_m3) for ls in lotes_ja_processados)
    volume_disponivel = float(lote_tora.volume_estimado_m3) - volume_processado
    
    # 3. Validar volume
    if float(lote.volume_saida_m3) > volume_disponivel:
        raise HTTPException(
            status_code=400,
            detail=f"Volume de saída ({lote.volume_saida_m3} m³) excede o volume disponível ({volume_disponivel:.2f} m³)"
        )
    
    # 4. Gerar ID customizado
    hoje = datetime.date.today().strftime("%Y%m%d")
    ultimo_lote = db.query(models.LoteSerrado).filter(
        models.LoteSerrado.id_lote_serrado_custom.like(f"SERR-{hoje}-%")
    ).order_by(models.LoteSerrado.id.desc()).first()
    
    if ultimo_lote:
        ultimo_numero = int(ultimo_lote.id_lote_serrado_custom.split("-")[-1])
        novo_numero = ultimo_numero + 1
    else:
        novo_numero = 1
    
    id_lote_serrado_custom = f"SERR-{hoje}-{novo_numero:03d}"
    
    # 5. Criar o lote serrado
    db_lote_serrado = models.LoteSerrado(
        **lote.model_dump(),
        id_lote_serrado_custom=id_lote_serrado_custom,
        id_equipe_serraria=current_user.id
    )
    
    try:
        # Salvar no banco
        db.add(db_lote_serrado)
        db.commit()
        db.refresh(db_lote_serrado)
        
        print(f"✅ Lote serrado {id_lote_serrado_custom} salvo no banco de dados")
        
        # Registrar na blockchain
        if BLOCKCHAIN_ENABLED:
            try:
                tx_hash = blockchain.registrar_lote_serrado_blockchain(
                    id_lote_serrado_custom=db_lote_serrado.id_lote_serrado_custom,
                    id_lote_tora_origem=lote_tora.id_lote_custom,
                    volume_saida_m3=float(lote.volume_saida_m3),
                    tipo_produto=lote.tipo_produto or "",
                    dimensoes=lote.dimensoes or ""
                )
                
                if tx_hash:
                    print(f"✅ Lote serrado registrado na blockchain: {tx_hash}")
                else:
                    print(f"⚠️ Lote serrado salvo no BD, mas falhou na blockchain")
                    
            except Exception as blockchain_error:
                print(f"⚠️ Erro blockchain: {blockchain_error}")
        
        return db_lote_serrado
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao salvar lote serrado: {e}")


@app.get("/lotes_serrada/", response_model=List[schemas.LoteSerradaDisplay])
def listar_lotes_serrados(
    db: Session = Depends(get_db),
    current_user: models.EquipeSerraria = Depends(get_current_serraria)
):
    """
    Lista todos os lotes serrados processados pelo usuário atual.
    """
    lotes = db.query(models.LoteSerrado).filter(
        models.LoteSerrado.id_equipe_serraria == current_user.id
    ).order_by(models.LoteSerrado.data_processamento.desc()).all()
    
    return lotes


@app.get("/lotes_serrado/", response_model=List[schemas.LoteSerradaDisplay])
def listar_lotes_serrados_para_fabrica(
    db: Session = Depends(get_db),
    current_user: models.EquipeFabrica = Depends(get_current_fabrica)
):
    """
    Lista todos os lotes serrados disponíveis para fabricação.
    """
    lotes = db.query(models.LoteSerrado).order_by(
        models.LoteSerrado.data_processamento.desc()
    ).all()
    
    return lotes

# ===================================
# ENDPOINTS - FÁBRICA (PRODUTOS ACABADOS)
# ===================================

@app.post("/produtos_acabados/", response_model=schemas.LoteProdutoAcabadoDisplay, status_code=status.HTTP_201_CREATED)
def create_produto_acabado(
    produto: schemas.LoteProdutoAcabadoCreate,
    db: Session = Depends(get_db),
    current_user: models.EquipeFabrica = Depends(get_current_fabrica)
):
    """
    Cria um novo produto acabado a partir de um lote serrado.
    REGISTRA NA BLOCKCHAIN automaticamente.
    """
    # 1. Verificar se o lote serrado existe
    lote_serrado = db.query(models.LoteSerrado).filter(
        models.LoteSerrado.id == produto.id_lote_serrado_origem
    ).first()
    
    if not lote_serrado:
        raise HTTPException(
            status_code=404,
            detail=f"Lote serrado com ID {produto.id_lote_serrado_origem} não encontrado"
        )
    
    # 2. Gerar ID customizado
    hoje = datetime.date.today().strftime("%Y%m%d")
    ultimo_produto = db.query(models.LoteProdutoAcabado).filter(
        models.LoteProdutoAcabado.id_lote_produto_custom.like(f"PROD-{hoje}-%")
    ).order_by(models.LoteProdutoAcabado.id.desc()).first()
    
    if ultimo_produto:
        ultimo_numero = int(ultimo_produto.id_lote_produto_custom.split("-")[-1])
        novo_numero = ultimo_numero + 1
    else:
        novo_numero = 1
    
    id_lote_produto_custom = f"PROD-{hoje}-{novo_numero:03d}"
    
    # 3. Gerar link de rastreabilidade
    link_qr_code = f"https://app-rastreabilidade.onrender.com/rastrear.html?id={id_lote_produto_custom}"
    
    # 4. Criar o produto
    db_produto = models.LoteProdutoAcabado(
        **produto.model_dump(exclude={'link_qr_code'}),
        id_lote_produto_custom=id_lote_produto_custom,
        id_equipe_fabrica=current_user.id,
        link_qr_code=link_qr_code
    )
    
    try:
        # Salvar no banco
        db.add(db_produto)
        db.commit()
        db.refresh(db_produto)
        
        print(f"✅ Produto {id_lote_produto_custom} salvo no banco de dados")
        
        # Registrar na blockchain
        if BLOCKCHAIN_ENABLED:
            try:
                tx_hash = blockchain.registrar_produto_acabado_blockchain(
                    id_produto_custom=db_produto.id_lote_produto_custom,
                    id_lote_serrado_origem=lote_serrado.id_lote_serrado_custom,
                    sku_produto=produto.sku_produto,
                    nome_produto=produto.nome_produto
                )
                
                if tx_hash:
                    print(f"✅ Produto registrado na blockchain: {tx_hash}")
                    print(f"🔗 Etherscan: https://sepolia.etherscan.io/tx/{tx_hash}")
                else:
                    print(f"⚠️ Produto salvo no BD, mas falhou na blockchain")
                    
            except Exception as blockchain_error:
                print(f"⚠️ Erro blockchain: {blockchain_error}")
        
        return db_produto
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao salvar produto acabado: {e}")


@app.get("/produtos_acabados/", response_model=List[schemas.LoteProdutoAcabadoDisplay])
def listar_produtos_acabados(
    db: Session = Depends(get_db),
    current_user: models.EquipeFabrica = Depends(get_current_fabrica)
):
    """
    Lista todos os produtos acabados fabricados pelo usuário atual.
    """
    produtos = db.query(models.LoteProdutoAcabado).filter(
        models.LoteProdutoAcabado.id_equipe_fabrica == current_user.id
    ).order_by(models.LoteProdutoAcabado.data_fabricacao.desc()).all()
    
    return produtos

# ===================================
# ENDPOINT PÚBLICO - RASTREABILIDADE
# ===================================

@app.get("/rastrear/{id_produto_custom}")
def rastrear_produto(id_produto_custom: str, db: Session = Depends(get_db)):
    """
    Endpoint PÚBLICO para rastrear um produto.
    Retorna toda a cadeia: Produto → Serrado → Tora.
    """
    # Buscar produto
    produto = db.query(models.LoteProdutoAcabado).filter(
        models.LoteProdutoAcabado.id_lote_produto_custom == id_produto_custom
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # Buscar lote serrado
    lote_serrado = db.query(models.LoteSerrado).filter(
        models.LoteSerrado.id == produto.id_lote_serrado_origem
    ).first()
    
    # Buscar lote de tora
    lote_tora = None
    if lote_serrado:
        lote_tora = db.query(models.LoteTora).filter(
            models.LoteTora.id == lote_serrado.id_lote_tora_origem
        ).first()
    
    return {
        "produto": {
            "id": produto.id,
            "id_custom": produto.id_lote_produto_custom,
            "nome": produto.nome_produto,
            "sku": produto.sku_produto,
            "data_fabricacao": produto.data_fabricacao.isoformat(),
            "dados_acabamento": produto.dados_acabamento
        },
        "lote_serrado": {
            "id": lote_serrado.id,
            "id_custom": lote_serrado.id_lote_serrado_custom,
            "tipo_produto": lote_serrado.tipo_produto,
            "dimensoes": lote_serrado.dimensoes,
            "volume_m3": float(lote_serrado.volume_saida_m3),
            "data_processamento": lote_serrado.data_processamento.isoformat()
        } if lote_serrado else None,
        "lote_tora": {
            "id": lote_tora.id,
            "id_custom": lote_tora.id_lote_custom,
            "especie_popular": lote_tora.especie_madeira_popular,
            "especie_cientifica": lote_tora.especie_madeira_cientifico,
            "volume_m3": float(lote_tora.volume_estimado_m3),
            "numero_dof": lote_tora.numero_dof,
            "numero_licenca": lote_tora.numero_licenca_ambiental,
            "coordenadas": {
                "lat": float(lote_tora.coordenadas_gps_lat),
                "lon": float(lote_tora.coordenadas_gps_lon)
            },
            "data_registro": lote_tora.data_hora_registro.isoformat()
        } if lote_tora else None
    }


# ===================================
# ENDPOINT - HEALTH CHECK
# ===================================

@app.get("/health")
def health_check():
    """
    Verifica se a API está funcionando.
    """
    return {
        "status": "healthy",
        "version": "3.0.0",
        "blockchain_enabled": BLOCKCHAIN_ENABLED
    }


@app.get("/")
def root():
    """
    Endpoint raiz.
    """
    return {
        "message": "API de Rastreabilidade de Madeira com Blockchain",
        "version": "3.0.0",
        "blockchain": "enabled" if BLOCKCHAIN_ENABLED else "disabled",
        "docs": "/docs"
    }