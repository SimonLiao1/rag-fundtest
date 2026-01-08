# Query Processing Data Flow (RAG V3)

本文档描述了基金从业知识 Copilot (V3) 处理用户查询的完整数据流。

## 核心流程图 (Mermaid)

```mermaid
graph TD
    User[用户输入 Query] --> Router{Router 分类器}
    
    subgraph "Phase 1: Intent Recognition & Routing"
        Router -- "计算/公式/数值" --> CalcPipeline[Calculation Pipeline]
        Router -- "事实/概念/法规" --> StdPipeline[Standard Pipeline]
    end

    subgraph "Phase 2: Hybrid Retrieval (Shared)"
        CalcPipeline --> SearchStart
        StdPipeline --> SearchStart
        SearchStart[Query] -->|并行| VecSearch[FAISS Vector Search<br>(Top-20 Child Chunks)]
        SearchStart -->|并行| KeySearch[SQLite FTS5 Search<br>(Top-20 Child Chunks)]
        
        VecSearch --> Merge[合并去重]
        KeySearch --> Merge
        
        Merge --> MapParents[映射回 Parent Chunks<br>(获取完整上下文)]
        
        MapParents --> Rerank[Cross-Encoder Rerank<br>(BAAI/bge-reranker-base)]
        
        Rerank --> TopK{Select Top-3}
        TopK --> Context[构建 Context]
    end

    subgraph "Phase 3: LLM Generation"
        Context --> LLM_Input
        
        subgraph "LLM Interaction (One Pass)"
            LLM_Input -->|Prompt Template| Prompt
            
            Prompt -- "Std Pipeline" --> GPT_Std[LLM: GPT-4o<br>(RAG_QA_PROMPT)]
            Prompt -- "Calc Pipeline" --> GPT_Calc[LLM: GPT-5-mini / GPT-4o<br>(CALC_QA_PROMPT + CoT)]
            
            GPT_Std --> Answer
            GPT_Calc --> Answer
        end
    end

    Answer[最终回答] --> Output[返回用户]

    style GPT_Std fill:#e1f5fe,stroke:#01579b
    style GPT_Calc fill:#fff3e0,stroke:#ff6f00
    style Rerank fill:#f3e5f5,stroke:#7b1fa2
```

---

## 详细步骤说明

### 1. 意图识别 (Router)
*   **输入**: 用户 Query
*   **逻辑**: 基于规则 (Regex + Keywords)
*   **动作**: 
    *   检测到 "计算"、"收益率"、"%"、"公式" 等 -> 标记为 `calc`
    *   其他 -> 标记为 `std`
*   **LLM 交互**: **无** (纯本地逻辑，速度快)

### 2. 混合检索与重排 (Retrieval & Rerank)
*   **召回 (Recall)**:
    *   **Vector**: 检索 `child_chunks` (FAISS) -> Top 20
    *   **Keyword**: 检索 `child_chunks` (SQLite FTS5) -> Top 20
*   **映射 (Mapping)**: 
    *   将找到的 Child Chunks 映射回对应的 **Parent Chunk** (包含完整章节/段落上下文)。
*   **重排序 (Rerank)**:
    *   使用本地模型 `BAAI/bge-reranker-base` 对 `(Query, Parent_Content)` 对进行打分。
    *   选取分数最高的 **Top-3**。
*   **LLM 交互**: **无** (使用本地 Cross-Encoder 模型)

### 3. 生成回答 (Generation)
*   **Prompt 构建**:
    *   `std`: 使用标准问答模板，强调基于证据回答。
    *   `calc`: 使用 **Chain-of-Thought (CoT)** 模板，强制分步推理 (Step 1: 识别目标 -> Step 2: 提取公式 -> Step 3: 计算 -> ...)。
*   **LLM 推理**:
    *   调用 OpenAI API (`gpt-4o` 或 `gpt-5-mini`)。
    *   将 `Context` + `Query` 发送给模型。
*   **LLM 交互**: **1 次** (流式或一次性返回)

## 总结
*   **LLM 交互次数**: **1 次** (仅在生成阶段)。
*   **本地模型**: Router (规则), Embedding (OpenAI API/Local), Rerank (Local BGE)。
*   **关键特点**:
    *   **Router 前置**: 避免用弱模型处理计算题。
    *   **Rerank 中置**: 确保喂给 LLM 的 Context 是高质量的，减少 Token 消耗和幻觉。
    *   **CoT 后置**: 通过 Prompt 激发 LLM 的推理能力。

