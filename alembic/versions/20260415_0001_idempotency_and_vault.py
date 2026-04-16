"""Add idempotency_key to orders, vault_secrets table, widen risk_ratio.

Revision ID: 20260415_0001
Revises: 11b60e25cc6b
Create Date: 2026-04-15

Fixes:
- H4: idempotency_key (+ unique index per session) on orders
- C3: vault_secrets table for persistent encrypted credential storage
- H5: risk_ratio widened to Numeric(18, 8) so it stays a Decimal
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260415_0001"
down_revision: Union[str, None] = "11b60e25cc6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- orders.idempotency_key ------------------------------------------------
    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("idempotency_key", sa.String(128), nullable=True))
        # Widen risk_ratio from Float to Numeric(18, 8) to keep it as Decimal.
        batch.alter_column(
            "risk_ratio",
            type_=sa.Numeric(18, 8),
            existing_nullable=True,
        )

    op.create_index(
        "ix_orders_idempotency_key",
        "orders",
        ["idempotency_key"],
    )
    # Partial unique index — only rows with a non-NULL idempotency_key must be
    # globally unique per session. Use plain unique index on SQLite.
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute(
            """
            CREATE UNIQUE INDEX uq_orders_session_idempotency_key
                ON orders (session_id, idempotency_key)
                WHERE idempotency_key IS NOT NULL
            """
        )
    else:
        op.create_index(
            "uq_orders_session_idempotency_key",
            "orders",
            ["session_id", "idempotency_key"],
            unique=True,
        )

    # --- vault_secrets --------------------------------------------------------
    op.create_table(
        "vault_secrets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("ciphertext", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("vault_secrets")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS uq_orders_session_idempotency_key")
    else:
        op.drop_index("uq_orders_session_idempotency_key", table_name="orders")

    op.drop_index("ix_orders_idempotency_key", table_name="orders")

    with op.batch_alter_table("orders") as batch:
        batch.alter_column("risk_ratio", type_=sa.Float)
        batch.drop_column("idempotency_key")
