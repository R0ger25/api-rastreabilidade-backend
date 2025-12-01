import os
import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from jose import jwt, JWTError # Importação necessária para o JWT

# Importa de todos os nossos outros arquivos
from database import get_db
import models
import schemas
import auth
from auth import SECRET_KEY, ALGORITHM

# Importa o CORS
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="API Rastreabilidade - Versão Completa")

# --- Configuração do CORS ---
origins = [
    "http://localhost",
    "http://127.0.0.1:5500",
    "null",
    "https://app-rastreabilidade.onrender.com"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    
    # Se não encontrou em nenhuma
    raise credentials_exception

# --- Endpoint de Login (Autentica QUALQUER usuário) ---

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Recebe email (no campo 'username') e senha.
    Verifica em TODAS as 3 tabelas de usuários.
    """
    user = None
    
    # 1. Tenta como Técnico
    user_tecnico = db.query(models.TecnicoCampo).filter(models.TecnicoCampo.email == form_data.username).first()
    if user_tecnico and auth.verificar_senha(form_data.password, user_tecnico.hash_senha):
        user = user_tecnico

    # 2. Tenta como Serraria
    if not user:
        user_serraria = db.query(models.EquipeSerraria).filter(models.EquipeSerraria.email == form_data.username).first()
        if user_serraria and auth.verificar_senha(form_data.password, user_serraria.hash_senha):
            user = user_serraria
            
    # 3. Tenta como Fábrica
    if not user:
        user_fabrica = db.query(models.EquipeFabrica).filter(models.EquipeFabrica.email == form_data.username).first()
        if user_fabrica and auth.verificar_senha(form_data.password, user_fabrica.hash_senha):
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

# --- Endpoint de Teste de Conexão (Opcional, mas útil) ---
@app.get("/test-db")
def test_database_connection(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "SUCESSO", "message": "A conexão com o banco de dados está estável!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# --- NOVO ENDPOINT DE FERRAMENTA (GERADOR DE HASH) ---
@app.get("/hash-senha/{senha}")
def get_hash_para_senha(senha: str):
    """
    Ferramenta de debug. Pega uma senha da URL e retorna o hash
    bcrypt correto gerado por ESTE servidor.
    """
    try:
        hash_gerado = auth.get_hash_senha(senha)
        return {
            "senha_fornecida": senha,
            "hash_gerado_pelo_servidor": hash_gerado
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar hash: {e}")
# --- FIM DO NOVO ENDPOINT ---

# --- Endpoints Protegidos ---

@app.get("/users/me", response_model=schemas.UserDisplay)
def read_users_me(current_user = Depends(get_current_user)):
    """
    ATUALIZADO: Retorna id, email e ROLE do usuário logado.
    """
    role = "desconhecido" # Valor padrão
    
    # Verifica a 'instância' do objeto retornado por get_current_user
    if isinstance(current_user, models.TecnicoCampo):
        role = "tecnico"
    elif isinstance(current_user, models.EquipeSerraria):
        role = "serraria"
    elif isinstance(current_user, models.EquipeFabrica):
        role = "fabrica"
    
    # Monta o dicionário de resposta com o role detectado
    # Pydantic (UserDisplay) vai validar isso automaticamente
    return {"id": current_user.id, "email": current_user.email, "role": role}

# --- Endpoint Específico do Técnico ---
# Esta é uma dependência extra para rotas que SÓ técnicos podem acessar

def get_current_tecnico(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.TecnicoCampo:
    credentials_exception = HTTPException(status_code=401, detail="Não autorizado: Apenas Técnicos de Campo podem acessar esta rota.")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.TecnicoCampo).filter(models.TecnicoCampo.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/lotes_tora/", response_model=schemas.LoteToraDisplay, status_code=status.HTTP_201_CREATED)
def create_lote_tora(
    lote: schemas.LoteToraCreate, 
    db: Session = Depends(get_db), 
    current_user: models.TecnicoCampo = Depends(get_current_tecnico) # PROTEGIDO SÓ para técnicos
):
    """
    Cria um novo Lote de Tora. Requer login de Técnico de Campo.
    """
    today_str = datetime.date.today().strftime("%Y%m%d")
    count_today = db.query(models.LoteTora).filter(models.LoteTora.id_lote_custom.like(f"TORA-{today_str}-%")).count()
    new_id_custom = f"TORA-{today_str}-{str(count_today + 1).zfill(3)}"

    # Usa .model_dump() para compatibilidade com Pydantic v2
    db_lote = models.LoteTora(
        **lote.model_dump(),
        id_lote_custom=new_id_custom,
        id_tecnico_campo=current_user.id
    )
    
    try:
        db.add(db_lote)
        db.commit()
        db.refresh(db_lote)
        return db_lote
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao salvar no banco: {e}")
# ===================================
# ENDPOINTS DA SERRARIA
# Copie e cole este código no seu main.py, após os endpoints do técnico
# ===================================

# --- DEPENDÊNCIA: Verificar se é Serraria ---

def get_current_serraria(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.EquipeSerraria:
    """
    Verifica se o usuário logado é da equipe da serraria.
    """
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


# --- ENDPOINT 1: LISTAR LOTES DE TORA DISPONÍVEIS ---

@app.get("/lotes_tora/", response_model=List[schemas.LoteToraDisplay])
def listar_lotes_tora(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Lista todos os lotes de tora.
    Técnicos veem apenas os seus. Serraria e Fábrica veem todos.
    """
    # Se for técnico, mostra apenas os dele
    if isinstance(current_user, models.TecnicoCampo):
        lotes = db.query(models.LoteTora).filter(
            models.LoteTora.id_tecnico_campo == current_user.id
        ).all()
    else:
        # Serraria e Fábrica veem todos
        lotes = db.query(models.LoteTora).all()
    
    return lotes


# --- ENDPOINT 2: OBTER DETALHES DE UM LOTE DE TORA ---

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
    
    # Técnicos só podem ver seus próprios lotes
    if isinstance(current_user, models.TecnicoCampo) and lote.id_tecnico_campo != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado a este lote")
    
    return lote


# --- ENDPOINT 3: CRIAR LOTE SERRADO ---

@app.post("/lotes_serrada/", response_model=schemas.LoteSerradaDisplay, status_code=status.HTTP_201_CREATED)
def create_lote_serrado(
    lote: schemas.LoteSerradaCreate,
    db: Session = Depends(get_db),
    current_user: models.EquipeSerraria = Depends(get_current_serraria)
):
    """
    Cria um novo lote serrado a partir de um lote de tora.
    Apenas equipe da serraria pode executar.
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
    
    # 2. Calcular volume já processado deste lote
    lotes_ja_processados = db.query(models.LoteSerrado).filter(
        models.LoteSerrado.id_lote_tora_origem == lote.id_lote_tora_origem
    ).all()
    
    volume_processado = sum(float(ls.volume_saida_m3) for ls in lotes_ja_processados)
    volume_disponivel = float(lote_tora.volume_estimado_m3) - volume_processado
    
    # 3. Validar se há volume suficiente
    if float(lote.volume_saida_m3) > volume_disponivel:
        raise HTTPException(
            status_code=400,
            detail=f"Volume de saída ({lote.volume_saida_m3} m³) excede o volume disponível ({volume_disponivel:.2f} m³)"
        )
    
    # 4. Gerar ID customizado (SERR-YYYYMMDD-XXX)
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
        db.add(db_lote_serrado)
        db.commit()
        db.refresh(db_lote_serrado)
        return db_lote_serrado
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao salvar lote serrado: {e}")

# --- ENDPOINT 4: LISTAR MEUS LOTES SERRADOS ---

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


# ===================================
# FIM DOS ENDPOINTS DA SERRARIA
# ===================================

# ===================================
# ENDPOINTS DA FÁBRICA
# Copie e cole este código no seu main.py, após os endpoints da serraria
# ===================================

# --- DEPENDÊNCIA: Verificar se é Fábrica ---

def get_current_fabrica(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.EquipeFabrica:
    """
    Verifica se o usuário logado é da equipe da fábrica.
    """
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


# --- ENDPOINT 1: LISTAR LOTES SERRADOS DISPONÍVEIS ---

@app.get("/lotes_serrado/", response_model=List[schemas.LoteSerradaDisplay])
def listar_lotes_serrados_para_fabrica(
    db: Session = Depends(get_db),
    current_user: models.EquipeFabrica = Depends(get_current_fabrica)
):
    """
    Lista todos os lotes serrados disponíveis para fabricação.
    Apenas equipe da fábrica pode acessar.
    """
    lotes = db.query(models.LoteSerrado).order_by(
        models.LoteSerrado.data_processamento.desc()
    ).all()
    
    return lotes


# --- ENDPOINT 2: OBTER DETALHES DE UM LOTE SERRADO ---

@app.get("/lotes_serrado/{lote_id}", response_model=schemas.LoteSerradaDisplay)
def obter_lote_serrado_para_fabrica(
    lote_id: int,
    db: Session = Depends(get_db),
    current_user: models.EquipeFabrica = Depends(get_current_fabrica)
):
    """
    Obtém detalhes de um lote serrado específico.
    """
    lote = db.query(models.LoteSerrado).filter(models.LoteSerrado.id == lote_id).first()
    
    if not lote:
        raise HTTPException(status_code=404, detail="Lote serrado não encontrado")
    
    return lote


# --- ENDPOINT 3: CRIAR PRODUTO ACABADO ---

@app.post("/produtos_acabados/", response_model=schemas.LoteProdutoAcabadoDisplay, status_code=status.HTTP_201_CREATED)
def create_produto_acabado(
    produto: schemas.LoteProdutoAcabadoCreate,
    db: Session = Depends(get_db),
    current_user: models.EquipeFabrica = Depends(get_current_fabrica)
):
    """
    Cria um novo produto acabado a partir de um lote serrado.
    Apenas equipe da fábrica pode executar.
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
    
    # 2. Gerar ID customizado (PROD-YYYYMMDD-XXX)
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
    
    # 3. Gerar link do QR Code (se não foi fornecido)
    # Aqui você pode usar um serviço de geração de QR Code
    # Por enquanto, vamos usar um placeholder
    if not produto.link_qr_code:
        # URL de rastreabilidade que aponta para uma página pública
        produto.link_qr_code = f"https://app-rastreabilidade.onrender.com/rastrear.html?id={id_lote_produto_custom}"
    
    # 4. Criar o produto acabado
    db_produto = models.LoteProdutoAcabado(
        **produto.model_dump(),
        id_lote_produto_custom=id_lote_produto_custom,
        id_equipe_fabrica=current_user.id
    )
    
    try:
        db.add(db_produto)
        db.commit()
        db.refresh(db_produto)
        return db_produto
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao salvar produto acabado: {e}")


# --- ENDPOINT 4: LISTAR MEUS PRODUTOS ACABADOS ---

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


# --- ENDPOINT 5: OBTER DETALHES DE UM PRODUTO ACABADO ---

@app.get("/produtos_acabados/{produto_id}", response_model=schemas.LoteProdutoAcabadoDisplay)
def obter_produto_acabado(
    produto_id: int,
    db: Session = Depends(get_db),
    current_user: models.EquipeFabrica = Depends(get_current_fabrica)
):
    """
    Obtém detalhes de um produto acabado específico.
    """
    produto = db.query(models.LoteProdutoAcabado).filter(
        models.LoteProdutoAcabado.id == produto_id
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto acabado não encontrado")
    
    # Fábrica só pode ver seus próprios produtos
    if produto.id_equipe_fabrica != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado a este produto")
    
    return produto


# --- ENDPOINT 6: RASTREABILIDADE COMPLETA (PÚBLICO) ---

@app.get("/rastrear/{id_produto_custom}")
def rastrear_produto(id_produto_custom: str, db: Session = Depends(get_db)):
    """
    Endpoint PÚBLICO para rastrear um produto pela sua ID customizada.
    Retorna toda a cadeia de rastreabilidade: Produto → Serrado → Tora.
    """
    # Buscar o produto
    produto = db.query(models.LoteProdutoAcabado).filter(
        models.LoteProdutoAcabado.id_lote_produto_custom == id_produto_custom
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # Buscar lote serrado origem
    lote_serrado = db.query(models.LoteSerrado).filter(
        models.LoteSerrado.id == produto.id_lote_serrado_origem
    ).first()
    
    # Buscar lote de tora origem
    lote_tora = None
    if lote_serrado:
        lote_tora = db.query(models.LoteTora).filter(
            models.LoteTora.id == lote_serrado.id_lote_tora_origem
        ).first()
    
    # Montar resposta com toda a cadeia
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
# FIM DOS ENDPOINTS DA FÁBRICA
# ===================================