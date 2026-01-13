import unittest
from unittest.mock import MagicMock, patch
import json
from scripts.question_gen.generator import QuestionGenerator
from scripts.question_gen.models import KnowledgePoint, QuestionCandidate

class TestGenerator(unittest.TestCase):
    
    @patch('scripts.question_gen.generator.ChatOpenAI')
    def test_generate_success(self, MockChat):
        generator = QuestionGenerator()
        
        # Mock prompt chain
        # We need to mock the `invoke` method of the chain created inside generate()
        # Since the chain is created dynamically (prompt | llm), we can mock the llm.invoke
        # because (prompt | llm).invoke calls llm.invoke with formatted string/messages.
        
        mock_response = MagicMock()
        mock_response.content = """
        {
            "question_text": "What is X?",
            "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
            "correct_answer": "A",
            "explanation": "Because."
        }
        """
        generator.llm.invoke = MagicMock(return_value=mock_response)
        
        kp = KnowledgePoint(
            summary="S", category="C", key_facts=["F"], 
            distractor_ideas=["D"], source_chunk_id="ID"
        )
        
        candidate = generator.generate(kp, "Fact")
        
        self.assertIsInstance(candidate, QuestionCandidate)
        self.assertEqual(candidate.question_text, "What is X?")
        self.assertEqual(candidate.correct_answer, "A")
        
    def test_generate_invalid_json(self):
        generator = QuestionGenerator()
        mock_response = MagicMock()
        mock_response.content = "Not JSON"
        generator.llm.invoke = MagicMock(return_value=mock_response)
        
        kp = KnowledgePoint(
            summary="S", category="C", key_facts=["F"], 
            distractor_ideas=["D"], source_chunk_id="ID"
        )
        
        candidate = generator.generate(kp, "Fact")
        self.assertIsNone(candidate)

if __name__ == '__main__':
    unittest.main()
