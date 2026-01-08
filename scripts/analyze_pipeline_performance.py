import pandas as pd
import sys
import io

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def analyze_performance():
    file_path = "evaluation_calc_optimization.xlsx"
    print(f"Reading {file_path}...")
    try:
        df = pd.read_excel(file_path)
    except FileNotFoundError:
        print("Error: Result file not found.")
        return

    # Check columns
    if 'pipeline_type' not in df.columns:
        print("Error: 'pipeline_type' column missing. Please re-run evaluation with updated code.")
        return

    # 1. Calculate is_correct
    results = []
    for i, row in df.iterrows():
        std = str(row.get('std_answer', '')).strip().upper()
        pred = str(row.get('pred_answer', '')).strip().upper()
        
        is_correct = False
        if std and std != 'NAN' and std in pred:
            is_correct = True
            
        results.append({
            "idx": i+1,
            "pipeline": row['pipeline_type'],
            "is_correct": is_correct,
            "std": std,
            "pred": pred,
            "question": row['question'][:50] + "..."
        })
    
    res_df = pd.DataFrame(results)
    
    # 2. Group Stats
    print("\n=== Performance by Pipeline Type ===")
    stats = res_df.groupby('pipeline')['is_correct'].agg(['count', 'sum', 'mean'])
    stats.columns = ['Total', 'Correct', 'Accuracy']
    stats['Accuracy'] = stats['Accuracy'].apply(lambda x: f"{x:.2%}")
    print(stats)
    
    # 3. Detailed Breakdown
    for p_type in res_df['pipeline'].unique():
        print(f"\n--- Pipeline: {p_type} ---")
        subset = res_df[res_df['pipeline'] == p_type]
        correct_count = subset['is_correct'].sum()
        total_count = len(subset)
        print(f"Accuracy: {correct_count}/{total_count} ({correct_count/total_count:.2%})")
        
        print("Incorrect Questions:")
        wrong_subset = subset[~subset['is_correct']]
        if wrong_subset.empty:
            print("  (None)")
        else:
            for _, row in wrong_subset.iterrows():
                print(f"  [{row['idx']}] {row['question']} (Std:{row['std']} | Pred:{row['pred']})")

if __name__ == "__main__":
    analyze_performance()



