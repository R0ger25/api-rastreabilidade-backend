"""
blockchain.py - Módulo de integração com Ethereum Sepolia
Gerencia a comunicação entre o backend FastAPI e o Smart Contract
"""

import os
from web3 import Web3
from typing import Optional, Dict
import json

# ===================================
# CONFIGURAÇÃO
# ===================================

# URL do provedor Ethereum (Infura ou Alchemy)
# Você precisa criar uma conta em https://infura.io ou https://alchemy.com
INFURA_URL = os.getenv("INFURA_SEPOLIA_URL", "https://sepolia.infura.io/v3/SEU_PROJECT_ID")

# Endereço do contrato deployado (você vai obter isso após fazer deploy no Remix)
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x...")

# ABI do contrato (copie do Remix após compilar)
CONTRACT_ABI = json.loads(os.getenv("CONTRACT_ABI", "[]"))

# Chave privada da conta que vai enviar transações
# NUNCA commite isso no Git! Use variáveis de ambiente!
PRIVATE_KEY = os.getenv("ETHEREUM_PRIVATE_KEY", "")

# Endereço da carteira
WALLET_ADDRESS = os.getenv("ETHEREUM_WALLET_ADDRESS", "")

# Converter para checksum address se necessário
if WALLET_ADDRESS and not WALLET_ADDRESS.startswith("0x"):
    WALLET_ADDRESS = "0x" + WALLET_ADDRESS

if WALLET_ADDRESS and WALLET_ADDRESS != "":
    try:
        from web3 import Web3 as Web3Check
        WALLET_ADDRESS = Web3Check.to_checksum_address(WALLET_ADDRESS)
        print(f"✅ Wallet address convertido para checksum: {WALLET_ADDRESS}")
    except Exception as e:
        print(f"⚠️ Erro ao converter wallet address: {e}")

# Converter CONTRACT_ADDRESS para checksum também
if CONTRACT_ADDRESS and CONTRACT_ADDRESS != "0x...":
    try:
        from web3 import Web3 as Web3Check
        CONTRACT_ADDRESS = Web3Check.to_checksum_address(CONTRACT_ADDRESS)
        print(f"✅ Contract address convertido para checksum: {CONTRACT_ADDRESS}")
    except Exception as e:
        print(f"⚠️ Erro ao converter contract address: {e}")

# ===================================
# INICIALIZAÇÃO WEB3
# ===================================

# Conectar ao provedor
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

# Verificar conexão
if w3.is_connected():
    print("✅ Conectado à Ethereum Sepolia!")
else:
    print("❌ Erro ao conectar à Ethereum")

# Instanciar o contrato
contract = None
if CONTRACT_ADDRESS != "0x..." and len(CONTRACT_ABI) > 0:
    try:
        contract_address_checksum = w3.to_checksum_address(CONTRACT_ADDRESS)
        contract = w3.eth.contract(address=contract_address_checksum, abi=CONTRACT_ABI)
        print(f"✅ Contrato carregado: {contract_address_checksum}")
    except Exception as e:
        print(f"❌ Erro ao carregar contrato: {e}")

# ===================================
# FUNÇÕES AUXILIARES
# ===================================

def to_checksum_address(address: str) -> str:
    """
    Converte qualquer endereço para formato checksum
    """
    try:
        if not address or address == "":
            return address
        if not address.startswith("0x"):
            address = "0x" + address
        return w3.to_checksum_address(address)
    except Exception as e:
        print(f"⚠️ Erro ao converter endereço {address}: {e}")
        return address

def converter_volume_para_blockchain(volume_decimal: float) -> int:
    """
    Converte volume decimal para inteiro (multiplica por 100)
    Exemplo: 150.75 -> 15075
    """
    return int(volume_decimal * 100)

def converter_coordenadas(lat: float, lon: float) -> str:
    """
    Converte coordenadas para string
    Exemplo: -3.119028, -60.021731 -> "-3.119028,-60.021731"
    """
    return f"{lat},{lon}"

def build_transaction(function_call) -> dict:
    """
    Constrói uma transação para enviar ao blockchain
    """
    # Garantir que WALLET_ADDRESS está em formato checksum
    wallet_checksum = w3.to_checksum_address(WALLET_ADDRESS)
    
    nonce = w3.eth.get_transaction_count(wallet_checksum)
    
    # Estimar gas
    try:
        gas_estimate = function_call.estimate_gas({'from': wallet_checksum})
    except Exception as e:
        print(f"⚠️ Erro ao estimar gas: {e}")
        gas_estimate = 300000  # Valor padrão
    
    # Construir transação
    transaction = function_call.build_transaction({
        'from': wallet_checksum,
        'nonce': nonce,
        'gas': gas_estimate,
        'gasPrice': w3.eth.gas_price,
        'chainId': 11155111  # Sepolia chain ID
    })
    
    return transaction

def send_transaction(transaction: dict) -> Optional[str]:
    """
    Assina e envia uma transação para o blockchain
    Retorna o hash da transação se bem-sucedido
    """
    try:
        # Assinar transação
        signed_txn = w3.eth.account.sign_transaction(transaction, PRIVATE_KEY)
        
        # Enviar transação
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Aguardar confirmação
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if tx_receipt['status'] == 1:
            print(f"✅ Transação bem-sucedida: {tx_hash.hex()}")
            return tx_hash.hex()
        else:
            print(f"❌ Transação falhou")
            return None
            
    except Exception as e:
        print(f"❌ Erro ao enviar transação: {e}")
        return None

