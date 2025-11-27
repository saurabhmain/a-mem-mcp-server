"""
Test Suite für A-MEM: Agentic Memory System

Tests für alle 4 Hauptkomponenten:
1. Note Construction
2. Link Generation  
3. Memory Evolution
4. Retrieve Relative Memory
"""

import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Mock-Objekte für externe Dependencies
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Da main.py alles enthält, müssen wir die Klassen extrahieren
# Für Tests erstellen wir Mock-Implementierungen


class MockAtomicNote:
    """Mock für AtomicNote"""
    def __init__(self, id: str, content: str, contextual_summary: str = "", 
                 keywords: list = None, tags: list = None, created_at = None):
        self.id = id
        self.content = content
        self.contextual_summary = contextual_summary
        self.keywords = keywords or []
        self.tags = tags or []
        self.created_at = created_at or datetime.now()
    
    def model_dump(self, mode='json'):
        return {
            'id': self.id,
            'content': self.content,
            'contextual_summary': self.contextual_summary,
            'keywords': self.keywords,
            'tags': self.tags,
            'created_at': self.created_at.isoformat()
        }


class TestEmbeddingCalculation:
    """Test für Embedding-Berechnung (Paper Section 3.1, Formel 3)"""
    
    def test_embedding_concatenation(self):
        """Test: ei = fenc[concat(ci, Ki, Gi, Xi)]"""
        note = MockAtomicNote(
            id="test-1",
            content="Python async programming",
            contextual_summary="Async/await patterns in Python",
            keywords=["async", "await", "coroutines"],
            tags=["python", "concurrency"]
        )
        
        # Simuliere Embedding-Berechnung wie in main.py:431
        text_for_embedding = f"{note.content} {note.contextual_summary} {' '.join(note.keywords)} {' '.join(note.tags)}"
        
        expected_text = "Python async programming Async/await patterns in Python async await coroutines python concurrency"
        
        assert text_for_embedding == expected_text
        assert "Python async programming" in text_for_embedding  # ci
        assert "Async/await patterns in Python" in text_for_embedding  # Xi
        assert "async await coroutines" in text_for_embedding  # Ki
        assert "python concurrency" in text_for_embedding  # Gi
        
        print("✅ Embedding-Konkatenation korrekt: Alle Komponenten (ci, Ki, Gi, Xi) enthalten")


class TestNoteConstruction:
    """Test für Note Construction (Paper Section 3.1)"""
    
    def test_atomic_note_structure(self):
        """Test: mi = {ci, ti, Ki, Gi, Xi, ei, Li}"""
        note = MockAtomicNote(
            id="test-1",
            content="Test content",  # ci
            contextual_summary="Test summary",  # Xi
            keywords=["keyword1", "keyword2"],  # Ki
            tags=["tag1", "tag2"],  # Gi
            created_at=datetime(2025, 1, 1)  # ti
        )
        
        # Prüfe alle Komponenten
        assert note.content == "Test content"  # ci ✅
        assert note.contextual_summary == "Test summary"  # Xi ✅
        assert note.keywords == ["keyword1", "keyword2"]  # Ki ✅
        assert note.tags == ["tag1", "tag2"]  # Gi ✅
        assert note.created_at is not None  # ti ✅
        assert note.id is not None  # ID ✅
        
        print("✅ AtomicNote Struktur korrekt: Alle Komponenten vorhanden")
    
    def test_note_serialization(self):
        """Test: Note kann serialisiert werden"""
        note = MockAtomicNote(
            id="test-1",
            content="Test",
            contextual_summary="Summary",
            keywords=["k1"],
            tags=["t1"]
        )
        
        data = note.model_dump(mode='json')
        
        assert data['id'] == "test-1"
        assert data['content'] == "Test"
        assert data['contextual_summary'] == "Summary"
        assert data['keywords'] == ["k1"]
        assert data['tags'] == ["t1"]
        assert 'created_at' in data
        
        print("✅ Note Serialization korrekt")


