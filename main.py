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
    Rota protegida genérica. Retorna as informações (id, email)
    do usuário que está logado (seja ele Técnico, Serraria ou Fábrica).
    """
    return current_user

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

# (Aqui você pode adicionar os endpoints para Serraria e Fábrica, se precisar)