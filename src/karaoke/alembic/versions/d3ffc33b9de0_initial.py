"""initial

Revision ID: d3ffc33b9de0
Revises: 
Create Date: 2023-08-15 16:49:02.399550

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d3ffc33b9de0"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "karaoke_session_song",
        sa.Column(
            "current_song", sa.Boolean(), nullable=False, server_default=False
        ),
    )
    op.add_column(
        "karaoke_session_song",
        sa.Column(
            "snooze_ttl", sa.Integer(), nullable=False, server_default=0
        ),
    )
    op.add_column(
        "karaoke_session_user",
        sa.Column(
            "stepped_out", sa.Boolean(), nullable=False, server_default=False
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("karaoke_session_user", "stepped_out")
    op.drop_column("karaoke_session_song", "snooze_ttl")
    op.drop_column("karaoke_session_song", "current_song")
    # ### end Alembic commands ###
