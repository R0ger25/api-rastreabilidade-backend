import os
import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from jose import jwt, JWTError # <-- IMPORTAÇÃO CORRIGIDA AQUI

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

def get_current_tecnico(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.TecnicoCampo:
    """
    Decodifica o token, pega o email e retorna o objeto do usuário (Técnico).
    Esta função PROTEGE um endpoint.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Agora o 'jwt' está definido e o código funciona
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError: # <-- E o JWTError também
        raise credentials_exception
    
    # Verifica se o usuário no token é um Técnico de Campo
    user = db.query(models.TecnicoCampo).filter(models.TecnicoCampo.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

# --- Endpoint de Login ---

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Recebe email (no campo 'username') e senha.
    Retorna um Token JWT se o login for válido.
    """
    user = db.query(models.TecnicoCampo).filter(models.TecnicoCampo.email == form_data.username).first()
    
    if not user or not auth.verificar_senha(form_data.password, user.hash_senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.criar_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- Endpoint de Teste de Conexão (Bom manter) ---
@app.get("/test-db")
def test_database_connection(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "SUCESSO", "message": "A conexão com o banco de dados está estável!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoints Protegidos (Técnico de Campo) ---

@app.get("/users/me", response_model=schemas.TecnicoDisplay)
def read_users_me(current_user: models.TecnicoCampo = Depends(get_current_tecnico)):
    """
    Rota protegida. Retorna as informações do usuário
    que está logado (dono do token).
    """
    return current_user

@app.post("/lotes_tora/", response_model=schemas.LoteToraDisplay, status_code=status.HTTP_201_CREATED)
def create_lote_tora(
    lote: schemas.LoteToraCreate, 
    db: Session = Depends(get_db), 
    current_user: models.TecnicoCampo = Depends(get_current_tecnico) # PROTEGIDO
):
    """
    Cria um novo Lote de Tora. Requer login de Técnico de Campo.
    """
    today_str = datetime.date.today().strftime("%Y%m%d")
    count_today = db.query(models.LoteTora).filter(models.LoteTora.id_lote_custom.like(f"TORA-{today_str}-%")).count()
    new_id_custom = f"TORA-{today_str}-{str(count_today + 1).zfill(3)}"

    db_lote = models.LoteTora(
        **lote.dict(),
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