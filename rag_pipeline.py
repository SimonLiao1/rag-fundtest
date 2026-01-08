import os
import sqlite3
from typing import List, Dict, Tuple
from dotenv import load_dotenv

# LangChain
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Config
from config.prompt_templates import RAG_QA_PROMPT_TEMPLATE

load_dotenv()

INDEX_DIR = "index"
FAISS_INDEX_DIR = os.path.join(INDEX_DIR, "faiss")
SQLITE_DB_PATH = os.path.join(INDEX_DIR, "sqlite_fts.db")

class FundRAG:
    def __init__(self):
        self._init_vector_store()
        self._init_llm()
        
    def _init_vector_store(self):
        """Load FAISS index"""
        print("Loading FAISS index...")
        if not os.path.exists(FAISS_INDEX_DIR):
            raise FileNotFoundError(f"FAISS index not found at {FAISS_INDEX_DIR}")
            
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vector_store = FAISS.load_local(
            FAISS_INDEX_DIR, 
            embeddings,
            allow_dangerous_deserialization=True # Trusted local source
        )
        
    def _init_llm(self):
        """Initialize LLM"""
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo", # or gpt-4 if available
            temperature=0.0
        )
        self.prompt = PromptTemplate.from_template(RAG_QA_PROMPT_TEMPLATE)
        self.chain = self.prompt | self.llm | StrOutputParser()

    def search_vector(self, query: str, k: int = 4) -> List[Dict]:
        """FAISS Semantic Search"""
        docs_and_scores = self.vector_store.similarity_search_with_score(query, k=k)
        results = []
        for doc, score in docs_and_scores:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score), # Distance (lower is better for L2, but OpenAI returns cosine distance usually)
                "source": "vector"
            })
        return results

    def search_keyword(self, query: str, k: int = 4) -> List[Dict]:
        """SQLite FTS5 Keyword Search"""
        results = []
        if not os.path.exists(SQLITE_DB_PATH):
            print("Warning: SQLite index not found.")
            return []

        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Simple keyword matching using FTS5 syntax
            # Sanitize query: 
            # 1. Remove quotes (single/double) to prevent SQL injection or syntax error
            # 2. Replace common punctuation (English/Chinese) with space to allow token matching
            # Note: We keep '%' to preserve meaning (e.g. "100%"), but escape it for FTS5 string if needed.
            # However, standard FTS5 syntax uses double quotes for phrases. 
            # If we pass plain text, FTS5 standard tokenizer treats symbols as separators.
            # To avoid "syntax error near %", we wrap the query in quotes OR escape it?
            # Actually, the simplest way for "loose match" that is safe is to just tokenize ourselves 
            # or replace syntax-breaking chars.
            # If user asks "100%", FTS tokenizer likely splits to "100" and "%". 
            # If "%" causes syntax error, it might be interpreted as an operator.
            # Let's try wrapping the whole term in double quotes to treat as string literal.
            
            safe_query = query.replace('"', '""') # Escape existing double quotes
            safe_query = f'"{safe_query}"' # Wrap in double quotes for literal match attempts

            
            # Use NEAR() or simple MATCH
            # Here we just use MATCH with simple tokenization
            # For better results, we might need to segment Chinese query into tokens
            # But SQLite simple tokenizer splits by space/symbol. 
            # We'll try a loose match.
            
            sql = """
                SELECT content, book, chapter, section, figure_ref, chunk_type, exam_priority
                FROM docs_fts 
                WHERE docs_fts MATCH ? 
                ORDER BY rank 
                LIMIT ?
            """
            
            cursor.execute(sql, (safe_query, k))
            rows = cursor.fetchall()
            
            for row in rows:
                results.append({
                    "content": row['content'],
                    "metadata": {
                        "book": row['book'],
                        "chapter": row['chapter'],
                        "section": row['section'],
                        "figure_ref": row['figure_ref'],
                        "chunk_type": row['chunk_type'],
                        "exam_priority": row['exam_priority']
                    },
                    "score": 0.0, # FTS doesn't give normalized score easily
                    "source": "keyword"
                })
                
            conn.close()
        except Exception as e:
            print(f"Keyword search error: {e}")
            
        return results

    def hybrid_retrieval(self, query: str, top_k: int = 5) -> List[Dict]:
        """Combine Vector + Keyword Search"""
        # 1. Parallel search (sequential here for simplicity)
        vector_results = self.search_vector(query, k=top_k)
        keyword_results = self.search_keyword(query, k=top_k)
        
        # 2. Merge and Deduplicate
        # Key for dedup: content hash or just content string
        seen_content = set()
        merged_results = []
        
        # Strategy: Interleave results or prioritize vector?
        # Let's add all vector results first, then keyword results if new
        
        all_candidates = vector_results + keyword_results
        
        for res in all_candidates:
            # Normalize content for dedup
            content_sig = res['content'].strip()
            if content_sig in seen_content:
                continue
            seen_content.add(content_sig)
            merged_results.append(res)
            
        return merged_results

    def rerank(self, candidates: List[Dict], query: str) -> List[Dict]:
        """
        Lightweight Rerank Strategy:
        1. Prioritize 'manual_table_rewrite' chunks (high information density)
        2. Prioritize 'exam_priority' > 1
        3. (Optional) Cross-Encoder reranking (skipped for speed/cost)
        """
        # Score adjustment
        scored_candidates = []
        for res in candidates:
            base_score = 1.0 # Baseline
            
            # Boost Table Chunks
            if res['metadata'].get('chunk_type') == 'manual_table_rewrite':
                base_score += 0.5
                
            # Boost Exam Priority
            if res['metadata'].get('exam_priority', 1) > 1:
                base_score += 0.3
                
            # Boost Keyword matches (if source was keyword, it implies exact term match)
            if res['source'] == 'keyword':
                base_score += 0.2
            
            res['_rerank_score'] = base_score
            scored_candidates.append(res)
            
        # Sort by adjusted score
        scored_candidates.sort(key=lambda x: x['_rerank_score'], reverse=True)
        return scored_candidates[:5] # Keep Top 5 for context

    def format_context(self, docs: List[Dict]) -> str:
        context_parts = []
        for i, doc in enumerate(docs):
            meta = doc['metadata']
            source_str = f"[{meta.get('book')}|{meta.get('chapter')}|{meta.get('section')}]"
            if meta.get('figure_ref'):
                source_str += f" ({meta.get('figure_ref')})"
                
            context_parts.append(f"证据 {i+1} {source_str}:\n{doc['content']}\n")
        return "\n".join(context_parts)

    def query(self, question: str) -> Dict:
        """Main RAG Entry Point"""
        # 1. Retrieval
        candidates = self.hybrid_retrieval(question, top_k=5)
        
        # 2. Rerank
        final_docs = self.rerank(candidates, question)
        
        if not final_docs:
            return {
                "answer": "未在教材中找到相关信息。",
                "confidence": 0.0,
                "evidence": []
            }
            
        # 3. Context Construction
        context_str = self.format_context(final_docs)
        
        # 4. Generation
        response_text = self.chain.invoke({
            "context": context_str,
            "question": question
        })
        
        # 5. Parse Output (Naive parsing, assumes LLM follows format)
        # In production, use structured output parser
        return {
            "full_response": response_text,
            "evidence_sources": [d['metadata'] for d in final_docs]
        }

if __name__ == "__main__":
    # Simple Test
    rag = FundRAG()
    q = "开放式基金和封闭式基金的区别是什么？"
    print(f"Question: {q}")
    result = rag.query(q)
    print("\nResult:")
    print(result['full_response'])

