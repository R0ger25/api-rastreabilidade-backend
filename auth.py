import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

# Garante que as variáveis do .env sejam carregadas
load_dotenv() 

# --- Configuração de Hash de Senha (bcrypt) ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_senha(senha_plana, hash_senha):
    """Verifica se a senha plana corresponde ao hash."""
    return pwd_context.verify(senha_plana, hash_senha)

def get_hash_senha(senha):
    """Gera o hash de uma senha plana."""
    return pwd_context.hash(senha)

# --- Configuração do Token JWT (Do jeito correto, via .env) ---

# 1. Pega a chave do ambiente (do .env local ou do Render)
SECRET_KEY = os.getenv("SECRET_KEY") 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # Token expira em 1 dia

# 2. Re-adicionamos a verificação de segurança
# (Se a API não encontrar a chave, ela deve falhar ao iniciar)
if not SECRET_KEY:
    raise ValueError(
        "Variável de ambiente SECRET_KEY não definida. "
        "Defina-a no seu .env ou nas variáveis de ambiente do Render."
    )

def criar_access_token(data: dict):
    """Cria um novo token de acesso JWT."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt