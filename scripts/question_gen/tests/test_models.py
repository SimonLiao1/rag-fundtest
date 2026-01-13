import unittest
from pydantic import ValidationError
from scripts.question_gen.models import KnowledgePoint, QuestionCandidate, GeneratedQuestion, QuestionOptions

class TestModels(unittest.TestCase):
    def test_knowledge_point_validation(self):
        """Test KnowledgePoint validation logic"""
        # Valid data
        kp = KnowledgePoint(
            summary="Valid Summary",
            category="Rule",
            key_facts=["Fact 1"],
            distractor_ideas=["Idea 1"],
            source_chunk_id="123"
        )
        self.assertEqual(kp.summary, "Valid Summary")

        # Missing field
        with self.assertRaises(ValidationError):
            KnowledgePoint(summary="Missing category")

    def test_question_candidate_validation(self):
        """Test QuestionCandidate validation logic"""
        kp = KnowledgePoint(
            summary="S", category="C", key_facts=["F"], 
            distractor_ideas=["D"], source_chunk_id="ID"
        )
        
        # Valid data
        qc = QuestionCandidate(
            question_text="Q?",
            options=QuestionOptions(A="1", B="2", C="3", D="4"),
            correct_answer="A",
            question_type="Fact",
            knowledge_point=kp
        )
        self.assertEqual(qc.correct_answer, "A")
        
        # Invalid answer (not A-D)
        with self.assertRaises(ValidationError):
            QuestionCandidate(
                question_text="Q?",
                options=QuestionOptions(A="1", B="2", C="3", D="4"),
                correct_answer="E", # Invalid
                question_type="Fact",
                knowledge_point=kp
            )

    def test_generated_question_validation(self):
        """Test GeneratedQuestion validation logic"""
        gq = GeneratedQuestion(
            id="uuid",
            question="Q?",
            options={"A":"1", "B":"2"},
            answer="A",
            explanation="Exp",
            source_chunk_id="123",
            source_metadata={},
            question_type="Fact",
            verification_score=0.9,
            created_at="2025-01-01"
        )
        self.assertEqual(gq.verification_score, 0.9)
        
        # Invalid score
        with self.assertRaises(ValidationError):
            GeneratedQuestion(
                id="uuid", question="Q?", options={}, answer="A", 
                explanation="", source_chunk_id="", source_metadata={}, 
                question_type="", verification_score=1.5, # > 1.0
                created_at=""
            )

if __name__ == '__main__':
    unittest.main()
