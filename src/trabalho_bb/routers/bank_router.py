from flask import (
    Flask,
    jsonify,
    request,
)

from trabalho_bb.hardware.tag_reader import read_card

from trabalho_bb.services.bank_service import (
    create_account,
    authenticate_client,
    update_client_account,
    get_client_data_account,
    withdraw_client_account,
    deposit_client_account,
    delete_client_account
    )

from trabalho_bb.exceptions.exceptions import (
    ClientNotFoundError,
    PasswordNotFoundError,
    IncorrectPasswordError,
    NoFieldsToBeUpdatedError,
    MissingValueError,
    InvalidWithdrawAmountError,
    InvalidDepositAmountError,
    InsufficientBalanceError, 
    DatabaseError,
    RfidTimeoutError
)

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "API funcionando"}), 200

@app.route("/api/clients", methods=["POST"])
def register_account():
    try:
        data = request.get_json()
        if not data:
            raise MissingValueError("Há campo(s) faltante(s)")

        name = data.get("name")
        cpf = data.get("cpf")
        password = data.get("password")
        rfid = data.get("rfid")

        new_account = create_account(name, cpf, password, rfid)

        return jsonify({
            "success": True,
            "message": "Cadastro realizado com sucesso",
            "data": new_account
        }), 201

    except MissingValueError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 400

    except IncorrectPasswordError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 401

    except DatabaseError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Ocorreu um erro inesperado no sistema",
        }), 500

@app.route("/api/auth", methods=["POST"])
def login_account():
    try:
        data = request.get_json()
        if not data:
            raise MissingValueError("Há campo(s) faltante(s)")

        rfid = data.get("rfid")
        password = data.get("password")

        auth_result = authenticate_client(rfid, password)

        return jsonify({
            "success": True,
            "message": "Login realizado com sucesso",
            "data": auth_result
        }), 200

    except MissingValueError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 400

    except IncorrectPasswordError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 401

    except ClientNotFoundError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 404

    except PasswordNotFoundError as e:
            return jsonify({
                "success": False,
                "message": str(e),
            }), 404

    except DatabaseError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Ocorreu um erro inesperado no sistema",
        }), 500

@app.route("/api/clients/<id>", methods=["PATCH"])
def update_account(id):
    try:
        if not id:
            raise MissingValueError("Falha ao processar requisição")
        
        data = request.get_json()
        if not data:
            raise MissingValueError("É necessário preencher algum campo para atualizar")

        name = data.get("name", None)
        cpf = data.get("cpf", None)
        password = data.get("password", None)
        rfid = data.get("rfid", None)

        update_result = update_client_account(id, name, cpf, password, rfid)

        return jsonify({
            "success": True,
            "message": "Atualização realizada com sucesso",
            "data": update_result
        }), 200

    except NoFieldsToBeUpdatedError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 400

    except MissingValueError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 400

    except IncorrectPasswordError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 401

    except ClientNotFoundError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 404

    except DatabaseError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Ocorreu um erro inesperado no sistema",
        }), 500

@app.route("/api/clients/<id>", methods=["GET"])
def get_data_account(id):
    try:
        if not id:
            raise MissingValueError("Falha ao processar requisição")

        client_data_result = get_client_data_account(id)
        
        return jsonify({
            "success": True,
            "message": "Informações enviadas com sucesso",
            "data": client_data_result
        }), 200

    except MissingValueError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 400

    except ClientNotFoundError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 404

    except DatabaseError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Ocorreu um erro inesperado no sistema",
        }), 500

@app.route("/api/clients/<id>/withdraw", methods=["PATCH"])
def withdraw_account(id):
    try:
        if not id:
            raise MissingValueError("Falha ao processar requisição")

        data = request.get_json()
        if not data:
            raise MissingValueError("É necessário preencher o valor para sacar")

        balance = data.get("balance")
        value_result = withdraw_client_account(id, balance)
        
        return jsonify({
            "success": True,
            "message": "Saque realizado com sucesso",
            "data": value_result
        }), 200

    except InvalidWithdrawAmountError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 400

    except InsufficientBalanceError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 400

    except DatabaseError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Ocorreu um erro inesperado no sistema",
        }), 500

@app.route("/api/clients/<id>/deposit", methods=["PATCH"])
def deposit_account(id):
    try:
        if not id:
            raise MissingValueError("Falha ao processar requisição")

        data = request.get_json()
        if not data:
            raise MissingValueError("É necessário preencher o valor para depositar")

        balance = data.get("balance")
        value_result = deposit_client_account(id, balance)
        
        return jsonify({
            "success": True,
            "message": "Depósito realizado com sucesso",
            "data": value_result
        }), 200

    except InvalidDepositAmountError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 400

    except MissingValueError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 400

    except DatabaseError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Ocorreu um erro inesperado no sistema",
        }), 500

@app.route("/api/clients/<id>", methods=["DELETE"])
def delete_account(id):
    try:
        if not id:
            raise MissingValueError("Falha ao processar requisição")

        delete_client_account(id)

        return jsonify({
            "success": True,
            "message": "Exclusão da conta efetuada com sucesso",
        }), 200

    except MissingValueError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 400

    except ClientNotFoundError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 404

    except DatabaseError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Ocorreu um erro inesperado no sistema",
        }), 500

@app.route("/api/rfid", methods=["GET"])
def read_rfid_card():
    try:
        rfid_result = read_card()

        return jsonify({
            "success": True,
            "message": "Cartão lido com sucesso",
            "data": rfid_result
        }), 200

    except RfidTimeoutError as e:
        return jsonify({
            "success": False,
            "message": str(e),
        }), 408

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Ocorreu um erro inesperado no sistema",
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port= 5000, debug=True)
