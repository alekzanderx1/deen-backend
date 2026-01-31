"""
Unit tests for EmbeddingService with lesson content-based chunk embeddings.

Tests cover:
- Content hashing
- Embedding generation (single and batch)
- Note embedding storage
- Lesson chunk embedding storage (from lesson_content rows)
- Similarity search (notes compared against lesson content embeddings)
- Signal quality calculation
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from services.embedding_service import EmbeddingService
from db.models.embeddings import NoteEmbedding, LessonChunkEmbedding
from db.models.lesson_content import LessonContent


# Mock data fixtures
@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = Mock(spec=Session)
    db.query = Mock(return_value=Mock())
    db.add = Mock()
    db.commit = Mock()
    db.execute = Mock()
    return db


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client"""
    with patch('services.embedding_service.OpenAI') as mock_openai:
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock embedding response
        mock_embedding_response = Mock()
        mock_embedding_data = Mock()
        mock_embedding_data.embedding = [0.1] * 1536  # 1536 dimensions
        mock_embedding_response.data = [mock_embedding_data]
        mock_client.embeddings.create.return_value = mock_embedding_response

        yield mock_client


@pytest.fixture
def embedding_service(mock_db, mock_openai_client):
    """Create an EmbeddingService instance with mocks"""
    with patch('services.embedding_service.OpenAI') as mock_openai:
        mock_openai.return_value = mock_openai_client
        service = EmbeddingService(mock_db)
        service.client = mock_openai_client
        return service


@pytest.fixture
def sample_notes():
    """Create sample note data"""
    return [
        {
            "id": "note1",
            "content": "User struggles with Arabic pronunciation",
            "confidence": 0.8,
            "tags": ["arabic", "pronunciation"]
        },
        {
            "id": "note2",
            "content": "Interested in Tajweed rules",
            "confidence": 0.9,
            "tags": ["tajweed", "quran"]
        }
    ]


@pytest.fixture
def sample_lesson_content():
    """Create sample lesson content data"""
    content1 = Mock(spec=LessonContent)
    content1.id = 1
    content1.lesson_id = 100
    content1.order_position = 0
    content1.title = "Introduction to Tajweed"
    content1.content_body = "Tajweed is the art of reciting the Quran with proper pronunciation."

    content2 = Mock(spec=LessonContent)
    content2.id = 2
    content2.lesson_id = 100
    content2.order_position = 1
    content2.title = "Makharij (Points of Articulation)"
    content2.content_body = "Makharij refers to the places where sounds originate in the mouth and throat."

    return [content1, content2]


# Test: Content Hashing
class TestContentHashing:
    """Test content hashing functionality"""

    def test_compute_content_hash_consistent(self, embedding_service):
        """Test that same content produces same hash"""
        content = "Test content for hashing"

        hash1 = embedding_service.compute_content_hash(content)
        hash2 = embedding_service.compute_content_hash(content)

        assert hash1 == hash2

    def test_compute_content_hash_different_content(self, embedding_service):
        """Test that different content produces different hashes"""
        content1 = "First content"
        content2 = "Second content"

        hash1 = embedding_service.compute_content_hash(content1)
        hash2 = embedding_service.compute_content_hash(content2)

        assert hash1 != hash2

    def test_compute_content_hash_format(self, embedding_service):
        """Test hash is SHA256 format (64 hex characters)"""
        content = "Test content"

        hash_result = embedding_service.compute_content_hash(content)

        assert len(hash_result) == 64
        assert all(c in '0123456789abcdef' for c in hash_result)


# Test: Embedding Generation
class TestEmbeddingGeneration:
    """Test embedding generation functionality"""

    def test_generate_embedding_single(self, embedding_service, mock_openai_client):
        """Test generating a single embedding"""
        text = "Test text for embedding"

        embedding = embedding_service.generate_embedding(text)

        assert len(embedding) == 1536
        mock_openai_client.embeddings.create.assert_called_once()

    def test_generate_embeddings_batch(self, embedding_service, mock_openai_client):
        """Test generating embeddings in batch"""
        texts = ["Text one", "Text two", "Text three"]

        # Mock batch response
        mock_batch_response = Mock()
        mock_batch_response.data = [Mock(embedding=[0.1] * 1536) for _ in texts]
        mock_openai_client.embeddings.create.return_value = mock_batch_response

        embeddings = embedding_service.generate_embeddings_batch(texts)

        assert len(embeddings) == 3
        assert all(len(e) == 1536 for e in embeddings)

    def test_generate_embeddings_batch_empty(self, embedding_service):
        """Test generating embeddings with empty list"""
        embeddings = embedding_service.generate_embeddings_batch([])

        assert embeddings == []


