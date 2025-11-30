# 🔌 Guia de Configuração do Banco de Dados

Este guia explica como conectar a aplicação ao banco de dados PostgreSQL.

## 📋 Pré-requisitos

- PostgreSQL instalado (local ou serviço em nuvem como Render.com)
- Python 3.8+ instalado
- Dependências do projeto instaladas

## 🚀 Passo a Passo

### 1️⃣ Instalar PostgreSQL

#### Opção A: Local (Desenvolvimento)
- **Windows**: Baixe em https://www.postgresql.org/download/windows/
- **Linux**: `sudo apt install postgresql postgresql-contrib`
- **macOS**: `brew install postgresql`

#### Opção B: Render.com (Produção)
1. Acesse https://render.com
2. Crie um novo PostgreSQL Database
3. Copie a "External Database URL"

### 2️⃣ Criar o Banco de Dados

Se estiver usando PostgreSQL local:

```bash
# Acesse o PostgreSQL
psql -U postgres

# Crie o banco
CREATE DATABASE rastreabilidade;

# Saia do psql
\q
```

### 3️⃣ Configurar o Arquivo .env

```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite o arquivo .env com suas credenciais
# Use um editor de texto (nano, vim, vscode, etc)
nano .env
```

**Formato da DATABASE_URL:**
```
postgresql://USUARIO:SENHA@HOST:PORTA/BANCO
```

**Exemplos:**

Local:
```
DATABASE_URL=postgresql://postgres:minhasenha@localhost:5432/rastreabilidade
```

Render.com:
```
DATABASE_URL=postgresql://rastreabilidade_user:abc123xyz@dpg-xxxxx.oregon-postgres.render.com/rastreabilidade
```

### 4️⃣ Instalar Dependências Python

```bash
pip install -r requirements.txt
```

### 5️⃣ Criar as Tabelas

```bash
python init_db.py
```

Você deve ver:
```
✅ Tabelas criadas com sucesso!

Tabelas criadas:
  - tecnicos_campo
  - equipe_serraria
  - equipe_fabrica
  - lotes_tora
  - lotes_serrada
  - lotes_produto_acabado
```

### 6️⃣ Testar a Conexão

```bash
# Inicie a aplicação
uvicorn main:app --reload

# Em outro terminal ou navegador, acesse:
curl http://localhost:8000/test-db
```

Resposta esperada:
```json
{
  "status": "SUCESSO",
  "message": "A conexão com o banco de dados está estável!"
}
```

## 🔍 Estrutura das Tabelas

### Tabelas de Usuários:
1. **tecnicos_campo** - Técnicos de campo que registram lotes de tora
2. **equipe_serraria** - Equipes que processam madeira serrada
3. **equipe_fabrica** - Equipes que fabricam produtos acabados

### Tabelas de Produtos:
4. **lotes_tora** - Lotes de madeira em tora
5. **lotes_serrada** - Lotes de madeira serrada
6. **lotes_produto_acabado** - Produtos finalizados

## ⚠️ Troubleshooting

### Erro: "Variável de ambiente DATABASE_URL não definida"
- Certifique-se de que o arquivo `.env` existe na raiz do projeto
- Verifique se a variável `DATABASE_URL` está corretamente definida

### Erro: "could not connect to server"
- Verifique se o PostgreSQL está rodando: `systemctl status postgresql` (Linux)
- Confirme o host e porta corretos
- Verifique firewall e permissões de rede

### Erro: "password authentication failed"
- Confirme usuário e senha corretos
- No PostgreSQL local, edite `pg_hba.conf` se necessário

### Erro: "database does not exist"
- Crie o banco de dados usando o comando `CREATE DATABASE`

## 📚 Recursos Adicionais

- [Documentação SQLAlchemy](https://docs.sqlalchemy.org/)
- [Documentação PostgreSQL](https://www.postgresql.org/docs/)
- [Documentação FastAPI + Databases](https://fastapi.tiangolo.com/tutorial/sql-databases/)

## 🔐 Segurança

⚠️ **IMPORTANTE:**
- NUNCA commite o arquivo `.env` no Git
- Use senhas fortes para ambientes de produção
- Em produção, use variáveis de ambiente do servidor (não arquivo .env)
- Mantenha backups regulares do banco de dados
