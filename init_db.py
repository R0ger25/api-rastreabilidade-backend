"""
Script para inicializar o banco de dados.
Cria todas as tabelas definidas nos models.py

Uso:
    python init_db.py
"""
from database import engine, Base
import models

def init_database():
    """Cria todas as tabelas no banco de dados"""
    try:
        print("Iniciando criação das tabelas...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tabelas criadas com sucesso!")
        print("\nTabelas criadas:")
        print("  - tecnicos_campo")
        print("  - equipe_serraria")
        print("  - equipe_fabrica")
        print("  - lotes_tora")
        print("  - lotes_serrada")
        print("  - lotes_produto_acabado")
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        raise

if __name__ == "__main__":
    init_database()
