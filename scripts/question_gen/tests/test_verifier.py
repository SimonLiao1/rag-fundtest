import unittest
from unittest.mock import MagicMock, patch
from scripts.question_gen.verifier import RAGVerifier
from scripts.question_gen.models import QuestionCandidate, KnowledgePoint, QuestionOptions

class TestVerifier(unittest.TestCase):
    
    @patch('scripts.question_gen.verifier.FundRAG') # Mock the RAG class import
    def test_verify_pass(self, MockFundRAG):
        # Setup RAG mock
        mock_rag = MockFundRAG.return_value
        mock_rag.query.return_value = {"retrieved_docs": [{"metadata": {"book": "B1"}}]}
        mock_rag.format_context.return_value = "Context"
        mock_rag.std_llm = MagicMock()
        
        verifier = RAGVerifier(rag_system=mock_rag)
        
        # Setup LLM verification response
        mock_msg = MagicMock()
        mock_msg.content = '{"status": "Pass", "score": 0.95, "reason": "Good"}'
        verifier.chain = MagicMock() # Mock the internal chain
        verifier.chain.invoke.return_value = mock_msg
        
        # Input
        kp = KnowledgePoint(summary="S", category="C", key_facts=["F"], distractor_ideas=["D"], source_chunk_id="ID")
        candidate = QuestionCandidate(
            question_text="Q", options=QuestionOptions(A="1",B="2",C="3",D="4"),
            correct_answer="A", question_type="Fact", knowledge_point=kp
        )
        
        result = verifier.verify(candidate)
        
        self.assertEqual(result.status, "Verified")
        self.assertEqual(result.verification_score, 0.95)
        self.assertEqual(result.source_metadata, {"book": "B1"})

if __name__ == '__main__':
    unittest.main()
