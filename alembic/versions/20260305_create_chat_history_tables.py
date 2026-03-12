"""create chat history tables

Revision ID: chat_history_001
Revises: page_quiz_001
Create Date: 2026-03-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "chat_history_001"
down_revision = "page_quiz_001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_message_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "session_id", name="uq_chat_sessions_user_session"),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("ix_chat_sessions_session_id", "chat_sessions", ["session_id"])
    op.create_index(
        "idx_chat_sessions_user_last_message_at",
        "chat_sessions",
        ["user_id", "last_message_at"],
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("chat_session_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_messages_role"),
        sa.ForeignKeyConstraint(["chat_session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_chat_messages_chat_session_id", "chat_messages", ["chat_session_id"])
    op.create_index("idx_chat_messages_session_id_id", "chat_messages", ["chat_session_id", "id"])


def downgrade():
    op.drop_index("idx_chat_messages_session_id_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_chat_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("idx_chat_sessions_user_last_message_at", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_session_id", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
