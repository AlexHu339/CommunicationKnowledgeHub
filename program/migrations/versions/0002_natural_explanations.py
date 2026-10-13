"""natural explanations and merged-card aliases"""

from alembic import op
import sqlalchemy as sa


revision = "0002_natural_explanations"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("knowledge_cards", sa.Column("explanation", sa.Text(), nullable=False, server_default=""))
    op.add_column("knowledge_cards", sa.Column("sections_json", sa.Text(), nullable=False, server_default="[]"))
    op.add_column("knowledge_cards", sa.Column("accuracy_notes_json", sa.Text(), nullable=False, server_default="[]"))
    op.create_table(
        "knowledge_card_aliases",
        sa.Column("alias_id", sa.String(length=80), primary_key=True),
        sa.Column("canonical_id", sa.String(length=80), sa.ForeignKey("knowledge_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_knowledge_card_aliases_canonical_id", "knowledge_card_aliases", ["canonical_id"])


def downgrade():
    op.drop_index("ix_knowledge_card_aliases_canonical_id", table_name="knowledge_card_aliases")
    op.drop_table("knowledge_card_aliases")
    op.drop_column("knowledge_cards", "accuracy_notes_json")
    op.drop_column("knowledge_cards", "sections_json")
    op.drop_column("knowledge_cards", "explanation")
