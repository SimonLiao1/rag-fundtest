import os
import json
import random
from typing import List, Optional, Dict
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from scripts.question_gen.models import KnowledgePoint, QuestionCandidate, QuestionOptions

load_dotenv()

# --- Templates ---

FACT_TEMPLATE = """
你是一个专业的试题生成专家。请基于给定的【知识点】生成一道【单选题】。

【知识点信息】
摘要: {summary}
核心事实: {key_facts}
干扰项思路: {distractor_ideas}

【出题要求 - 事实题 (Fact)】
1. 题干：询问关于该知识点的正确描述。例如“以下关于...的说法，正确的是？”
2. 正确选项：直接改写核心事实，保持语义一致，但不要照抄原文。
3. 干扰项：根据干扰项思路生成3个错误选项。错误选项必须在逻辑、数值或概念上与原文相悖。
4. 风格：正式、客观，符合基金从业资格考试风格。

【输出格式】
请严格输出符合以下 JSON 格式的字符串：
{{
    "question_text": "...",
    "options": {{
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "..."
    }},
    "correct_answer": "A/B/C/D",
    "explanation": "简要解释为什么该选项正确，其他选项错误。"
}}
"""

NEGATIVE_TEMPLATE = """
你是一个专业的试题生成专家。请基于给定的【知识点】生成一道【选非题】。

【知识点信息】
摘要: {summary}
核心事实: {key_facts}
干扰项思路: {distractor_ideas}

【出题要求 - 选非题 (Negative)】
1. 题干：询问关于该知识点的**错误**描述。例如“以下关于...的说法，错误的是？”或“不属于...的是？”
2. 正确选项（即那个错误的说法）：基于核心事实进行逻辑反转、数值篡改或概念偷换。
3. 干扰项（即那3个正确的说法）：直接改写核心事实，作为干扰项（因为题目选错的，所以正确的说法是干扰项）。
4. 风格：正式、客观，符合基金从业资格考试风格。

【输出格式】
请严格输出符合以下 JSON 格式的字符串：
{{
    "question_text": "...",
    "options": {{
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "..."
    }},
    "correct_answer": "A/B/C/D",
    "explanation": "简要解释为什么该选项是错误的（即符合题意）。"
}}
"""

SCENARIO_TEMPLATE = """
你是一个专业的试题生成专家。请基于给定的【知识点】生成一道【情景题】。

【知识点信息】
摘要: {summary}
核心事实: {key_facts}
干扰项思路: {distractor_ideas}

【出题要求 - 情景题 (Scenario)】
1. 题干：构造一个简短的业务场景（如“某基金经理小王...”），描述一种行为或情况，询问该行为的合规性或性质。
2. 正确选项：根据核心事实判断该行为的后果或定性。
3. 干扰项：给出看似合理但错误的判断或理由。
4. 风格：贴近实际业务，逻辑严密。

【输出格式】
请严格输出符合以下 JSON 格式的字符串：
{{
    "question_text": "...",
    "options": {{
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "..."
    }},
    "correct_answer": "A/B/C/D",
    "explanation": "结合场景与知识点进行解析。"
}}
"""

class QuestionGenerator:
    def __init__(self, model_name: str = None, temperature: float = 0.7):
        # Use env var or default to qwen-max if not provided
        if model_name is None:
            model_name = os.getenv("RAG_LLM_MODEL", "qwen-max")
        # Initialize LLM
        efund_base = os.getenv("EFUNDS_API_BASE")
        efund_key = os.getenv("EFUNDS_API_KEY")
        
        llm_kwargs = {}
        if efund_base:
            llm_kwargs["base_url"] = efund_base
        if efund_key:
            llm_kwargs["api_key"] = efund_key
            
        extra_headers = {}
        if os.getenv("EFUNDS_USER_NAME"):
            extra_headers["Efunds-User-Name"] = os.getenv("EFUNDS_USER_NAME")
        if os.getenv("EFUNDS_ACC_TOKEN"):
            extra_headers["Efunds-Acc-Token"] = os.getenv("EFUNDS_ACC_TOKEN")
        if os.getenv("EFUNDS_SOURCE"):
            extra_headers["Efunds-Source"] = os.getenv("EFUNDS_SOURCE")
            
        if extra_headers:
            llm_kwargs["model_kwargs"] = {"extra_headers": extra_headers}

        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature, **llm_kwargs)
        
        # Parsers are slightly loose here as we manually handle the JSON structure usually, 
        # but let's try Pydantic parser for robustness if the model follows well.
        # However, for generating options A-D, a simple JSON parser is often more flexible 
        # because we need to map A-D randomly usually? Or let LLM do it.
        # Here we ask LLM to output A-D.
        
        self.templates = {
            "Fact": PromptTemplate(template=FACT_TEMPLATE, input_variables=["summary", "key_facts", "distractor_ideas"]),
            "Negative": PromptTemplate(template=NEGATIVE_TEMPLATE, input_variables=["summary", "key_facts", "distractor_ideas"]),
            "Scenario": PromptTemplate(template=SCENARIO_TEMPLATE, input_variables=["summary", "key_facts", "distractor_ideas"]),
        }

    def generate(self, kp: KnowledgePoint, target_type: str = "Fact") -> Optional[QuestionCandidate]:
        """
        Generates a question from a KnowledgePoint.
        """
        if target_type not in self.templates:
            print(f"Unknown target type: {target_type}, falling back to Fact")
            target_type = "Fact"
            
        prompt = self.templates[target_type]
        chain = prompt | self.llm
        
        try:
            # Join lists for prompt
            facts_str = "\n- " + "\n- ".join(kp.key_facts)
            ideas_str = "\n- " + "\n- ".join(kp.distractor_ideas)
            
            response_msg = chain.invoke({
                "summary": kp.summary,
                "key_facts": facts_str,
                "distractor_ideas": ideas_str
            })
            
            # Clean and parse JSON
            content = response_msg.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            data = json.loads(content)
            
            # Construct QuestionCandidate
            candidate = QuestionCandidate(
                question_text=data["question_text"],
                options=QuestionOptions(**data["options"]),
                correct_answer=data["correct_answer"],
                explanation=data.get("explanation", ""),
                question_type=target_type,
                knowledge_point=kp
            )
            return candidate
            
        except Exception as e:
            print(f"Generation failed for KP {kp.summary[:20]}...: {e}")
            return None

# --- Quick Test ---
if __name__ == "__main__":
    from scripts.question_gen.models import KnowledgePoint
    
    # Mock KP
    mock_kp = KnowledgePoint(
        summary="Test Summary",
        category="Rule",
        key_facts=["Fact A", "Fact B"],
        distractor_ideas=["Idea 1", "Idea 2"],
        source_chunk_id="test_chunk"
    )
    
    gen = QuestionGenerator()
    q = gen.generate(mock_kp, "Negative")
    if q:
        print(q.model_dump_json(indent=2))
