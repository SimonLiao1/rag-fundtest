import os
import json
import sqlite3
import re
from typing import List, Dict, Set
from dotenv import load_dotenv

# LangChain
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Config
from config.prompt_templates import RAG_QA_PROMPT_TEMPLATE, CALC_QA_PROMPT_TEMPLATE

load_dotenv()

INDEX_DIR = "index"
FAISS_INDEX_DIR = os.path.join(INDEX_DIR, "faiss_v2")
SQLITE_DB_PATH = os.path.join(INDEX_DIR, "sqlite_v2.db")

class FundRAG:
    def __init__(self):
        self._init_vector_store()
        self._init_llm()
        
    def _init_vector_store(self):
        """Load FAISS V2 index"""
        print("Loading FAISS V2 index...")
        if not os.path.exists(FAISS_INDEX_DIR):
            raise FileNotFoundError(f"FAISS index not found at {FAISS_INDEX_DIR}")
            
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vector_store = FAISS.load_local(
            FAISS_INDEX_DIR, 
            embeddings,
            allow_dangerous_deserialization=True
        )
        
    def _init_llm(self):
        # Standard Pipeline (for Fact/Negative/Scenario)
        # Load from env or default to gpt-4o-mini
        std_model = os.getenv("RAG_LLM_MODEL", "gpt-4o-mini")
        print(f"Loading Standard LLM: {std_model}")
        self.std_llm = ChatOpenAI(model_name=std_model, temperature=0.0)
        self.std_prompt = PromptTemplate.from_template(RAG_QA_PROMPT_TEMPLATE)
        self.std_chain = self.std_prompt | self.std_llm | StrOutputParser()

        # Calc Pipeline (for Calculation questions)
        # Using stronger model for reasoning (e.g. gpt-4o)
        # Fallback to 3.5 if env not set, but user requested strong model.
        calc_model = os.getenv("CALC_MODEL_NAME", "gpt-5-mini")
        try:
            self.calc_llm = ChatOpenAI(model_name=calc_model, temperature=0.0)
        except Exception as e:
            print(f"Warning: Failed to load {calc_model}, falling back to gpt-3.5-turbo. Error: {e}")
            self.calc_llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.0)
            
        self.calc_prompt = PromptTemplate.from_template(CALC_QA_PROMPT_TEMPLATE)
        self.calc_chain = self.calc_prompt | self.calc_llm | StrOutputParser()

    def search_child_vector(self, query: str, k: int = 5) -> List[Dict]:
        """FAISS Child Search"""
        docs_and_scores = self.vector_store.similarity_search_with_score(query, k=k)
        results = []
        for doc, score in docs_and_scores:
            results.append({
                "parent_id": doc.metadata.get('parent_id'),
                "child_content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
                "source": "vector"
            })
        return results

    def search_child_keyword(self, query: str, k: int = 5) -> List[Dict]:
        """SQLite FTS5 Child Search"""
        results = []
        if not os.path.exists(SQLITE_DB_PATH):
            return []

        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Sanitize
            safe_query = query.replace('"', '""')
            safe_query = f'"{safe_query}"' # Quote wrap for literal phrase match attempt
            
            sql = """
                SELECT content, parent_id, metadata
                FROM doc_children_fts 
                WHERE doc_children_fts MATCH ? 
                ORDER BY rank 
                LIMIT ?
            """
            cursor.execute(sql, (safe_query, k))
            rows = cursor.fetchall()
            
            for row in rows:
                meta = json.loads(row['metadata'])
                results.append({
                    "parent_id": row['parent_id'],
                    "child_content": row['content'],
                    "metadata": meta,
                    "score": 0.0,
                    "source": "keyword"
                })
            conn.close()
        except Exception as e:
            print(f"Keyword search warning: {e}")
            
        return results

    def get_parents(self, parent_ids: List[str]) -> Dict[str, Dict]:
        """Batch fetch Parents from SQLite"""
        parents = {}
        if not parent_ids:
            return parents
            
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            placeholders = ','.join(['?'] * len(parent_ids))
            sql = f"SELECT id, content, metadata FROM doc_parents WHERE id IN ({placeholders})"
            
            cursor.execute(sql, parent_ids)
            rows = cursor.fetchall()
            
            for row in rows:
                parents[row['id']] = {
                    "content": row['content'],
                    "metadata": json.loads(row['metadata'])
                }
            conn.close()
        except Exception as e:
            print(f"Parent fetch error: {e}")
            
        return parents

    def hybrid_retrieval(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        1. Search Children (Vector + Keyword)
        2. Map to Parents
        3. Deduplicate Parents
        """
        # 1. Search Children
        vector_hits = self.search_child_vector(query, k=top_k)
        keyword_hits = self.search_child_keyword(query, k=top_k)
        
        all_hits = vector_hits + keyword_hits
        
        # 2. Collect unique Parent IDs (preserve order for ranking)
        parent_ids = []
        seen_ids = set()
        
        # Simple merge logic
        for hit in all_hits:
            pid = hit['parent_id']
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                parent_ids.append(pid)
        
        # Limit to top K Parents
        target_ids = parent_ids[:top_k]
        
        # 3. Fetch Parent Content
        parent_map = self.get_parents(target_ids)
        
        # 4. Construct Final Result List (in ranked order)
        final_results = []
        for pid in target_ids:
            if pid in parent_map:
                p_data = parent_map[pid]
                final_results.append({
                    "content": p_data['content'],
                    "metadata": p_data['metadata'],
                    "parent_id": pid
                })
                
        return final_results

    def format_context(self, docs: List[Dict]) -> str:
        context_parts = []
        for i, doc in enumerate(docs):
            meta = doc['metadata']
            source_str = f"[{meta.get('book')}|{meta.get('chapter')}|{meta.get('section')}]"
            if meta.get('figure_ref'):
                source_str += f" ({meta.get('figure_ref')})"
                
            context_parts.append(f"证据 {i+1} {source_str}:\n{doc['content']}\n")
        return "\n".join(context_parts)

    def _classify_query(self, query: str) -> str:
        """
        Rule-based Classifier for 'Calc' vs 'Standard'.
        Return: 'calc' or 'std'
        """
        # Keywords suggesting calculation
        calc_keywords = [
            "计算", "多少", "收益率", "净值", "费用", "金额", "比率", "份额",
            "%", "＋", "－", "+", "-", "×", "÷", "=", "大于", "小于",
            "转换", "换算", "公式",
            "n", "m", "比例", "期限" # Added to catch specific regulation numerical questions
        ]
        
        # Specific patterns often found in calc questions
        # e.g. "A. 100元" or "A. 10%"
        option_pattern = r"[A-D]\s*[：:.]\s*\d+"
        digit_pattern = r"\d+"
        
        score = 0
        q_lower = query.lower()
        
        for kw in calc_keywords:
            if kw in q_lower:
                score += 1
                
        if re.search(option_pattern, query):
            score += 2
            
        if re.search(digit_pattern, query):
            score += 1
            
        # Threshold
        if score >= 2:
            return 'calc'
        
        return 'std'

    def query(self, question: str) -> Dict:
        """Entry Point with Router"""
        
        # 0. Router
        pipeline_type = self._classify_query(question)
        # print(f"DEBUG: Pipeline Type = {pipeline_type}")
        
        # 1. Retrieval (Shared)
        final_docs = self.hybrid_retrieval(question, top_k=3) 
        
        if not final_docs:
            return {
                "answer": "未在教材中找到相关信息。",
                "confidence": 0.0,
                "evidence": []
            }
            
        # 2. Context Construction
        context_str = self.format_context(final_docs)
        
        # 3. Generation (Routed)
        if pipeline_type == 'calc':
            response_text = self.calc_chain.invoke({
                "context": context_str,
                "question": question
            })
        else:
            response_text = self.std_chain.invoke({
                "context": context_str,
                "question": question
            })
        
        return {
            "full_response": response_text,
            "evidence_sources": [d['metadata'] for d in final_docs],
            "pipeline": pipeline_type  # Return router decision for consistency check
        }

if __name__ == "__main__":
    rag = FundRAG()
    
    print("--- Test Standard ---")
    q1 = "开放式基金和封闭式基金的区别是什么？"
    res1 = rag.query(q1)
    print(f"Q: {q1}\nType: {res1.get('pipeline')}\nAns: {res1['full_response'][:100]}...\n")
    
    print("--- Test Calc ---")
    q2 = "某投资者投资10万元认购基金，认购费率为1%，净认购金额是多少？"
    res2 = rag.query(q2)
    print(f"Q: {q2}\nType: {res2.get('pipeline')}\nAns: {res2['full_response'][:100]}...")
