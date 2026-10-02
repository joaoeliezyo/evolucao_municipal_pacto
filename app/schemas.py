from pydantic import BaseModel


class ImportResult(BaseModel):
    status: str
    arquivo: str
    ano: int
    quantidade: int
    meses: list[int]
    competencias_existentes: list[int]