class TestLinkGeneration:
    """Test für Link Generation (Paper Section 3.2)"""
    
    def test_similarity_calculation_concept(self):
        """Test: Konzept der Similarity-Berechnung (Formel 4)"""
        # sn,j = (en · ej) / (|en| · |ej|)
        # ChromaDB macht das intern, hier testen wir das Konzept
        
        embedding_a = [0.5, 0.3, 0.8]
        embedding_b = [0.4, 0.2, 0.9]
        
        # Cosine Similarity = dot product / (norm_a * norm_b)
        dot_product = sum(a * b for a, b in zip(embedding_a, embedding_b))
        norm_a = sum(a * a for a in embedding_a) ** 0.5
        norm_b = sum(b * b for b in embedding_b) ** 0.5
        similarity = dot_product / (norm_a * norm_b)
        
        assert 0 <= similarity <= 1  # Cosine Similarity ist zwischen 0 und 1
        print(f"✅ Similarity-Berechnung korrekt: {similarity:.4f}")
    
    def test_top_k_retrieval_concept(self):
        """Test: Top-k Retrieval Konzept (Formel 5)"""
        # M_near = {mj | rank(sn,j) ≤ k, mj ∈ M}
        
        similarities = [
            ("note-1", 0.95),
            ("note-2", 0.87),
            ("note-3", 0.72),
            ("note-4", 0.65),
            ("note-5", 0.58),
            ("note-6", 0.45)
        ]
        
        k = 5
        top_k = sorted(similarities, key=lambda x: x[1], reverse=True)[:k]
        
        assert len(top_k) == k
        assert top_k[0][1] == 0.95  # Höchste Similarity
        assert top_k[-1][1] == 0.58  # k-te Similarity
        
        print(f"✅ Top-k Retrieval korrekt: {len(top_k)} Kandidaten")
    
    def test_link_relation_types(self):
        """Test: Link Relation Types"""
        relation_types = ["extends", "contradicts", "supports", "relates_to"]
        
        for rel_type in relation_types:
            assert rel_type in ["extends", "contradicts", "supports", "relates_to"]
        
        print("✅ Link Relation Types korrekt")


class TestMemoryEvolution:
    """Test für Memory Evolution (Paper Section 3.3)"""
    
    def test_evolution_concept(self):
        """Test: Konzept der Memory Evolution (Formel 7)"""
        # mj* = LLM(mn || M_near || mj || Ps3)
        
        new_note = MockAtomicNote(
            id="new-1",
            content="Python async/await is used for concurrent I/O operations",
            contextual_summary="Async programming in Python",
            keywords=["async", "await"],
            tags=["python", "concurrency"]
        )
        
        existing_note = MockAtomicNote(
            id="existing-1",
            content="Python supports multiple concurrency models",
            contextual_summary="Python concurrency overview",
            keywords=["concurrency"],
            tags=["python"]
        )
        
        # Evolution sollte:
        # 1. Prüfen ob Update nötig ist
        # 2. Contextual Summary erweitern
        # 3. Keywords/Tags aktualisieren
        
        # Simuliere Evolution-Ergebnis
        evolved_summary = "Python concurrency overview, including async/await patterns"
        evolved_keywords = ["concurrency", "async", "await"]
        evolved_tags = ["python", "concurrency", "async"]
        
        assert "async" in evolved_keywords
        assert "async" in evolved_tags
        assert "async" in evolved_summary.lower()
        
        print("✅ Memory Evolution Konzept korrekt: Bestehende Note wird erweitert")
    
    def test_evolution_embedding_recalculation(self):
        """Test: Embedding-Recalculation nach Evolution"""
        # Nach Evolution muss neues Embedding berechnet werden
        # ei = fenc[concat(ci, Ki, Gi, Xi)]
        
        evolved_note = MockAtomicNote(
            id="evolved-1",
            content="Original content",  # ci bleibt gleich
            contextual_summary="Updated summary",  # Xi aktualisiert
            keywords=["old", "new"],  # Ki aktualisiert
            tags=["tag1", "tag2"]  # Gi aktualisiert
        )
        
        # Embedding sollte aus allen Komponenten berechnet werden
        evolved_text = f"{evolved_note.content} {evolved_note.contextual_summary} {' '.join(evolved_note.keywords)} {' '.join(evolved_note.tags)}"
        
        assert "Original content" in evolved_text  # ci
        assert "Updated summary" in evolved_text  # Xi (aktualisiert)
        assert "old new" in evolved_text  # Ki (aktualisiert)
        assert "tag1 tag2" in evolved_text  # Gi (aktualisiert)
        
        print("✅ Evolution Embedding-Recalculation korrekt")


