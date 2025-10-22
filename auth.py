import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# --- Configuração de Hash de Senha (bcrypt) ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_senha(senha_plana, hash_senha):
    """Verifica se a senha plana corresponde ao hash."""
    return pwd_context.verify(senha_plana, hash_senha)

def get_hash_senha(senha):
    """Gera o hash de uma senha plana."""
    return pwd_context.hash(senha)

# --- Configuração do Token JWT (Versão "Gambiarra" para Faculdade) ---

# Colocamos a chave direto no código.
# NÃO FAÇA ISSO EM PROJETOS REAIS!
SECRET_KEY = "41960d71f4f6e8a6cd5a2aea21d073c697bf0dbef6d0f63ede7b1452a0f009fe"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # Token expira em 1 dia

# Não precisamos mais da verificação, pois a chave está logo acima.
# if not SECRET_KEY:
#    raise ValueError("Variável de ambiente SECRET_KEY não definida.")

def criar_access_token(data: dict):
    """Cria um novo token de acesso JWT."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt