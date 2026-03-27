"""create lesson page quiz tables

Revision ID: page_quiz_001
Revises: embeddings_001
Create Date: 2026-02-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'page_quiz_001'
down_revision = 'embeddings_001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'lesson_page_quiz_questions',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('lesson_content_id', sa.BigInteger(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('order_position', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['lesson_content_id'], ['lesson_content.id'], ondelete='CASCADE'),
    )
    op.create_index(
        'idx_lesson_page_quiz_questions_lesson_content_id',
        'lesson_page_quiz_questions',
        ['lesson_content_id'],
    )

    op.create_table(
        'lesson_page_quiz_choices',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('question_id', sa.BigInteger(), nullable=False),
        sa.Column('choice_key', sa.Text(), nullable=False),
        sa.Column('choice_text', sa.Text(), nullable=False),
        sa.Column('order_position', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_correct', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['question_id'], ['lesson_page_quiz_questions.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_lesson_page_quiz_choices_question_id', 'lesson_page_quiz_choices', ['question_id'])
    op.create_unique_constraint(
        'uq_lesson_page_quiz_choices_question_choice_key',
        'lesson_page_quiz_choices',
        ['question_id', 'choice_key'],
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_lesson_page_quiz_choices_one_correct
        ON lesson_page_quiz_choices (question_id)
        WHERE is_correct = true
        """
    )

    op.create_table(
        'lesson_page_quiz_attempts',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('lesson_content_id', sa.BigInteger(), nullable=False),
        sa.Column('question_id', sa.BigInteger(), nullable=False),
        sa.Column('selected_choice_id', sa.BigInteger(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('answered_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['lesson_content_id'], ['lesson_content.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['lesson_page_quiz_questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['selected_choice_id'], ['lesson_page_quiz_choices.id']),
    )
    op.create_index('idx_lesson_page_quiz_attempts_user_id', 'lesson_page_quiz_attempts', ['user_id'])
    op.create_index('idx_lesson_page_quiz_attempts_question_id', 'lesson_page_quiz_attempts', ['question_id'])
    op.create_index('idx_lesson_page_quiz_attempts_lesson_content_id', 'lesson_page_quiz_attempts', ['lesson_content_id'])


def downgrade():
    op.drop_index('idx_lesson_page_quiz_attempts_lesson_content_id', table_name='lesson_page_quiz_attempts')
    op.drop_index('idx_lesson_page_quiz_attempts_question_id', table_name='lesson_page_quiz_attempts')
    op.drop_index('idx_lesson_page_quiz_attempts_user_id', table_name='lesson_page_quiz_attempts')
    op.drop_table('lesson_page_quiz_attempts')

    op.execute('DROP INDEX IF EXISTS uq_lesson_page_quiz_choices_one_correct')
    op.drop_constraint('uq_lesson_page_quiz_choices_question_choice_key', 'lesson_page_quiz_choices', type_='unique')
    op.drop_index('idx_lesson_page_quiz_choices_question_id', table_name='lesson_page_quiz_choices')
    op.drop_table('lesson_page_quiz_choices')

    op.drop_index('idx_lesson_page_quiz_questions_lesson_content_id', table_name='lesson_page_quiz_questions')
    op.drop_table('lesson_page_quiz_questions')
