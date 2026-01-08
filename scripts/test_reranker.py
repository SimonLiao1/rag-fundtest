import torch
from sentence_transformers import CrossEncoder

def test_rerank():
    model_name = "BAAI/bge-reranker-base"
    print(f"Loading model: {model_name}...")
    
    # Initialize CrossEncoder
    # It will download the model automatically on first run
    try:
        reranker = CrossEncoder(model_name, automodel_args={"torch_dtype": torch.float32})
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    # Test Case
    query = "开放式基金的申购费率是多少？"
    
    candidates = [
        "开放式基金的申购费率通常在1.0%到1.5%之间，具体视基金合同而定。",  # Relevant
        "封闭式基金的折价率受市场供求关系影响较大。",                       # Irrelevant
        "货币基金通常不收取申购费用。",                                   # Semi-relevant but specific
        "股票型基金的年管理费率一般为1.5%。"                               # Irrelevant (Management fee vs Subscription fee)
    ]
    
    print(f"\nQuery: {query}")
    print("Candidates:")
    for i, doc in enumerate(candidates):
        print(f"[{i}] {doc}")
        
    # Prepare pairs for scoring
    pairs = [[query, doc] for doc in candidates]
    
    # Predict scores
    print("\nScoring...")
    scores = reranker.predict(pairs)
    
    # Combine and Sort
    results = list(zip(candidates, scores))
    results.sort(key=lambda x: x[1], reverse=True)
    
    print("\n--- Rerank Results ---")
    for doc, score in results:
        print(f"Score: {score:.4f} | {doc}")

if __name__ == "__main__":
    test_rerank()


