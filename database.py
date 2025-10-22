import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

# Carrega variáveis de ambiente (do .env local ou do Render)
load_dotenv()

# Pegue esta URL no dashboard do seu banco de dados no Render
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("Variável de ambiente DATABASE_URL não definida. Verifique seu .env ou as variáveis no Render.")

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base = declarative_base()
    
    print("Conexão com o banco de dados configurada com sucesso.")
except Exception as e:
    print(f"ERRO AO CONFIGURAR O BANCO DE DADOS: {e}")
    # Se falhar aqui, a aplicação vai quebrar, o que é bom para debug.

# Helper para obter uma sessão do banco em cada requisição
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()