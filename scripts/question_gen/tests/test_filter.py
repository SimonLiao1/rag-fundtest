import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from scripts.question_gen.filter import DuplicationFilter
from scripts.question_gen.models import GeneratedQuestion

class TestFilter(unittest.TestCase):
    
    @patch('scripts.question_gen.filter.OpenAIEmbeddings')
    @patch('scripts.question_gen.filter.pd.read_excel') # Mock pandas to avoid file IO
    @patch('scripts.question_gen.filter.os.path.exists')
    def test_duplication_check(self, mock_exists, mock_read_excel, MockEmbeddings):
        mock_exists.return_value = True # Simulate validation file exists
        
        # Mock Embeddings
        mock_embed_instance = MockEmbeddings.return_value
        # 3 dimensions for simple math
        mock_embed_instance.embed_documents.return_value = [[1.0, 0.0, 0.0]] # Existing vector
        mock_embed_instance.embed_query.side_effect = [
            [1.0, 0.0, 0.0], # Duplicate (Same as existing)
            [0.0, 1.0, 0.0]  # Distinct (Orthogonal)
        ]
        
        # Mock Pandas
        mock_df = MagicMock()
        mock_df.__getitem__.return_value.dropna.return_value.astype.return_value.tolist.return_value = ["Q1"]
        mock_df.columns = ['question']
        mock_read_excel.return_value = mock_df
        
        filter = DuplicationFilter()
        
        # Test 1: Duplicate
        self.assertTrue(filter.is_duplicate("Same Question"))
        
        # Test 2: Distinct
        self.assertFalse(filter.is_duplicate("Different Question"))

if __name__ == '__main__':
    unittest.main()
