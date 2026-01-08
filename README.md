# 基金从业知识 Copilot

基于 RAG（Retrieval-Augmented Generation）技术的基金从业考试问答系统。

## 项目简介
本项目将《证券投资基金》教材内容转化为可检索、可解释的智能问答系统，支持：
- **精准问答**: 结合混合检索与重排序 (Hybrid Retrieval + Rerank)，准确率达 88%+.
- **智能推理**: 针对计算题自动启用思维链 (CoT) 推理。
- **可溯源**: 回答包含精确的教材引用 (Book | Chapter | Section)。
- **置信度评估**: 提供回答的自信程度。

**最新评测结果 (V3)**:
- **总体准确率**: **88.28%** (452/512)
- **计算题准确率**: 87.50%
- **选非题准确率**: 93.96%
> 详见 [评测报告](Evaluation_Report_V3.md) 和 [流程说明](query_data_flow.md)

## 目录结构
- `rawdoc/`: 原始教材与验证集
- `data/`: 清洗后的中间数据
  - `parents.jsonl` / `children.jsonl`: Parent-Child 切片数据
- `index/`: 检索索引 (FAISS V2 + SQLite V2)
- `models/`: 本地模型 (如 bge-reranker-base)
- `config/`: 配置文件 (Prompt Templates)
- `scripts/`: 数据处理与分析脚本
- `rag_pipeline_v3.py`: 核心 RAG 链路 (包含 Router, Hybrid Retrieval, Rerank)
- `cli.py`: 命令行交互入口
- `EvaluationTools.py`: 自动化评测工具

## 快速开始

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量**
   创建 `.env` 文件并填入：
   ```ini
   OPENAI_API_KEY=sk-...
   RAG_LLM_MODEL=gpt-4o
   CALC_MODEL_NAME=gpt-5-mini
   ```

3. **下载模型 (首次运行)**
   ```bash
   python scripts/download_model.py
   ```
   此步骤会下载 `bge-reranker-base` 到本地 `models/` 目录。

4. **构建索引**
   ```bash
   python scripts/process_data_v2.py  # 处理数据
   python scripts/build_index_v2.py   # 构建索引
   ```

5. **运行系统**
   ```bash
   python cli.py
   ```
   
6. **运行评测**
   ```bash
   python EvaluationTools.py --input rawdoc/validation_set.xlsx
   ```
