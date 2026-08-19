"""Esquema inicial: wallet_usuarios, wallets, wallet_transacciones

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wallet_usuarios",
        sa.Column("id",            sa.Integer(),     primary_key=True, autoincrement=True),
        sa.Column("username",      sa.String(50),    nullable=False,   unique=True),
        sa.Column("email",         sa.String(100),   nullable=False,   unique=True),
        sa.Column("password_hash", sa.String(100),   nullable=False),
        sa.Column("nombre",        sa.String(150),   nullable=False),
        sa.Column("cedula",        sa.String(20),    nullable=False,   unique=True),
        sa.Column("activo",        sa.Boolean(),     default=True),
        sa.Column("creado_en",     sa.DateTime(timezone=True)),
    )

    op.create_table(
        "wallets",
        sa.Column("id",             sa.Integer(),       primary_key=True, autoincrement=True),
        sa.Column("usuario_id",     sa.Integer(),       sa.ForeignKey("wallet_usuarios.id"), unique=True),
        sa.Column("saldo",          sa.Numeric(18, 2),  nullable=False,  default=0),
        sa.Column("activa",         sa.Boolean(),       default=True),
        sa.Column("creado_en",      sa.DateTime(timezone=True)),
        sa.Column("actualizado_en", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "wallet_transacciones",
        sa.Column("id",             sa.Integer(),       primary_key=True, autoincrement=True),
        sa.Column("wallet_id",      sa.Integer(),       sa.ForeignKey("wallets.id"), nullable=False),
        sa.Column("tipo",           sa.String(20),      nullable=False),
        sa.Column("monto",          sa.Numeric(18, 2),  nullable=False),
        sa.Column("descripcion",    sa.String(200)),
        sa.Column("referencia",     sa.String(50)),
        sa.Column("cedula_destino", sa.String(20)),
        sa.Column("estado",         sa.String(20),      default="COMPLETADA"),
        sa.Column("creado_en",      sa.DateTime(timezone=True)),
    )

    # Índices para búsquedas frecuentes
    op.create_index("ix_transacciones_wallet_id", "wallet_transacciones", ["wallet_id"])
    op.create_index("ix_transacciones_creado_en", "wallet_transacciones", ["creado_en"])


def downgrade() -> None:
    op.drop_index("ix_transacciones_creado_en",  table_name="wallet_transacciones")
    op.drop_index("ix_transacciones_wallet_id",  table_name="wallet_transacciones")
    op.drop_table("wallet_transacciones")
    op.drop_table("wallets")
    op.drop_table("wallet_usuarios")
