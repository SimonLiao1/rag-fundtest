import os
import json
import sqlite3
import re
from typing import List, Dict, Set
from dotenv import load_dotenv

import sys
import io
# Fix encoding for Windows console
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# LangChain
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Rerank imports (moved to lazy load)
# from sentence_transformers import CrossEncoder
# import torch

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
        # self._init_reranker() # Lazy load
        self.reranker = None
        
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
        # EFundGPT Configuration (Optional overrides for LLM only)
        # This allows keeping Embeddings on original OpenAI while moving LLM to EFundGPT
        efund_base = os.getenv("EFUNDS_API_BASE")
        efund_key = os.getenv("EFUNDS_API_KEY")
        
        # Headers for EFundGPT
        extra_headers = {}
        if os.getenv("EFUNDS_USER_NAME"):
            extra_headers["Efunds-User-Name"] = os.getenv("EFUNDS_USER_NAME")
        if os.getenv("EFUNDS_ACC_TOKEN"):
            extra_headers["Efunds-Acc-Token"] = os.getenv("EFUNDS_ACC_TOKEN")
        if os.getenv("EFUNDS_SOURCE"):
            extra_headers["Efunds-Source"] = os.getenv("EFUNDS_SOURCE")
            
        # Common kwargs for ChatOpenAI
        llm_kwargs = {}
        if efund_base:
            print(f"Using EFundGPT API Base: {efund_base}")
            llm_kwargs["base_url"] = efund_base
        if efund_key:
            llm_kwargs["api_key"] = efund_key
        if extra_headers:
            print("Injecting EFundGPT headers...")
            llm_kwargs["model_kwargs"] = {"extra_headers": extra_headers}

        # Standard Pipeline (for Fact/Negative/Scenario)
        # Load from env or default to gpt-4o-mini
        std_model = os.getenv("RAG_LLM_MODEL", "gpt-5.1-chat") #gpt-4o-mini
        print(f"Loading Standard LLM: {std_model}")
        self.std_llm = ChatOpenAI(model_name=std_model, temperature=0.0, **llm_kwargs)
        self.std_prompt = PromptTemplate.from_template(RAG_QA_PROMPT_TEMPLATE)
        self.std_chain = self.std_prompt | self.std_llm | StrOutputParser()

        # Calc Pipeline (for Calculation questions)
        # Using stronger model for reasoning (e.g. gpt-4o)
        # Fallback to 3.5 if env not set, but user requested strong model.
        calc_model = os.getenv("CALC_MODEL_NAME", "gpt-5.1")
        try:
            self.calc_llm = ChatOpenAI(model_name=calc_model, temperature=0.0, **llm_kwargs)
        except Exception as e:
            print(f"Warning: Failed to load {calc_model}, falling back to gpt-3.5-turbo. Error: {e}")
            # Fallback also uses the same kwargs unless it was the model itself that failed
            self.calc_llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.0, **llm_kwargs)
            
        self.calc_prompt = PromptTemplate.from_template(CALC_QA_PROMPT_TEMPLATE)
        self.calc_chain = self.calc_prompt | self.calc_llm | StrOutputParser()

    def _init_reranker(self):
        """Load BGE Reranker"""
        # BAAI/bge-reranker-base is lightweight and effective for Chinese
        print("Lazy Loading Rerank Model...", flush=True)
        try:
            from sentence_transformers import CrossEncoder
            import torch
            
            # Prefer local model if exists
            local_path = os.path.join("models", "bge-reranker-base")
            model_name_or_path = "BAAI/bge-reranker-base"
            
            if os.path.exists(local_path):
                print(f"Loading local Rerank model from: {local_path}")
                model_name_or_path = local_path
            else:
                print(f"Local model not found at {local_path}, downloading/loading from HuggingFace...")
            
            self.reranker = CrossEncoder(
                model_name_or_path, 
                model_kwargs={"torch_dtype": torch.float32} # Use float32 for CPU compatibility
            )
        except Exception as e:
            print(f"Reranker load failed: {e}")
            self.reranker = None

    def ensure_reranker(self):
        if self.reranker is None:
            self._init_reranker()

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
            # print(f"Keyword search warning: {e}")
            pass
            
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

    def _rerank_docs(self, query: str, docs: List[Dict]) -> List[Dict]:
        """
        Rerank a list of Parent Docs using CrossEncoder.
        docs: List of dict with 'content', 'metadata', 'parent_id'
        """
        self.ensure_reranker()
        
        if not self.reranker or not docs:
            return docs
            
        pairs = [[query, doc['content']] for doc in docs]
        
        try:
            scores = self.reranker.predict(pairs)
            
            # Attach scores
            for i, doc in enumerate(docs):
                doc['rerank_score'] = float(scores[i])
                
            # Sort descending
            docs.sort(key=lambda x: x['rerank_score'], reverse=True)
            
        except Exception as e:
            print(f"Rerank failed: {e}")
            
        return docs

    def hybrid_retrieval(self, query: str, final_k: int = 3) -> List[Dict]:
        """
        1. Search Children (Broad Recall: Vector + Keyword) -> Initial Pool (e.g. 20)
        2. Map to Parents
        3. Deduplicate
        4. Rerank Parents -> Final K
        """
        # 1. Broad Search (Initial K = 20)
        initial_k = 20
        vector_hits = self.search_child_vector(query, k=initial_k)
        keyword_hits = self.search_child_keyword(query, k=initial_k)
        
        all_hits = vector_hits + keyword_hits
        
        # 2. Collect unique Parent IDs
        parent_ids = []
        seen_ids = set()
        
        for hit in all_hits:
            pid = hit['parent_id']
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                parent_ids.append(pid)
        
        # 3. Fetch All Candidates (No limit here yet, or maybe top 20 parents)
        # If we have too many parents, Rerank might be slow. Let's limit candidate parents to 20.
        candidate_ids = parent_ids[:20]
        parent_map = self.get_parents(candidate_ids)
        
        candidate_docs = []
        for pid in candidate_ids:
            if pid in parent_map:
                p_data = parent_map[pid]
                candidate_docs.append({
                    "content": p_data['content'],
                    "metadata": p_data['metadata'],
                    "parent_id": pid
                })
        
        # 4. Rerank
        reranked_docs = self._rerank_docs(query, candidate_docs)
        
        # 5. Top K
        return reranked_docs[:final_k]

    def format_context(self, docs: List[Dict]) -> str:
        context_parts = []
        for i, doc in enumerate(docs):
            meta = doc['metadata']
            source_str = f"[{meta.get('book')}|{meta.get('chapter')}|{meta.get('section')}]"
            if meta.get('figure_ref'):
                source_str += f" ({meta.get('figure_ref')})"
                
            # Add rerank score to context for debugging (optional)
            # score_info = f" (Score: {doc.get('rerank_score', 0):.4f})"
            score_info = ""
                
            context_parts.append(f"证据 {i+1} {source_str}{score_info}:\n{doc['content']}\n")
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
            "n", "m", "比例", "期限" 
        ]
        
        # Specific patterns often found in calc questions
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
        
        # 1. Retrieval (Shared, now with Rerank)
        final_docs = self.hybrid_retrieval(question, final_k=5) 
        
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
            "pipeline": pipeline_type,
            "retrieved_docs": final_docs # Return for debug
        }
    
    def query_stream(self, question: str):
        """
        Entry Point with Router - Streaming Version
        
        Yields:
            dict: Streaming chunks containing:
                - type: 'metadata' (initial), 'chunk' (streaming), 'sources' (final)
                - content: the actual content
                - other metadata as needed
        """
        # 0. Router
        pipeline_type = self._classify_query(question)
        
        # 1. Retrieval (Shared, now with Rerank)
        final_docs = self.hybrid_retrieval(question, final_k=5)
        
        # Yield metadata first
        yield {
            "type": "metadata",
            "pipeline": pipeline_type,
            "docs_found": len(final_docs)
        }
        
        if not final_docs:
            yield {
                "type": "chunk",
                "content": "未在教材中找到相关信息。"
            }
            yield {
                "type": "sources",
                "evidence_sources": [],
                "retrieved_docs": []
            }
            return
        
        # 2. Context Construction
        context_str = self.format_context(final_docs)
        
        # 3. Generation (Routed) - Stream the response
        if pipeline_type == 'calc':
            chain = self.calc_chain
        else:
            chain = self.std_chain
        
        # Stream chunks from LLM
        for chunk in chain.stream({
            "context": context_str,
            "question": question
        }):
            yield {
                "type": "chunk",
                "content": chunk
            }
        
        # Yield sources at the end
        yield {
            "type": "sources",
            "evidence_sources": [d['metadata'] for d in final_docs],
            "retrieved_docs": final_docs
        }

if __name__ == "__main__":
    rag = FundRAG()
    
    print("--- Test Rerank ---")
    q = "开放式基金的申购费率是多少？"
    res = rag.query(q)
    print(f"Q: {q}")
    print("Top 3 Evidence Scores:")
    for doc in res['retrieved_docs']:
        print(f"- {doc.get('rerank_score', 0):.4f} | {doc['content'][:50]}...")