# ===================================
# FUNÇÕES PRINCIPAIS
# ===================================

def registrar_lote_tora_blockchain(
    id_lote_custom: str,
    coordenadas_lat: float,
    coordenadas_lon: float,
    numero_dof: str,
    numero_licenca: str,
    especie: str,
    volume_m3: float
) -> Optional[str]:
    """
    Registra um lote de tora no blockchain
    Retorna o hash da transação se bem-sucedido
    """
    if not contract:
        print("⚠️ Contrato não configurado")
        return None
    
    try:
        # Preparar dados
        coordenadas_str = converter_coordenadas(coordenadas_lat, coordenadas_lon)
        volume_int = converter_volume_para_blockchain(volume_m3)
        
        # Chamar função do contrato
        function_call = contract.functions.registrarLoteTora(
            id_lote_custom,
            coordenadas_str,
            numero_dof,
            numero_licenca,
            especie,
            volume_int
        )
        
        # Construir e enviar transação
        transaction = build_transaction(function_call)
        tx_hash = send_transaction(transaction)
        
        return tx_hash
        
    except Exception as e:
        print(f"❌ Erro ao registrar lote de tora: {e}")
        return None

def registrar_lote_serrado_blockchain(
    id_lote_serrado_custom: str,
    id_lote_tora_origem: str,
    volume_saida_m3: float,
    tipo_produto: str,
    dimensoes: str
) -> Optional[str]:
    """
    Registra um lote serrado no blockchain
    """
    if not contract:
        print("⚠️ Contrato não configurado")
        return None
    
    try:
        volume_int = converter_volume_para_blockchain(volume_saida_m3)
        
        function_call = contract.functions.registrarLoteSerrado(
            id_lote_serrado_custom,
            id_lote_tora_origem,
            volume_int,
            tipo_produto or "",
            dimensoes or ""
        )
        
        transaction = build_transaction(function_call)
        tx_hash = send_transaction(transaction)
        
        return tx_hash
        
    except Exception as e:
        print(f"❌ Erro ao registrar lote serrado: {e}")
        return None

def registrar_produto_acabado_blockchain(
    id_produto_custom: str,
    id_lote_serrado_origem: str,
    sku_produto: str,
    nome_produto: str
) -> Optional[str]:
    """
    Registra um produto acabado no blockchain
    """
    if not contract:
        print("⚠️ Contrato não configurado")
        return None
    
    try:
        function_call = contract.functions.registrarProdutoAcabado(
            id_produto_custom,
            id_lote_serrado_origem,
            sku_produto,
            nome_produto
        )
        
        transaction = build_transaction(function_call)
        tx_hash = send_transaction(transaction)
        
        return tx_hash
        
    except Exception as e:
        print(f"❌ Erro ao registrar produto acabado: {e}")
        return None

def obter_rastreabilidade_blockchain(id_produto: str) -> Optional[Dict]:
    """
    Obtém rastreabilidade completa de um produto do blockchain
    """
    if not contract:
        print("⚠️ Contrato não configurado")
        return None
    
    try:
        resultado = contract.functions.obterRastreabilidadeCompleta(id_produto).call()
        
        # Desestruturar resultado
        produto, serrado, tora = resultado
        
        return {
            "produto": {
                "id_custom": produto[0],
                "id_lote_serrado_origem": produto[1],
                "timestamp": produto[2],
                "sku": produto[3],
                "nome": produto[4],
                "fabrica_responsavel": produto[5]
            },
            "lote_serrado": {
                "id_custom": serrado[0],
                "id_lote_tora_origem": serrado[1],
                "timestamp": serrado[2],
                "volume_m3": serrado[3] / 100,  # Converter de volta
                "tipo_produto": serrado[4],
                "dimensoes": serrado[5],
                "serraria_responsavel": serrado[6]
            },
            "lote_tora": {
                "id_custom": tora[0],
                "timestamp": tora[1],
                "coordenadas": tora[2],
                "numero_dof": tora[3],
                "numero_licenca": tora[4],
                "especie": tora[5],
                "volume_m3": tora[6] / 100,  # Converter de volta
                "tecnico_responsavel": tora[7]
            }
        }
        
    except Exception as e:
        print(f"❌ Erro ao obter rastreabilidade: {e}")
        return None

def verificar_lote_existe(id_lote: str, tipo: str = "tora") -> bool:
    """
    Verifica se um lote existe no blockchain
    tipo: 'tora', 'serrado', ou 'produto'
    """
    if not contract:
        return False
    
    try:
        if tipo == "tora":
            return contract.functions.lotesToraExiste(id_lote).call()
        elif tipo == "serrado":
            return contract.functions.loteSerradoExiste(id_lote).call()
        elif tipo == "produto":
            return contract.functions.produtoExiste(id_lote).call()
        else:
            return False
    except Exception as e:
        print(f"❌ Erro ao verificar existência: {e}")
        return False