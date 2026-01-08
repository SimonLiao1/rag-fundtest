import pandas as pd
import os
import sys

# Add parent directory to path to import EvaluationTools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from EvaluationTools import evaluate  <-- EvaluationTools uses v2 by default
# We need to monkey patch or modify EvaluationTools, or just copy the evaluate logic here for v3 test.

# To keep it clean, let's create a temporary evaluate function here that uses FundRAG from v3
from rag_pipeline_v3 import FundRAG
import time

def evaluate_v3(input_file, output_file):
    print(f"Loading validation set from {input_file}...")
    df = pd.read_csv(input_file)
    
    print("Initializing RAG system V3 (With Rerank)...")
    rag = FundRAG()
    
    results = []
    print(f"Starting evaluation on {len(df)} questions...")
    
    for index, row in df.iterrows():
        question = row['question']
        std_answer = row.get('answer', '') or row.get('std_answer', '')
        
        print(f"[{index+1}/{len(df)}] Q: {question[:30]}...")
        
        start_time = time.time()
        try:
            rag_output = rag.query(question)
            full_response = rag_output['full_response']
            
            # Simple parsing
            pred_answer = ""
            lines = full_response.split('\n')
            for line in lines:
                if line.strip().lower().startswith("answer:") or line.strip().startswith("答案："):
                    pred_answer = line.split(":", 1)[1].strip()
                    break
            
            latency = time.time() - start_time
            
            results.append({
                "question": question,
                "std_answer": std_answer,
                "pred_answer": pred_answer,
                "full_response": full_response,
                "evidence_sources": str(rag_output.get('evidence_sources', [])),
                "pipeline_type": rag_output.get('pipeline', 'unknown'),
                "latency": round(latency, 2)
            })
            
        except Exception as e:
            print(f"Error processing Q{index+1}: {e}")
            
    result_df = pd.DataFrame(results)
    result_df.to_excel(output_file, index=False)
    print(f"Evaluation complete. Results saved to {output_file}")
    
    # Simple Accuracy
    if 'std_answer' in result_df.columns:
        correct = 0
        total = 0
        for _, row in result_df.iterrows():
            std = str(row['std_answer']).strip().upper()
            pred = str(row['pred_answer']).strip().upper()
            if not std or std == 'NAN': continue
            total += 1
            if std in pred:
                correct += 1
        
        if total > 0:
            print(f"Estimated Accuracy: {correct}/{total} ({correct/total:.2%})")

def run_calc_test():
    # 1. Load categorized data
    input_file = "evaluation_with_types.csv"
    if not os.path.exists(input_file):
        # If csv doesn't exist, try xlsx and filter manually if possible, 
        # but here we rely on the previously generated type file.
        print(f"Error: {input_file} not found. Please run analyze_by_type.py first.")
        return

    print(f"Loading {input_file}...")
    df = pd.read_csv(input_file)
    
    # 2. Filter for Calc questions
    # Note: Column names might vary based on previous script output
    # Looking for 'category' column containing 'Calc' or '计算'
    
    # Debug: print columns
    print(f"Columns: {df.columns.tolist()}")
    
    if 'category' in df.columns:
        calc_df = df[df['category'].astype(str).str.contains('Calc|计算', case=False, na=False)]
    else:
        print("Error: 'category' column not found.")
        return
        
    print(f"Found {len(calc_df)} calculation questions.")
    
    if len(calc_df) == 0:
        return

    # 3. Save to temp file
    temp_file = "rawdoc/temp_calc_test.csv"
    # Ensure rawdoc dir exists
    if not os.path.exists("rawdoc"):
        os.makedirs("rawdoc")
        
    # We need to keep 'question', 'std_answer' (or 'answer') for evaluation
    # Original 'evaluation_with_types.csv' might have 'question', 'std_answer'
    # Let's map them back if needed.
    
    # The 'evaluation_with_types.csv' was generated from results, so it has 'question' and 'std_answer' (or similar)
    # Let's check the first row content logic
    
    # Add original index
    calc_df['original_index'] = calc_df.index + 2 # +2 because index starts at 0 and excel header is row 1
    
    # Rename std_answer to answer for EvaluationTools
    if 'std_answer' in calc_df.columns:
        calc_df = calc_df.rename(columns={'std_answer': 'answer'})
        
    calc_df.to_csv(temp_file, index=False)
    print(f"Saved temp test file to {temp_file}")
    
    # 4. Run Evaluation
    output_file = "evaluation_calc_rerank.xlsx"
    print("Running evaluation on Calc subset (V3 Rerank)...")
    evaluate_v3(input_file=temp_file, output_file=output_file)
    
if __name__ == "__main__":
    run_calc_test()

