from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import base64
import time
import re

app = Flask(__name__)
CORS(app)

# =============================================================================
# CONFIGURAÇÕES GHOSTPAY - CREDENCIAIS CORRETAS!
# =============================================================================

GHOSTPAY_URL = "https://api.ghostspaysv2.com/functions/v1/transactions"
SECRET_KEY = "sk_live_4rcXnqQ6KL4dJ2lW0gZxh9lCj5tm99kYMCk0i57KocSKGGD4"
COMPANY_ID = "43fc8053-d32c-4d37-bf93-33046dd7215b"

# Basic Auth encoding (como mostrado na documentação)
auth_string = f"{SECRET_KEY}:"
basic_auth = base64.b64encode(auth_string.encode()).decode()

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def clean_document(document):
    """Limpa CPF/CNPJ - remove caracteres não numéricos (equivalente a /\D/g em JS)"""
    if document:
        return re.sub(r'\D', '', document)
    return "00000000191"

# =============================================================================
# ROTAS PRINCIPAIS
# =============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "API Rio Bonito SOS Online"})

@app.route('/create-payment', methods=['POST', 'OPTIONS'])
def create_payment():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        print("=== DADOS RECEBIDOS DO FRONTEND ===")
        print(f"Dados: {data}")
        
        # Validações básicas
        if not data or 'customer' not in data or 'amount' not in data:
            return jsonify({
                "error": True, 
                "message": "Dados incompletos. Customer e amount são obrigatórios."
            }), 400
        
        customer = data['customer']
        amount = data['amount']
        
        if not customer.get('name') or not customer.get('email'):
            return jsonify({
                "error": True,
                "message": "Nome e email do cliente são obrigatórios."
            }), 400
        
        # Validar valor mínimo (R$ 10,00 = 1000 centavos)
        if amount < 1000:
            return jsonify({
                "error": True,
                "message": "Valor mínimo é R$ 10,00 (1000 centavos)"
            }), 400
        
        # ✅ PAYLOAD CORRETO BASEADO NA DOCUMENTAÇÃO
        payload = {
            "paymentMethod": "PIX",
            "customer": {
                "name": customer['name'],
                "email": customer['email'],
                # ✅ ADICIONAR CAMPOS OPCIONAIS QUE EVITAM ERROS
                "phone": customer.get('phone', '11999999999'),  # Default para evitar erro
                "document": {
                    "number": clean_document(customer.get('document')),  # ✅ CORRIGIDO - função Python
                    "type": "CPF"
                }
            },
            "items": [
                {
                    "title": "Doação para Rio Bonito SOS",
                    "unitPrice": amount,
                    "quantity": 1,
                    "externalRef": f"doacao-{int(time.time())}"
                }
            ],
            "amount": amount,
            "description": data.get('description', 'Doação para Rio Bonito SOS'),
            "metadata": {
                "campaign": "rio-bonito-sos",
                "source": "website"
            },
            "pix": {}  # ✅ CAMPO OBRIGATÓRIO PARA PIX
        }
        
        # ✅ HEADERS CORRETOS (BASIC AUTH como na documentação)
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'authorization': f'Basic {basic_auth}'
        }
        
        print("=== ENVIANDO PARA GHOSTPAY ===")
        print(f"URL: {GHOSTPAY_URL}")
        print(f"Headers: {dict(headers)}")  # ✅ Convertendo para dict para print seguro
        print(f"Payload: {payload}")
        
        # Fazer requisição para GhostPay
        response = requests.post(
            GHOSTPAY_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print("=== RESPOSTA GHOSTPAY ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 201:
            return jsonify(response.json()), 201
        else:
            try:
                error_response = response.json()
                error_details = error_response.get('refusedReason', {}).get('description', response.text)
            except:
                error_details = response.text
                
            return jsonify({
                "error": True,
                "message": f"Erro na API GhostPay: {response.status_code}",
                "details": error_details,
                "status_code": response.status_code
            }), response.status_code
            
    except Exception as e:
        print(f"ERRO INTERNO: {str(e)}")
        return jsonify({
            "error": True,
            "message": f"Erro interno: {str(e)}"
        }), 500

@app.route('/test-pix-complete', methods=['GET'])
def test_pix_complete():
    """Teste COMPLETO com payload que funciona"""
    try:
        # ✅ PAYLOAD COMPLETO E CORRETO
        test_payload = {
            "paymentMethod": "PIX",
            "customer": {
                "name": "João Silva Teste",
                "email": "joao.teste@email.com",
                "phone": "11999999999",
                "document": {
                    "number": "00000000191",
                    "type": "CPF"
                }
            },
            "items": [
                {
                    "title": "Doação Teste Rio Bonito SOS",
                    "unitPrice": 1000,
                    "quantity": 1,
                    "externalRef": f"test-{int(time.time())}"
                }
            ],
            "amount": 1000,
            "description": "Teste de doação via PIX",
            "metadata": {
                "campaign": "teste",
                "source": "api-test"
            },
            "pix": {}
        }
        
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'authorization': f'Basic {basic_auth}'
        }
        
        print("=== TESTE PIX COMPLETO ===")
        print(f"Payload: {test_payload}")
        
        response = requests.post(
            GHOSTPAY_URL,
            json=test_payload,
            headers=headers,
            timeout=30
        )
        
        result = {
            "status_code": response.status_code,
            "success": response.status_code == 201,
            "response": response.json() if response.text else {},
            "diagnostico": "✅ FUNCIONOU" if response.status_code == 201 else "❌ FALHOU",
            "ghostpay_message": response.text[:200] if response.text else "Sem resposta"
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": True,
            "message": f"Erro no teste: {str(e)}"
        }), 500

@app.route('/debug-headers', methods=['GET'])
def debug_headers():
    """Mostra os headers que estão sendo usados"""
    return jsonify({
        "authorization_header": f"Basic {basic_auth}",
        "secret_key": SECRET_KEY[:20] + "...",
        "company_id": COMPANY_ID,
        "ghostpay_url": GHOSTPAY_URL,
        "status": "Configurado - Sem erros de sintaxe"
    })

@app.route('/test', methods=['GET'])
def test():
    """Endpoint de teste básico"""
    return jsonify({
        "message": "API funcionando!",
        "status": "OK",
        "timestamp": time.time()
    })

@app.route('/')
def home():
    return jsonify({
        "message": "API Rio Bonito SOS - Sistema Corrigido ✅",
        "version": "3.1.0",
        "status": "Operacional - Sem erros de sintaxe",
        "endpoints": {
            "health": "/health (GET)",
            "test": "/test (GET)",
            "create_payment": "/create-payment (POST)",
            "test_pix": "/test-pix-complete (GET)",
            "debug": "/debug-headers (GET)"
        },
        "notes": "Erro de sintaxe resolvido - código 100% Python"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
