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
    """Limpa CPF/CNPJ - remove caracteres não numéricos"""
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
                    "number": clean_document(customer.get('document')),
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
        print(f"Headers Authorization: Basic {basic_auth[:50]}...")
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
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text}")
        
        # ✅ DEBUG DETALHADO DA RESPOSTA
        if response.status_code == 201:
            response_data = response.json()
            print("=== DADOS PIX RECEBIDOS ===")
            print(f"Resposta completa: {response_data}")
            
            # Verificar se temos dados PIX
            if 'pix' in response_data and response_data['pix']:
                pix_data = response_data['pix']
                print(f"Dados PIX: {pix_data}")
                
                # Garantir que temos qrCode
                if 'qrCode' in pix_data:
                    print(f"✅ QR Code recebido: {pix_data['qrCode'][:50]}...")
                else:
                    print("❌ QR Code não encontrado na resposta PIX")
                    
            else:
                print("❌ Dados PIX não encontrados na resposta")
                print(f"Estrutura da resposta: {list(response_data.keys())}")
                
            return jsonify(response_data), 201
            
        else:
            # ❌ ERRO NA GHOSTPAY
            try:
                error_response = response.json()
                error_details = error_response.get('refusedReason', {}).get('description', response.text)
                print(f"❌ ERRO GHOSTPAY: {error_details}")
            except:
                error_details = response.text
                print(f"❌ ERRO GHOSTPAY (raw): {error_details}")
                
            return jsonify({
                "error": True,
                "message": f"Erro na API GhostPay: {response.status_code}",
                "details": error_details,
                "status_code": response.status_code,
                "debug_info": {
                    "payload_enviado": payload,
                    "resposta_ghostpay": response.text
                }
            }), response.status_code
            
    except Exception as e:
        print(f"ERRO INTERNO: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            "error": True,
            "message": f"Erro interno: {str(e)}",
            "traceback": traceback.format_exc()
        }), 500

@app.route('/test-pix-debug', methods=['GET'])
def test_pix_debug():
    """Teste COMPLETO com debug detalhado"""
    try:
        # ✅ PAYLOAD IDÊNTICO AO QUE O FRONTEND ENVIA
        test_payload = {
            "customer": {
                "name": "MAURICIO",
                "email": "MAURICIO.MARTINS@GMAIL.COM", 
                "document": "10931469740"
            },
            "amount": 25000,
            "description": "Doação Rio Bonito SOS - MAURICIO"
        }
        
        customer = test_payload['customer']
        amount = test_payload['amount']
        
        # ✅ RECRIANDO O PAYLOAD EXATO DO create-payment
        payload = {
            "paymentMethod": "PIX",
            "customer": {
                "name": customer['name'],
                "email": customer['email'],
                "phone": "11999999999",
                "document": {
                    "number": clean_document(customer.get('document')),
                    "type": "CPF"
                }
            },
            "items": [
                {
                    "title": "Doação para Rio Bonito SOS",
                    "unitPrice": amount,
                    "quantity": 1,
                    "externalRef": f"test-{int(time.time())}"
                }
            ],
            "amount": amount,
            "description": test_payload.get('description', 'Doação para Rio Bonito SOS'),
            "metadata": {
                "campaign": "rio-bonito-sos", 
                "source": "website"
            },
            "pix": {}
        }
        
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'authorization': f'Basic {basic_auth}'
        }
        
        print("=== TESTE PIX DEBUG - PAYLOAD IDÊNTICO ===")
        print(f"Payload: {payload}")
        
        response = requests.post(
            GHOSTPAY_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        result = {
            "status_code": response.status_code,
            "success": response.status_code == 201,
            "ghostpay_response": response.json() if response.text else {},
            "request_debug": {
                "url": GHOSTPAY_URL,
                "headers": {"authorization": f"Basic {basic_auth[:50]}..."},
                "payload": payload
            },
            "pix_data_present": False,
            "qr_code_present": False
        }
        
        # ✅ VERIFICAR DADOS PIX
        if response.status_code == 201:
            response_data = response.json()
            result["ghostpay_response"] = response_data
            
            if 'pix' in response_data and response_data['pix']:
                result["pix_data_present"] = True
                if 'qrCode' in response_data['pix']:
                    result["qr_code_present"] = True
                    result["qr_code_preview"] = response_data['pix']['qrCode'][:100] + "..."
        
        print(f"=== RESULTADO TESTE DEBUG ===")
        print(f"Status: {result['status_code']}")
        print(f"PIX Data Present: {result['pix_data_present']}")
        print(f"QR Code Present: {result['qr_code_present']}")
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": True,
            "message": f"Erro no teste: {str(e)}",
            "traceback": str(e)
        }), 500

@app.route('/debug-ghostpay-response', methods=['GET'])
def debug_ghostpay_response():
    """Analisa a estrutura da resposta da GhostPay"""
    try:
        # Payload mínimo para teste
        test_payload = {
            "paymentMethod": "PIX",
            "customer": {
                "name": "Teste Debug",
                "email": "debug@test.com",
                "phone": "11999999999",
                "document": {
                    "number": "00000000191",
                    "type": "CPF"
                }
            },
            "items": [{
                "title": "Teste Debug",
                "unitPrice": 1000,
                "quantity": 1,
                "externalRef": "debug-001"
            }],
            "amount": 1000,
            "description": "Teste Debug",
            "pix": {}
        }
        
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'authorization': f'Basic {basic_auth}'
        }
        
        response = requests.post(GHOSTPAY_URL, json=test_payload, headers=headers, timeout=30)
        
        analysis = {
            "status_code": response.status_code,
            "response_keys": [],
            "has_pix": False,
            "pix_structure": {},
            "full_response": response.json() if response.text else {}
        }
        
        if response.status_code == 201:
            data = response.json()
            analysis["response_keys"] = list(data.keys())
            analysis["has_pix"] = 'pix' in data
            if analysis["has_pix"]:
                analysis["pix_structure"] = {
                    "pix_keys": list(data['pix'].keys()) if data['pix'] else [],
                    "pix_data": data['pix']
                }
        
        return jsonify(analysis)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return jsonify({
        "message": "API Rio Bonito SOS - Debug Mode",
        "version": "4.0.0",
        "status": "Debug Ativo",
        "endpoints_debug": {
            "test_pix_complete": "/test-pix-debug (GET)",
            "analyze_response": "/debug-ghostpay-response (GET)",
            "health": "/health (GET)"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