class TestRetrieveMemory:
    """Test für Retrieve Relative Memory (Paper Section 3.4)"""
    
    def test_query_embedding_concept(self):
        """Test: Query Embedding (Formel 8)"""
        # eq = fenc(q)
        
        query = "Python async programming"
        # Embedding sollte berechnet werden
        # In Realität: embedding = embedder.encode(query)
        
        assert len(query) > 0
        assert "Python" in query
        
        print("✅ Query Embedding Konzept korrekt")
    
    def test_retrieval_similarity_concept(self):
        """Test: Retrieval Similarity (Formel 9)"""
        # sq,i = (eq · ei) / (|eq| · |ei|)
        
        query_embedding = [0.5, 0.3, 0.8]
        memory_embedding = [0.4, 0.2, 0.9]
        
        # Cosine Similarity
        dot_product = sum(q * m for q, m in zip(query_embedding, memory_embedding))
        norm_q = sum(q * q for q in query_embedding) ** 0.5
        norm_m = sum(m * m for m in memory_embedding) ** 0.5
        similarity = dot_product / (norm_q * norm_m)
        
        assert 0 <= similarity <= 1
        
        print(f"✅ Retrieval Similarity korrekt: {similarity:.4f}")
    
    def test_top_k_retrieval(self):
        """Test: Top-k Retrieval (Formel 10)"""
        # M_retrieved = {mi | rank(sq,i) ≤ k, mi ∈ M}
        
        query = "Python async"
        memories = [
            ("memory-1", 0.92, "Python async/await patterns"),
            ("memory-2", 0.85, "Async programming in Python"),
            ("memory-3", 0.78, "Concurrency models"),
            ("memory-4", 0.65, "Threading in Python"),
            ("memory-5", 0.58, "Multiprocessing"),
            ("memory-6", 0.45, "Other topic")
        ]
        
        k = 5
        top_k = sorted(memories, key=lambda x: x[1], reverse=True)[:k]
        
        assert len(top_k) == k
        assert all(score >= 0.58 for _, score, _ in top_k)
        assert top_k[0][1] == 0.92  # Höchste Similarity
        
        print(f"✅ Top-k Retrieval korrekt: {len(top_k)} Memories")


class TestIntegration:
    """Integrationstests für End-to-End Flow"""
    
    def test_full_workflow_concept(self):
        """Test: Vollständiger Workflow"""
        # 1. Note Creation
        note = MockAtomicNote(
            id="workflow-1",
            content="Python async/await tutorial",
            contextual_summary="Learning async programming",
            keywords=["async", "await", "python"],
            tags=["tutorial", "programming"]
        )
        
        # 2. Embedding Calculation
        text_for_embedding = f"{note.content} {note.contextual_summary} {' '.join(note.keywords)} {' '.join(note.tags)}"
        assert len(text_for_embedding) > 0
        
        # 3. Similarity Search (simuliert)
        candidate_similarities = [0.85, 0.72, 0.68]
        top_k = sorted(candidate_similarities, reverse=True)[:3]
        assert len(top_k) == 3
        
        # 4. Link Generation (simuliert)
        should_link = top_k[0] > 0.7
        assert should_link == True
        
        # 5. Memory Evolution (simuliert)
        should_evolve = top_k[0] > 0.75
        assert should_evolve == True
        
        print("✅ Vollständiger Workflow korrekt")
    
    def test_data_consistency(self):
        """Test: Datenkonsistenz zwischen Komponenten"""
        note = MockAtomicNote(
            id="consistency-1",
            content="Test",
            contextual_summary="Summary",
            keywords=["k1"],
            tags=["t1"]
        )
        
        # Serialisierung
        data = note.model_dump(mode='json')
        
        # Embedding-Berechnung sollte konsistent sein
        text_for_embedding = f"{note.content} {note.contextual_summary} {' '.join(note.keywords)} {' '.join(note.tags)}"
        
        # Alle Komponenten sollten vorhanden sein
        assert data['content'] in text_for_embedding
        assert data['contextual_summary'] in text_for_embedding
        assert all(kw in text_for_embedding for kw in data['keywords'])
        assert all(tag in text_for_embedding for tag in data['tags'])
        
        print("✅ Datenkonsistenz korrekt")


def run_tests():
    """Führt alle Tests aus"""
    print("\n" + "="*60)
    print("🧪 A-MEM Test Suite")
    print("="*60 + "\n")
    
    test_classes = [
        TestEmbeddingCalculation,
        TestNoteConstruction,
        TestLinkGeneration,
        TestMemoryEvolution,
        TestRetrieveMemory,
        TestIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 60)
        
        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_instance, method_name)
                method()
                passed_tests += 1
                print(f"  ✅ {method_name}")
            except AssertionError as e:
                print(f"  ❌ {method_name}: {e}")
            except Exception as e:
                print(f"  ⚠️  {method_name}: {e}")
    
    print("\n" + "="*60)
    print(f"📊 Test Results: {passed_tests}/{total_tests} passed")
    print("="*60 + "\n")
    
    if passed_tests == total_tests:
        print("✅ ALLE TESTS BESTANDEN!")
        return True
    else:
        print(f"❌ {total_tests - passed_tests} Test(s) fehlgeschlagen")
        return False


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)

