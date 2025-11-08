from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)  # Isso resolve CORS para SEU frontend

# Configurações da API GhostPay
GHOSTPAY_URL = "https://api.ghostspaysv2.com/functions/v1/transactions"
SECRET_KEY = "sk_live_4rcXnqQ6KL4dJ2lW0gZxh9lCj5tm99kYMCk0i57KocSKGGD4"
COMPANY_ID = "43fc8053-d32c-4d37-bf93-33046dd7215b"

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
        print(f"Payload: {payload}")
        
        # Fazer requisição para GhostPay (AGORA DO BACKEND, SEM CORS!)
        response = requests.post(
            GHOSTPAY_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print("=== RESPOSTA GHOSTPAY ===")
        print(f"Status: {response.status_code}")
        print(f"Resposta: {response.text}")
        
        if response.status_code == 201:
            return jsonify(response.json()), 201
        else:
            return jsonify({
                "error": True,
                "message": f"Erro na API GhostPay: {response.status_code}",
                "details": response.text
            }), response.status_code
            
    except Exception as e:
        print(f"ERRO: {str(e)}")
        return jsonify({
            "error": True,
            "message": f"Erro interno: {str(e)}"
        }), 500

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "API funcionando!", "status": "OK"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
