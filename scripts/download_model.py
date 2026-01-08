import os
from sentence_transformers import CrossEncoder

def download_reranker():
    model_name = "BAAI/bge-reranker-base"
    save_path = "models/bge-reranker-base"
    
    print(f"开始下载模型: {model_name} ...")
    print(f"目标路径: {os.path.abspath(save_path)}")
    
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    
    # 这会自动下载并保存到指定目录
    model = CrossEncoder(model_name)
    model.save(save_path)
    
    print("✅ 模型下载完成！")
    print(f"请更新 rag_pipeline_v3.py 中的模型路径为: {save_path}")

if __name__ == "__main__":
    download_reranker()

