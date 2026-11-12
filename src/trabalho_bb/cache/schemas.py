from dataclasses import dataclass


@dataclass(frozen=True)
class ClientData:
    id: str
    name: str
    cpf: str
    rfid: str
    balance: float