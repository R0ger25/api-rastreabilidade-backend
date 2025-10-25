import os
import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from jose import jwt, JWTError # Importação correta

# Importa de todos os nossos outros arquivos
from database import get_db
import models
import schemas
import auth
from auth import SECRET_KEY, ALGORITHM

# Importa o CORS
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="API Rastreabilidade - Versão Completa")

# --- Configuração do CORS (formatação limpa) ---
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
    CORRIGIDO: Esta função agora é genérica.
    Decodifica o token e retorna o objeto do usuário de QUALQUER tabela.
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

# --- Endpoint de Login (CORRIGIDO) ---

# ... (o resto do seu main.py, importações, etc, fica igual) ...

# ... (o resto do seu main.py, importações, etc, fica igual) ...

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Recebe email (no campo 'username') e senha.
    Verifica em todas as 3 tabelas de usuários.
    """
    
    print("--- INICIANDO TENTATIVA DE LOGIN ---")
    print(f"Username recebido: {form_data.username}")
    print(f"Password recebida (tamanho): {len(form_data.password)}")
    print("-----------------------------------")

    user = None
    
    # 1. Tenta como Técnico
    user_tecnico = db.query(models.TecnicoCampo).filter(models.TecnicoCampo.email == form_data.username).first()
    
    # --- NOVO DEBUG DE COMPARAÇÃO AVANÇADO ---
    if user_tecnico:
        print("--- DEBUG AVANÇADO: ENCONTROU USUÁRIO TÉCNICO ---")
        senha_digitada = form_data.password
        hash_do_banco = user_tecnico.hash_senha
        
        # [PROVA 1]: Vamos ver o hash "sujo"
        print(f"[1] Senha digitada: '{senha_digitada}'")
        print(f"[2] Hash do Banco (Repr): {repr(hash_do_banco)}")
        print(f"[2] Hash do Banco (Tamanho): {len(hash_do_banco)}")
        if len(hash_do_banco) != 60:
             print("[!] ALERTA: Um hash bcrypt padrão tem EXATAMENTE 60 caracteres. O seu tem {len(hash_do_banco)}. Provavelmente tem espaços extras.")

        # [PROVA 2]: O TESTE DE CONTROLE
        # Vamos verificar a senha digitada contra o hash LIMPO (que eu colei aqui)
        hash_limpo_conhecido = '$2b$12$E.C3mF4m1J3n1.X/2k.HGe.g.S/uS6xWctbO33.jL2N0mS/m/L.Oq'
        try:
            resultado_controle = auth.verificar_senha(senha_digitada, hash_limpo_conhecido)
            print(f"[3] TESTE DE CONTROLE ('{senha_digitada}' vs hash LIMPO): {resultado_controle}")
        except Exception as e:
            print(f"[3] TESTE DE CONTROLE FALHOU: {e}")

        # [PROVA 3]: A VERIFICAÇÃO REAL (que está falhando)
        print("--- Executando verificação real... ---")
        try:
            resultado_real = auth.verificar_senha(senha_digitada, hash_do_banco)
            print(f"[4] VERIFICAÇÃO REAL ('{senha_digitada}' vs Hash do Banco): {resultado_real}")
            
            if resultado_real:
                print("[>] VERIFICAÇÃO REAL BATEU! Login deve funcionar.")
                user = user_tecnico
            else:
                print("[X] VERIFICAÇÃO REAL FALHOU! (Compare com o Teste de Controle)")
        except Exception as e:
            print(f"[X] ERRO AO VERIFICAR SENHA (passlib quebrou): {e}")
        print("-----------------------------------")
        
    else:
        print(f"--- DEBUG: Usuário '{form_data.username}' NÃO ENCONTRADO na tabela tecnicos_campo ---")
    # --- FIM DO DEBUG ---

    # 2. Tenta como Serraria
    if not user:
        # ... (código da serraria) ...
            
    # 3. Tenta como Fábrica
    if not user:
        # ... (código da fábrica) ...

    # 4. Se não encontrou em nenhuma
    if not user:
        print("--- DEBUG: Login FALHOU. Retornando 401 ---")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 5. Se encontrou, cria o token
    print("--- DEBUG: Login BEM-SUCEDIDO. Criando token ---")
    access_token = auth.criar_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# ... (o resto do seu main.py, /test-db, /users/me, etc) ...

# --- Endpoint de Teste de Conexão (Bom manter) ---
@app.get("/test-db")
def test_database_connection(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "SUCESSO", "message": "A conexão com o banco de dados está estável!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoints Protegidos ---

@app.get("/users/me", response_model=schemas.UserDisplay)
def read_users_me(current_user = Depends(get_current_user)):
    """
    CORRIGIDO: Rota protegida genérica.
    Usa o get_current_user e retorna o schemas.UserDisplay.
    """
    return current_user

# --- Endpoint Específico do Técnico ---
# (Precisamos manter a função get_current_tecnico se quisermos 
# ter rotas que SÓ técnicos podem acessar)

def get_current_tecnico(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.TecnicoCampo:
    # Esta função é a mesma que você tinha, mas agora é usada SÓ para esta rota
    credentials_exception = HTTPException(status_code=401, detail="Não autorizado: Apenas Técnicos de Campo")
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
    current_user: models.TecnicoCampo = Depends(get_current_tecnico) # Protegido SÓ para técnicos
):
    """
    Cria um novo Lote de Tora. Requer login de Técnico de Campo.
    """
    today_str = datetime.date.today().strftime("%Y%m%d")
    count_today = db.query(models.LoteTora).filter(models.LoteTora.id_lote_custom.like(f"TORA-{today_str}-%")).count()
    new_id_custom = f"TORA-{today_str}-{str(count_today + 1).zfill(3)}"

    db_lote = models.LoteTora(
        **lote.model_dump(), # CORRIGIDO: de .dict() para .model_dump() (Pydantic v2)
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