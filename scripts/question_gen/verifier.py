import json
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from rag_pipeline_v3 import FundRAG
from scripts.question_gen.models import QuestionCandidate, GeneratedQuestion

VERIFICATION_PROMPT = """
你是一个严谨的考试题目审核员。请基于提供的【教材原文证据】，验证以下【生成题目】的质量。

【生成题目】
题干: {question}
选项:
A. {opt_A}
B. {opt_B}
C. {opt_C}
D. {opt_D}
正确答案: {correct_answer}

【教材原文证据】
{evidence_context}

【审核要求】
1. **唯一性**: 提供的证据是否**充分且唯一**地支持正确答案？
2. **正确性**: 正确答案是否与原文完全一致？
3. **互斥性**: 干扰项是否通过原文可以被明确排除（证明为错）？
4. **无幻觉**: 题目中是否包含了原文未提及的虚构信息？

【输出格式】
请严格输出符合以下 JSON 格式的字符串：
{{
    "status": "Pass/Fail",
    "score": 0.0-1.0,
    "reason": "简要说明审核通过或不通过的理由，指出具体的证据缺失或逻辑漏洞。"
}}
"""

class RAGVerifier:
    def __init__(self, rag_system: FundRAG = None):
        """
        :param rag_system: An instance of FundRAG. If None, a new one will be initialized (heavy).
        """
        if rag_system:
            self.rag = rag_system
        else:
            print("Initializing new FundRAG for Verifier...")
            self.rag = FundRAG()
            
        # We use a separate lightweight LLM for the verification step itself if needed,
        # but here we can reuse the rag's llm or init a new one.
        # Let's reuse the config approach for consistency.
        self.llm = self.rag.std_llm # Reuse the standard LLM from RAG
        
        self.prompt = PromptTemplate(
            template=VERIFICATION_PROMPT,
            input_variables=["question", "opt_A", "opt_B", "opt_C", "opt_D", "correct_answer", "evidence_context"]
        )
        self.chain = self.prompt | self.llm

    def verify(self, candidate: QuestionCandidate) -> GeneratedQuestion:
        """
        Verifies a question candidate using Reverse RAG.
        Returns a GeneratedQuestion with status 'Verified' or 'Rejected'.
        """
        # 1. Reverse RAG Retrieval
        # Construct a query string that includes the question and the claimed correct answer
        # to maximize the chance of retrieving relevant evidence.
        correct_text = getattr(candidate.options, candidate.correct_answer)
        query = f"{candidate.question_text} {correct_text}"
        
        retrieval_result = self.rag.query(query)
        evidence_docs = retrieval_result.get("retrieved_docs", [])
        evidence_context = self.rag.format_context(evidence_docs)
        
        # 2. LLM Verification
        try:
            res_msg = self.chain.invoke({
                "question": candidate.question_text,
                "opt_A": candidate.options.A,
                "opt_B": candidate.options.B,
                "opt_C": candidate.options.C,
                "opt_D": candidate.options.D,
                "correct_answer": candidate.correct_answer,
                "evidence_context": evidence_context
            })
            
            content = res_msg.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            result_data = json.loads(content)
            status = "Verified" if result_data.get("status") == "Pass" else "Rejected"
            score = float(result_data.get("score", 0.0))
            reason = result_data.get("reason", "")
            
        except Exception as e:
            print(f"Verification LLM failed: {e}")
            status = "Rejected"
            score = 0.0
            reason = f"Verification Error: {str(e)}"

        # 3. Construct Final Result
        # Convert Pydantic options to dict
        options_dict = candidate.options.model_dump()
        
        # Attach source metadata from the original KP's source chunk if possible.
        # In a real flow, we might fetch the metadata again or pass it through.
        # Here we assume the retrieval result's top doc might be the source, 
        # OR better, we use the candidate.knowledge_point.source_chunk_id if we had a way to lookup metadata.
        # For now, let's use the top retrieved evidence as the "verified source".
        
        verified_source_meta = {}
        if evidence_docs:
            verified_source_meta = evidence_docs[0].get("metadata", {})

        final_q = GeneratedQuestion(
            id=candidate.id,
            question=candidate.question_text,
            options=options_dict,
            answer=candidate.correct_answer,
            explanation=f"{candidate.explanation}\n[审核意见]: {reason}",
            source_chunk_id=candidate.knowledge_point.source_chunk_id,
            source_metadata=verified_source_meta, # Use evidence metadata
            question_type=candidate.question_type,
            verification_score=score,
            status=status,
            created_at="" # Should be set by caller or defaults
        )
        
        return final_q

# --- Quick Test ---
if __name__ == "__main__":
    from scripts.question_gen.models import KnowledgePoint, QuestionOptions
    
    # Mock Candidate
    kp = KnowledgePoint(summary="Test", category="Rule", key_facts=[], distractor_ideas=[], source_chunk_id="test")
    candidate = QuestionCandidate(
        question_text="开放式基金的申购费率最高不得超过申购金额的多少？",
        options=QuestionOptions(A="1%", B="2%", C="5%", D="10%"),
        correct_answer="C",
        question_type="Fact",
        knowledge_point=kp
    )
    
    verifier = RAGVerifier()
    result = verifier.verify(candidate)
    print(result.model_dump_json(indent=2, ensure_ascii=False))
