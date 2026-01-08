
import time
import os
import sys

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

print(f"[{time.strftime('%H:%M:%S')}] 开始诊断程序...", flush=True)

try:
    print(f"[{time.strftime('%H:%M:%S')}] 1. 导入依赖...", flush=True)
    import torch
    from sentence_transformers import CrossEncoder
    print(f"[{time.strftime('%H:%M:%S')}]    依赖导入完成. Torch版本: {torch.__version__}", flush=True)

    print(f"[{time.strftime('%H:%M:%S')}] 2. 检查本地模型路径...", flush=True)
    model_path = os.path.join("models", "bge-reranker-base")
    if os.path.exists(model_path):
        print(f"[{time.strftime('%H:%M:%S')}]    本地模型存在: {model_path}", flush=True)
    else:
        print(f"[{time.strftime('%H:%M:%S')}]    警告: 本地模型不存在，将尝试联网下载", flush=True)

    print(f"[{time.strftime('%H:%M:%S')}] 3. 加载 Reranker 模型...", flush=True)
    start_load = time.time()
    reranker = CrossEncoder(model_path, model_kwargs={"torch_dtype": torch.float32})
    print(f"[{time.strftime('%H:%M:%S')}]    模型加载耗时: {time.time() - start_load:.2f}秒", flush=True)

    print(f"[{time.strftime('%H:%M:%S')}] 4. 测试 Rerank 推理...", flush=True)
    query = "什么是开放式基金？"
    doc = "开放式基金（Open-end Funds）是指基金份额不固定，基金份额总额随时增减..."
    
    start_infer = time.time()
    score = reranker.predict([(query, doc)])
    print(f"[{time.strftime('%H:%M:%S')}]    推理完成. 得分: {score[0]:.4f}", flush=True)
    print(f"[{time.strftime('%H:%M:%S')}]    推理耗时: {time.time() - start_infer:.2f}秒", flush=True)

    print(f"[{time.strftime('%H:%M:%S')}] 5. 初始化完整 Pipeline...", flush=True)
    # Fix import path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from rag_pipeline_v3 import FundRAG
    rag = FundRAG()
    
    # Manually inject the loaded reranker to skip lazy loading check
    rag.reranker = reranker 
    
    print(f"[{time.strftime('%H:%M:%S')}] 6. 执行完整 Query...", flush=True)
    q = "开放式基金的申购费率是多少？"
    start_query = time.time()
    res = rag.query(q)
    print(f"[{time.strftime('%H:%M:%S')}]    Query 完成. 耗时: {time.time() - start_query:.2f}秒", flush=True)
    print(f"[{time.strftime('%H:%M:%S')}]    Pipeline 类型: {res.get('pipeline')}", flush=True)

    print(f"[{time.strftime('%H:%M:%S')}] ✅ 诊断通过，系统功能正常。", flush=True)

except Exception as e:
    print(f"\n[{time.strftime('%H:%M:%S')}] ❌ 发生错误: {e}", flush=True)
    import traceback
    traceback.print_exc()

