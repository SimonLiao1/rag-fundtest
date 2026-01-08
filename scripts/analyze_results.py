import pandas as pd
import sys
import io

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def analyze(file_path="evaluation_results_v3.xlsx"):
    try:
        print(f"Reading {file_path}...")
        df = pd.read_excel(file_path)
        
        total = len(df)
        correct = 0
        error_count = 0
        
        # Simple analysis
        print("-" * 30)
        print("SAMPLE RESULTS:")
        print("-" * 30)
        
        for index, row in df.head(5).iterrows():
            q = row['question'][:30] + "..."
            std = str(row.get('std_answer', 'N/A')).strip()
            pred = str(row.get('pred_answer', 'N/A')).strip()
            full = str(row.get('full_response', ''))[:50].replace('\n', ' ')
            
            print(f"Q: {q}")
            print(f"  Std: {std} | Pred: {pred}")
            print(f"  Response: {full}...")
            print("-" * 10)

        # Calculate Stats if std_answer exists
        if 'std_answer' in df.columns:
            for index, row in df.iterrows():
                std = str(row['std_answer']).strip().upper()
                pred = str(row['pred_answer']).strip().upper()
                
                # Check for errors
                if 'error' in row and pd.notna(row['error']):
                    error_count += 1
                    continue
                    
                if not std or std == 'NAN': continue
                
                # Logic: Is the standard answer letter (A/B/C/D) in the prediction?
                # or does the prediction start with it?
                if std in pred:
                    correct += 1
            
            print("\n" + "=" * 30)
            print("EVALUATION SUMMARY")
            print("=" * 30)
            print(f"Total Questions: {total}")
            print(f"Errors/Failures: {error_count}")
            print(f"Correct Matches: {correct}")
            if total > 0:
                print(f"Accuracy Rate:   {correct/total:.2%}")
                
    except Exception as e:
        print(f"Analysis error: {e}")

if __name__ == "__main__":
    analyze()

