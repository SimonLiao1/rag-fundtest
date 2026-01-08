# 计算题专项优化计划 (Calc Optimization)

鉴于计算题 (Calc) 在当前 RAG 系统中准确率较低 (约 41%)，计划将其从主流程中隔离，使用专门的 Prompt 和更强的推理模型 (如 gpt-4o/o1-mini) 进行处理。

## 1. 架构设计 (Architecture)

采用 **路由模式 (Router Pattern)**：
1.  **Router**: 接收用户 Query，判断题目类型。
2.  **Calc Pipeline**: 专门处理计算题，侧重于公式提取、数值代入和步骤推理。
3.  **Standard Pipeline**: 处理非计算题，维持现有逻辑 (Fact, Negative, Scenario)。

```mermaid
graph TD
    UserQuery[用户提问] --> Router{题目分类器}
    Router -- "是计算题 (Calc)" --> CalcPipeline[计算题专用 Pipeline]
    Router -- "其他 (Fact/Neg/Scen)" --> StdPipeline[标准 RAG Pipeline]
    
    subgraph CalcPipeline
        Retriever[检索 Parent/Child] --> CalcPrompt[计算专用 Prompt]
        CalcPrompt --> StrongLLM[推理模型 (e.g. GPT-4o)]
    end
    
    subgraph StdPipeline
        Retriever2[检索 Parent/Child] --> StdPrompt[标准 Prompt]
        StdPrompt --> StdLLM[标准模型 (e.g. GPT-3.5/4o-mini)]
    end
```

## 2. 任务列表 (Task List)

### Phase 1: 路由与分类器 (Router & Classifier)
- [ ] **实现分类器 (`QueryRouter`)**:
  - 基于关键词规则 (如 "计算", "多少", "收益率", "净值", 数字符号等) 或轻量级 LLM 进行快速分类。
  - 输入: Question
  - 输出: `is_calc` (Boolean)
- [ ] **集成到 `FundRAG`**:
  - 修改 `rag_pipeline_v2.py` 的 `query` 方法，增加路由逻辑。

### Phase 2: 计算题专用 Pipeline (Calc Pipeline)
- [ ] **配置计算模型**:
  - 在 `config` 中添加 `CALC_MODEL_NAME` (e.g., "gpt-4o" 或 "gpt-4o-mini")。
  - 初始化专用的 LLM 实例。
- [ ] **设计计算专用 Prompt**:
  - 在 `config/prompt_templates.py` 中新增 `CALC_QA_PROMPT_TEMPLATE`。
  - 重点：强制要求 **Chain-of-Thought (CoT)**。
  - 结构：
    1. **提取公式**: 从上下文中找到相关公式。
    2. **提取参数**: 从题目和上下文中提取数值。
    3. **执行计算**: 逐步展示计算过程。
    4. **匹配选项**: 将计算结果与选项比对。
- [ ] **实现 `calc_pipeline` 方法**:
  - 复用现有的 `hybrid_retrieval` 获取上下文 (计算题也需要上下文中的公式和费率表)。
  - 调用专用 Prompt 和 LLM。

### Phase 3: 测试与验证 (Validation)
- [ ] **单元测试**:
  - 选取 5-10 道典型的计算题，验证 Router 是否正确识别。
  - 验证 Calc Pipeline 的输出是否包含推理步骤。
- [ ] **回归测试**:
  - 运行 `EvaluationTools.py` (需支持区分 Pipeline 或只测 Calc 子集)。
  - 对比优化前后的计算题准确率。

## 3. 关键配置

- **Model**: `CALC_MODEL_NAME` = "gpt-4o" (建议使用强推理模型)
- **Prompt Strategy**: CoT (思维链) + One-shot (可选)


