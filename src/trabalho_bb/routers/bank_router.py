from flask import (
    Flask,
    jsonify,
    request,
)
from ..services.bank_service import authenticate_client
from ..exceptions.exceptions import (
    ClientNotFoundError,
    PasswordNotFoundError,
    IncorrectPasswordError,
    MissingValueError,
    NoFieldsToBeUpdated,
    InsufficientBalanceError, 
    DatabaseError, 
)

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "API funcionando"}), 200

@app.route("/auth", methods=["POST"])
def login():
    try:
        data = request.get_json()
        if not data:
            raise MissingValueError("RFID e senha inválidos")

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port= 5000, debug=True)