from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Municipio(Base):
    __tablename__ = 'municipios'
    id: Mapped[int] = mapped_column(primary_key=True)
    nome_original: Mapped[str]
    nome_exibicao: Mapped[str] = mapped_column(unique=True)
    ativo: Mapped[bool] = mapped_column(default=True)


class Periodo(Base):
    __tablename__ = 'periodos'
    __table_args__ = (UniqueConstraint('ano', 'mes'), CheckConstraint('mes BETWEEN 1 AND 12'))
    id: Mapped[int] = mapped_column(primary_key=True)
    ano: Mapped[int]
    mes: Mapped[int]
    importado_em: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    arquivo_nome: Mapped[str]


class Posicao(Base):
    __tablename__ = 'posicoes'
    __table_args__ = (UniqueConstraint('municipio_id', 'periodo_id'), CheckConstraint('posicao > 0'))
    id: Mapped[int] = mapped_column(primary_key=True)
    municipio_id: Mapped[int] = mapped_column(ForeignKey('municipios.id'), index=True)
    periodo_id: Mapped[int] = mapped_column(ForeignKey('periodos.id'), index=True)
    posicao: Mapped[int]


class ImportacaoPendente(Base):
    """Arquivo validado, guardado temporariamente para confirmação única."""
    __tablename__ = 'importacoes_pendentes'
    token: Mapped[str] = mapped_column(primary_key=True)
    arquivo_nome: Mapped[str]
    ano: Mapped[int]
    mes: Mapped[int]
    conteudo: Mapped[bytes]
    expira_em: Mapped[int]
