import unittest
from unittest.mock import MagicMock, patch
from scripts.question_gen.extractor import KnowledgeExtractor, KnowledgePoint

class TestExtractor(unittest.TestCase):
    
    @patch('scripts.question_gen.extractor.ChatOpenAI')
    def test_extract_success(self, MockChat):
        # Setup Mock
        mock_llm = MockChat.return_value
        # Mocking the chain invoke result is tricky because of the pipe operator logic in LangChain.
        # However, our Extractor wraps the chain. Let's mock the chain attribute of the instance 
        # OR mock the invoke call if we can access the chain.
        
        # Instead of deep mocking LangChain internals, let's mock the `invoke` method of the chain 
        # if possible, or simpler: just verify the `extract` method handles a valid return.
        
        extractor = KnowledgeExtractor()
        
        # Mock the chain object on the extractor instance
        mock_chain = MagicMock()
        extractor.chain = mock_chain
        
        # Define what the chain returns (Pydantic object)
        expected_kp = KnowledgePoint(
            summary="Sum", category="Rule", key_facts=["F1"], 
            distractor_ideas=["D1"], source_chunk_id="chunk_id"
        )
        mock_chain.invoke.return_value = expected_kp
        
        result = extractor.extract("Some content", "chunk_id")
        
        self.assertEqual(result, expected_kp)
        mock_chain.invoke.assert_called_once()
        
    @patch('scripts.question_gen.extractor.ChatOpenAI')
    def test_extract_failure(self, MockChat):
        extractor = KnowledgeExtractor()
        extractor.chain = MagicMock()
        extractor.chain.invoke.side_effect = Exception("API Error")
        
        result = extractor.extract("Some content", "chunk_id")
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
