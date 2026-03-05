"""전문 검색용 search_vector 컬럼, GIN 인덱스, tsvector 트리거, pg_trgm 확장 추가.

Revision ID: 0001
Revises:
Create Date: 2026-03-05
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """마이그레이션 적용.

    1. pg_trgm 확장 생성
    2. tasks.search_vector 컬럼 추가 + GIN 인덱스
    3. tasks.title, tasks.description trigram GIN 인덱스
    4. tasks tsvector 트리거
    5. task_comments.search_vector 컬럼 추가 + GIN 인덱스
    6. task_comments.content trigram GIN 인덱스
    7. task_comments tsvector 트리거
    """
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # tasks: search_vector 컬럼 추가
    op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS search_vector tsvector")

    # tasks: tsvector GIN 인덱스
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_search ON tasks USING GIN (search_vector)"
    )

    # tasks: title trigram GIN 인덱스
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_trigram_title ON tasks USING GIN (title gin_trgm_ops)"
    )

    # tasks: description trigram GIN 인덱스
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_trigram_desc ON tasks USING GIN (description gin_trgm_ops)"
    )

    # tasks: tsvector 트리거
    op.execute(
        """
        CREATE OR REPLACE TRIGGER tasks_search_update
        BEFORE INSERT OR UPDATE ON tasks
        FOR EACH ROW EXECUTE FUNCTION
        tsvector_update_trigger(search_vector, 'pg_catalog.simple', title, description)
        """
    )

    # 기존 행 search_vector 초기화
    op.execute(
        "UPDATE tasks SET search_vector = to_tsvector('pg_catalog.simple', coalesce(title,'') || ' ' || coalesce(description,''))"
    )

    # task_comments: search_vector 컬럼 추가
    op.execute(
        "ALTER TABLE task_comments ADD COLUMN IF NOT EXISTS search_vector tsvector"
    )

    # task_comments: tsvector GIN 인덱스
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_comments_search ON task_comments USING GIN (search_vector)"
    )

    # task_comments: content trigram GIN 인덱스
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_comments_trigram ON task_comments USING GIN (content gin_trgm_ops)"
    )

    # task_comments: tsvector 트리거
    op.execute(
        """
        CREATE OR REPLACE TRIGGER comments_search_update
        BEFORE INSERT OR UPDATE ON task_comments
        FOR EACH ROW EXECUTE FUNCTION
        tsvector_update_trigger(search_vector, 'pg_catalog.simple', content)
        """
    )

    # 기존 행 search_vector 초기화
    op.execute(
        "UPDATE task_comments SET search_vector = to_tsvector('pg_catalog.simple', coalesce(content,''))"
    )


def downgrade() -> None:
    """마이그레이션 롤백.

    트리거, 인덱스, 컬럼을 역순으로 제거합니다.
    """
    op.execute("DROP TRIGGER IF EXISTS comments_search_update ON task_comments")
    op.execute("DROP INDEX IF EXISTS idx_comments_trigram")
    op.execute("DROP INDEX IF EXISTS idx_comments_search")
    op.execute("ALTER TABLE task_comments DROP COLUMN IF EXISTS search_vector")

    op.execute("DROP TRIGGER IF EXISTS tasks_search_update ON tasks")
    op.execute("DROP INDEX IF EXISTS idx_tasks_trigram_desc")
    op.execute("DROP INDEX IF EXISTS idx_tasks_trigram_title")
    op.execute("DROP INDEX IF EXISTS idx_tasks_search")
    op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS search_vector")
