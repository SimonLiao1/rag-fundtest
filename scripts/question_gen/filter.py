import os
import pandas as pd
import numpy as np
from typing import List
from langchain_openai import OpenAIEmbeddings
from scripts.question_gen.models import GeneratedQuestion

from dotenv import load_dotenv

load_dotenv()

class DuplicationFilter:
    def __init__(self, validation_file: str = "rawdoc/validation_set.xlsx", threshold: float = 0.85):
        self.threshold = threshold
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.existing_vectors = []
        self.existing_texts = []
        
        # Load validation set if exists
        if os.path.exists(validation_file):
            print(f"Loading validation set from {validation_file}...")
            try:
                df = pd.read_excel(validation_file)
                # Assume column 'question' exists, fallback to first column if not
                col_name = 'question' if 'question' in df.columns else df.columns[0]
                questions = df[col_name].dropna().astype(str).tolist()
                
                if questions:
                    self.existing_vectors = self.embeddings.embed_documents(questions)
                    self.existing_texts = questions
                    print(f"Loaded {len(self.existing_vectors)} existing questions.")
            except Exception as e:
                print(f"Failed to load validation set: {e}")
        else:
            print(f"Validation set not found at {validation_file}, starting empty.")

        # In-session history
        self.generated_vectors = []
        self.generated_texts = []

    def is_duplicate(self, question_text: str) -> bool:
        """
        Checks if the question is similar to any existing or previously generated question.
        Returns True if duplicate (similarity > threshold).
        """
        if not question_text.strip():
            return True
            
        new_vector = self.embeddings.embed_query(question_text)
        
        # Check against existing (Validation Set)
        if self.existing_vectors:
            sims = self._cosine_similarity(new_vector, self.existing_vectors)
            if np.max(sims) > self.threshold:
                # print(f"Duplicate found in validation set (max sim: {np.max(sims):.4f})")
                return True
                
        # Check against generated (Session History)
        if self.generated_vectors:
            sims = self._cosine_similarity(new_vector, self.generated_vectors)
            if np.max(sims) > self.threshold:
                # print(f"Duplicate found in generated history (max sim: {np.max(sims):.4f})")
                return True
        
        return False

    def add_question(self, question: GeneratedQuestion):
        """Adds a verified question to the session history."""
        # We re-embed here or cache the embedding from check step. 
        # For simplicity/robustness, we re-embed or just assume it passed check.
        # Ideally we cache, but `embed_query` is cheap enough for single item usually.
        # Optimization: We could return vector from is_duplicate? 
        # For now, let's just re-embed to keep API clean.
        
        vector = self.embeddings.embed_query(question.question)
        self.generated_vectors.append(vector)
        self.generated_texts.append(question.question)

    def _cosine_similarity(self, vec: List[float], matrix: List[List[float]]) -> np.ndarray:
        """Computes cosine similarity between a vector and a matrix of vectors."""
        vec = np.array(vec)
        matrix = np.array(matrix)
        
        dot_product = np.dot(matrix, vec)
        norm_vec = np.linalg.norm(vec)
        norm_matrix = np.linalg.norm(matrix, axis=1)
        
        return dot_product / (norm_matrix * norm_vec)

# --- Quick Test ---
if __name__ == "__main__":
    # Ensure rawdoc dir exists for test or mock it
    if not os.path.exists("rawdoc"):
        os.makedirs("rawdoc")
        pd.DataFrame({"question": ["什么是基金？"]}).to_excel("rawdoc/validation_set.xlsx")
        
    filter = DuplicationFilter()
    print("Is '什么是基金？' duplicate?", filter.is_duplicate("什么是基金？"))
    print("Is '基金的概念是什么？' duplicate?", filter.is_duplicate("基金的概念是什么？")) # Likely true
    print("Is '今天天气怎么样？' duplicate?", filter.is_duplicate("今天天气怎么样？")) # Likely false
