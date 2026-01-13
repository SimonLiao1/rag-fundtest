import json
import os
from typing import List, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from scripts.question_gen.models import KnowledgePoint

load_dotenv()

# --- Prompt Definition ---

KNOWLEDGE_EXTRACTION_PROMPT = """
你是一个专业的教材分析助手。你的任务是从给定的教材片段（Chunk）中提取出一个结构化的“知识点”，用于后续生成单选题。

【输入教材片段】
{chunk_content}

【提取要求】
1. **Summary**: 用一句话概括这个片段的核心知识点。
2. **Category**: 判断知识点类型，必须是以下之一：
   - Definition (定义): 某个概念的解释
   - Rule (规则): 具体的规定、数值、比例、时间限制
   - Process (流程): 步骤、顺序
   - Prohibition (禁止): 明确禁止的行为
   - Classification (分类): 包含哪些类别或特征
   - General (一般描述): 其他
3. **Key Facts**: 提取 2-4 个原子事实（Atomic Facts）。每个事实必须直接来源于原文，且是生成题目正确选项的依据。
4. **Distractor Ideas**: 构思 2-3 个可能的干扰项方向（例如：混淆概念、反转逻辑、修改数值）。不要直接写干扰项文本，而是写“思路”。

【输出格式】
请严格输出符合以下 JSON 格式的字符串，不要包含 Markdown 代码块标记：
{{
    "summary": "...",
    "category": "...",
    "key_facts": ["...", "..."],
    "distractor_ideas": ["...", "..."],
    "source_chunk_id": "{chunk_id}"
}}
"""

class KnowledgeExtractor:
    def __init__(self, model_name: str = None, temperature: float = 0.0):
        # Use env var or default to qwen-max if not provided
        if model_name is None:
            model_name = os.getenv("RAG_LLM_MODEL", "qwen-max")
        # Initialize LLM similar to main pipeline
        efund_base = os.getenv("EFUNDS_API_BASE")
        efund_key = os.getenv("EFUNDS_API_KEY")
        
        llm_kwargs = {}
        if efund_base:
            llm_kwargs["base_url"] = efund_base
        if efund_key:
            llm_kwargs["api_key"] = efund_key
            
        # Headers for EFundGPT if present
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
        self.parser = PydanticOutputParser(pydantic_object=KnowledgePoint)
        
        # We define a custom prompt that includes format instructions if needed, 
        # but here we rely on the specific JSON prompt structure + Pydantic validation.
        self.prompt = PromptTemplate(
            template=KNOWLEDGE_EXTRACTION_PROMPT,
            input_variables=["chunk_content", "chunk_id"]
        )
        
        self.chain = self.prompt | self.llm | self.parser

    def extract(self, chunk_content: str, chunk_id: str) -> Optional[KnowledgePoint]:
        """
        Extracts a KnowledgePoint from a text chunk.
        Returns None if extraction fails or content is not suitable.
        """
        try:
            # Pre-check: if chunk is too short, skip
            if len(chunk_content.strip()) < 50:
                print(f"Chunk {chunk_id} too short, skipping.")
                return None
                
            result = self.chain.invoke({
                "chunk_content": chunk_content,
                "chunk_id": chunk_id
            })
            return result
        except Exception as e:
            print(f"Extraction failed for chunk {chunk_id}: {e}")
            return None

# --- Quick Test ---
if __name__ == "__main__":
    extractor = KnowledgeExtractor()
    test_chunk = """
    基金管理人应当在基金份额发售的3日前公布招募说明书、基金合同及其他有关文件。
    基金管理人应当将基金募集期间募集的资金存入专门账户，在基金募集行为结束前，任何人不得动用。
    """
    kp = extractor.extract(test_chunk, "test_id_001")
    if kp:
        print(json.dumps(kp.model_dump(), indent=2, ensure_ascii=False))