# Test: Note Embedding Storage
class TestNoteEmbeddingStorage:
    """Test note embedding storage functionality"""

    def test_store_note_embedding_new(self, embedding_service, mock_db, mock_openai_client):
        """Test storing a new note embedding"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = embedding_service.store_note_embedding(
            user_id="user123",
            note_id="note1",
            note_type="learning_notes",
            content="Test content"
        )

        mock_db.add.assert_called_once()
        assert result.user_id == "user123"
        assert result.note_id == "note1"

    def test_store_note_embedding_existing_unchanged(self, embedding_service, mock_db):
        """Test storing when existing embedding with same content hash"""
        existing = Mock(spec=NoteEmbedding)
        existing.content_hash = embedding_service.compute_content_hash("Test content")
        mock_db.query.return_value.filter.return_value.first.return_value = existing

        result = embedding_service.store_note_embedding(
            user_id="user123",
            note_id="note1",
            note_type="learning_notes",
            content="Test content"
        )

        # Should return existing without regenerating
        assert result == existing
        mock_db.add.assert_not_called()

    def test_store_note_embedding_existing_changed(self, embedding_service, mock_db, mock_openai_client):
        """Test storing when existing embedding with different content hash"""
        existing = Mock(spec=NoteEmbedding)
        existing.content_hash = "old_hash_value"
        mock_db.query.return_value.filter.return_value.first.return_value = existing

        result = embedding_service.store_note_embedding(
            user_id="user123",
            note_id="note1",
            note_type="learning_notes",
            content="New content"
        )

        # Should update existing
        assert result == existing
        assert existing.content_hash != "old_hash_value"


# Test: Lesson Chunk Embedding Storage (using lesson_content)
class TestLessonChunkEmbeddingStorage:
    """Test lesson chunk embedding storage from lesson_content rows"""

    def test_store_lesson_chunk_embeddings_new(
        self, embedding_service, mock_db, mock_openai_client, sample_lesson_content
    ):
        """Test storing new lesson chunk embeddings from lesson_content"""
        # Mock no existing chunks
        mock_db.query.return_value.filter.return_value.all.return_value = []
        # Mock lesson content query
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = sample_lesson_content

        # Mock batch embedding response for 2 content rows
        mock_batch_response = Mock()
        mock_batch_response.data = [Mock(embedding=[0.1] * 1536) for _ in sample_lesson_content]
        mock_openai_client.embeddings.create.return_value = mock_batch_response

        result = embedding_service.store_lesson_chunk_embeddings(lesson_id=100)

        # Should create 2 chunks (one per lesson_content row)
        assert len(result) == 2
        assert mock_db.add.call_count == 2

    def test_store_lesson_chunk_embeddings_no_content(self, embedding_service, mock_db):
        """Test storing when lesson has no content rows"""
        # Mock no lesson content
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = embedding_service.store_lesson_chunk_embeddings(lesson_id=100)

        # Should return empty list
        assert result == []
        mock_db.add.assert_not_called()

    def test_store_lesson_chunk_embeddings_existing_unchanged(
        self, embedding_service, mock_db, sample_lesson_content
    ):
        """Test storing when existing chunks with same content hash"""
        # First call for existing chunks
        existing_chunk = Mock(spec=LessonChunkEmbedding)
        combined = embedding_service._combine_lesson_content_for_hash(sample_lesson_content)
        existing_chunk.content_hash = embedding_service.compute_content_hash(combined)

        # Mock the query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query

        # Mock lesson content query (first query)
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value.all.return_value = sample_lesson_content
        mock_filter.all.return_value = [existing_chunk]

        result = embedding_service.store_lesson_chunk_embeddings(lesson_id=100)

        # Should return existing chunks without regenerating
        assert result == [existing_chunk]

    def test_format_lesson_content_for_embedding(self, embedding_service):
        """Test lesson content formatting"""
        content = Mock(spec=LessonContent)
        content.title = "Test Section"
        content.content_body = "This is the content body."

        result = embedding_service._format_lesson_content_for_embedding(content)

        assert "Section: Test Section" in result
        assert "This is the content body." in result

    def test_format_lesson_content_for_embedding_empty(self, embedding_service):
        """Test lesson content formatting with empty values"""
        content = Mock(spec=LessonContent)
        content.title = None
        content.content_body = None

        result = embedding_service._format_lesson_content_for_embedding(content)

        assert result == ""


# Test: Embedding Existence Checks
class TestEmbeddingExistenceChecks:
    """Test embedding existence check functionality"""

    def test_has_note_embeddings_true(self, embedding_service, mock_db):
        """Test checking for note embeddings when they exist"""
        mock_db.query.return_value.filter.return_value.count.return_value = 5

        result = embedding_service.has_note_embeddings("user123")

        assert result is True

    def test_has_note_embeddings_false(self, embedding_service, mock_db):
        """Test checking for note embeddings when none exist"""
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        result = embedding_service.has_note_embeddings("user123")

        assert result is False

    def test_has_lesson_chunks_true(self, embedding_service, mock_db):
        """Test checking for lesson chunks when they exist"""
        mock_db.query.return_value.filter.return_value.count.return_value = 3

        result = embedding_service.has_lesson_chunks(1)

        assert result is True

    def test_has_lesson_chunks_false(self, embedding_service, mock_db):
        """Test checking for lesson chunks when none exist"""
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        result = embedding_service.has_lesson_chunks(1)

        assert result is False

    def test_get_lesson_chunk_count(self, embedding_service, mock_db):
        """Test getting count of lesson chunks"""
        mock_db.query.return_value.filter.return_value.count.return_value = 5

        result = embedding_service.get_lesson_chunk_count(1)

        assert result == 5


# Test: Similarity Search
class TestSimilaritySearch:
    """Test similarity search functionality with lesson chunks"""

    def test_find_similar_notes_no_lesson_chunks(self, embedding_service, mock_db):
        """Test similarity search when lesson has no chunks"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = embedding_service.find_similar_notes_to_lesson(
            user_id="user123",
            lesson_id=1
        )

        assert result == []

    def test_find_similar_notes_with_chunks_and_results(self, embedding_service, mock_db):
        """Test similarity search with lesson chunks and results"""
        # Mock lesson chunks
        chunk1 = Mock(spec=LessonChunkEmbedding)
        chunk1.embedding = [0.1] * 1536
        chunk2 = Mock(spec=LessonChunkEmbedding)
        chunk2.embedding = [0.2] * 1536

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [chunk1, chunk2]

        # Mock similarity search results
        mock_result = [
            ("note1", "learning_notes", 0.85),
            ("note2", "interest_notes", 0.75),
        ]
        mock_db.execute.return_value = mock_result

        result = embedding_service.find_similar_notes_to_lesson(
            user_id="user123",
            lesson_id=1,
            threshold=0.4
        )

        assert len(result) == 2
        assert result[0][0] == "note1"
        assert result[0][2] == 0.85


