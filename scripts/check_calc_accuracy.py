import pandas as pd
import sys
import io

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def analyze_calc_results():
    result_file = "evaluation_calc_rerank.xlsx"
    source_file = "rawdoc/temp_calc_test.csv"
    
    print(f"Reading {result_file} and {source_file}...")
    res_df = pd.read_excel(result_file)
    try:
        src_df = pd.read_csv(source_file)
    except:
        print("Source file not found, cannot map original indices.")
        src_df = pd.DataFrame()

    total = len(res_df)
    correct = 0
    
    print("\n--- Detailed Results (Original Index Mapping) ---")
    
    for i, row in res_df.iterrows():
        q = row['question']
        std = str(row['std_answer']).strip().upper()
        full_resp = str(row['full_response'])
        pred = str(row['pred_answer']).strip().upper()
        # New: Get pipeline type if available
        pipeline = row.get('pipeline_type', 'N/A')
        
        # Check correctness
        is_correct = False
        if std and std != 'NAN' and std in pred:
            is_correct = True
            correct += 1
            
        # Find original index
        orig_idx = "N/A"
        if not src_df.empty:
            # Match by question string
            match = src_df[src_df['question'] == q]
            if not match.empty:
                orig_idx = match.iloc[0]['original_index']
        
        if not is_correct:
            status = "[WRONG]"
            print(f"{status} [Orig:{orig_idx}] Std:{std} | Pred:{pred} | Pipeline:{pipeline}")
            print(f"    Q: {q[:60]}...")
            
            # Print CoT snippet
            if "Step" in full_resp:
                start = full_resp.find("Step")
                steps = full_resp[start:start+300].replace("\n", " ") + "..."
                print(f"    CoT: {steps}")
            else:
                print(f"    CoT: (No steps found)")
                
    print(f"\nTotal: {total}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {correct/total:.2%}")

if __name__ == "__main__":
    analyze_calc_results()
