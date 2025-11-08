from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# Configurações da API GhostPay
GHOSTPAY_URL = "https://api.ghostspaysv2.com/functions/v1/transactions"
SECRET_KEY = "sk_live_4rcXnqQ6KL4dJ2lW0gZxh9lCj5tm99kYMCk0i57KocSKGGD4"
COMPANY_ID = "43fc8053-d32c-4d37-bf93-33046dd7215b"

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "API Rio Bonito SOS Online"})

@app.route('/create-payment', methods=['POST', 'OPTIONS'])
def create_payment():
    # Lidar com preflight CORS
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response, 200
    
    try:
        data = request.get_json()
        
        print("=== DADOS RECEBIDOS ===")
        print(f"Customer: {data.get('customer')}")
        print(f"Amount: {data.get('amount')}")
        
        # Validar dados obrigatórios
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
        
        # Preparar payload para GhostPay
        payload = {
            "paymentMethod": "PIX",
            "customer": {
                "name": customer['name'],
                "email": customer['email']
            },
            "items": [
                {
                    "title": "Doação para Rio Bonito SOS",
                    "unitPrice": amount,
                    "quantity": 1,
                    "externalRef": "doacao-ribonito"
                }
            ],
            "amount": amount,
            "description": data.get('description', 'Doação para Rio Bonito SOS'),
            "metadata": {
                "campaign": "rio-bonito-sos",
                "source": "website"
            }
        }
        
        # Adicionar CPF se fornecido
        if customer.get('document'):
            payload['customer']['document'] = customer['document']
        
        # Headers para GhostPay API
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {SECRET_KEY}',
            'X-Company-ID': COMPANY_ID
        }
        
        print("=== ENVIANDO PARA GHOSTPAY ===")
        print(f"URL: {GHOSTPAY_URL}")
        print(f"Headers Auth: Bearer {SECRET_KEY[:20]}...")  # Mostrar apenas parte do token
        print(f"Company ID: {COMPANY_ID}")
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
        elif response.status_code == 401:
            return jsonify({
                "error": True,
                "message": "ERRO 401 - Não autorizado. Verifique:",
                "details": [
                    "1. Secret Key está correta?",
                    "2. Company ID está correto?",
                    "3. A API Key está ativa?",
                    f"Resposta completa: {response.text}"
                ]
            }), 401
        else:
            return jsonify({
                "error": True,
                "message": f"Erro na API GhostPay: {response.status_code}",
                "details": response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão: {str(e)}")
        return jsonify({
            "error": True,
            "message": f"Erro de conexão: {str(e)}"
        }), 500
    except Exception as e:
        print(f"Erro interno: {str(e)}")
        return jsonify({
            "error": True,
            "message": f"Erro interno: {str(e)}"
        }), 500

@app.route('/test-ghostpay', methods=['GET'])
def test_ghostpay():
    """Rota para testar a conexão com GhostPay"""
    try:
        # Payload de teste mínimo
        test_payload = {
            "paymentMethod": "PIX",
            "customer": {
                "name": "João Silva",
                "email": "joao@teste.com"
            },
            "items": [
                {
                    "title": "Teste de Doação",
                    "unitPrice": 1000,
                    "quantity": 1,
                    "externalRef": "test-001"
                }
            ],
            "amount": 1000,
            "description": "Teste de conexão com GhostPay"
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {SECRET_KEY}',
            'X-Company-ID': COMPANY_ID
        }
        
        print("=== TESTANDO GHOSTPAY ===")
        print(f"Secret Key: {SECRET_KEY[:20]}...")
        print(f"Company ID: {COMPANY_ID}")
        
        response = requests.post(
            GHOSTPAY_URL,
            json=test_payload,
            headers=headers,
            timeout=30
        )
        
        result = {
            "status_code": response.status_code,
            "ghostpay_response": response.text,
            "credentials_check": {
                "secret_key_length": len(SECRET_KEY),
                "company_id": COMPANY_ID,
                "secret_key_prefix": SECRET_KEY[:20] + "..."
            }
        }
        
        print(f"Resultado do teste: {result}")
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": True,
            "message": f"Erro no teste: {str(e)}"
        }), 500

@app.route('/')
def home():
    return jsonify({
        "message": "API Rio Bonito SOS",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health (GET)",
            "create_payment": "/create-payment (POST)",
            "test_ghostpay": "/test-ghostpay (GET)"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)