# Test: Signal Quality Calculation
class TestSignalQualityCalculation:
    """Test signal quality calculation functionality"""

    def test_calculate_signal_quality_empty(self, embedding_service):
        """Test signal quality with no filtered notes"""
        result = embedding_service.calculate_signal_quality([])

        assert result == 0.0

    def test_calculate_signal_quality_single_note(self, embedding_service):
        """Test signal quality with single note"""
        filtered_notes = [("note1", "learning_notes", 0.75)]

        result = embedding_service.calculate_signal_quality(filtered_notes)

        assert result == 0.75

    def test_calculate_signal_quality_multiple_notes(self, embedding_service):
        """Test signal quality with multiple notes"""
        filtered_notes = [
            ("note1", "learning_notes", 0.8),
            ("note2", "interest_notes", 0.6),
            ("note3", "knowledge_notes", 0.7),
        ]

        result = embedding_service.calculate_signal_quality(filtered_notes)

        # Average of 0.8, 0.6, 0.7 = 0.7
        assert result == pytest.approx(0.7, rel=0.01)


# Test: Batch Operations
class TestBatchOperations:
    """Test batch embedding operations"""

    def test_store_note_embeddings_batch_empty(self, embedding_service, mock_db):
        """Test batch storage with empty notes"""
        result = embedding_service.store_note_embeddings_batch(
            user_id="user123",
            notes=[],
            note_type="learning_notes"
        )

        assert result == []

    def test_store_note_embeddings_batch_new_notes(
        self, embedding_service, mock_db, mock_openai_client, sample_notes
    ):
        """Test batch storage with new notes"""
        # Mock no existing embeddings
        mock_db.query.return_value.filter.return_value.all.return_value = []

        # Mock batch embedding generation
        mock_batch_response = Mock()
        mock_batch_response.data = [Mock(embedding=[0.1] * 1536) for _ in sample_notes]
        mock_openai_client.embeddings.create.return_value = mock_batch_response

        result = embedding_service.store_note_embeddings_batch(
            user_id="user123",
            notes=sample_notes,
            note_type="learning_notes"
        )

        assert len(result) == 2


# Test: Delete Operations
class TestDeleteOperations:
    """Test embedding deletion functionality"""

    def test_delete_note_embedding(self, embedding_service, mock_db):
        """Test deleting a note embedding"""
        mock_db.query.return_value.filter.return_value.delete.return_value = 1

        result = embedding_service.delete_note_embedding(
            user_id="user123",
            note_id="note1"
        )

        assert result is True

    def test_delete_note_embedding_not_found(self, embedding_service, mock_db):
        """Test deleting non-existent note embedding"""
        mock_db.query.return_value.filter.return_value.delete.return_value = 0

        result = embedding_service.delete_note_embedding(
            user_id="user123",
            note_id="nonexistent"
        )

        assert result is False

    def test_delete_user_embeddings(self, embedding_service, mock_db):
        """Test deleting all embeddings for a user"""
        mock_db.query.return_value.filter.return_value.delete.return_value = 10

        result = embedding_service.delete_user_embeddings("user123")

        assert result == 10

    def test_delete_lesson_chunks(self, embedding_service, mock_db):
        """Test deleting all chunks for a lesson"""
        mock_db.query.return_value.filter.return_value.delete.return_value = 5

        result = embedding_service.delete_lesson_chunks(1)

        assert result == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
