import sys
import io
import pandas as pd
import re

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def classify_question(text):
    """
    Classify question based on keywords.
    Priority: Negative > Scenario > Fact
    """
    text = str(text)
    
    # 1. 选非题 (Negative)
    negative_keywords = ['错误', '不正确', '不包括', '不属于', '不符合', '例外']
    for kw in negative_keywords:
        if kw in text:
            return "选非题 (Negative)"
            
    # 2. 情景/计算题 (Scenario/Calc)
    # Heuristic: Starts with specific subject or involves calculation keywords
    if re.match(r'^(某|甲|乙|A|B|X)', text): # e.g. "某基金...", "甲公司..."
        return "情景题 (Scenario)"
        
    calc_keywords = ['计算', '收益率', '净值', '折算', '费用']
    # If it contains calculation keywords AND looks like it asks for a number or result
    if any(kw in text for kw in calc_keywords) and ('是多少' in text or '为' in text):
        return "计算题 (Calc)"

    # 3. 常规事实题 (Fact)
    return "事实题 (Fact)"

def is_correct(row):
    """Determine correctness loosely."""
    std = str(row.get('std_answer', '')).strip().upper()
    pred = str(row.get('pred_answer', '')).strip().upper()
    
    if not std or std == 'NAN': return False
    return std in pred

def analyze_by_type(file_path="evaluation_results.xlsx"):
    print(f"Reading {file_path}...")
    try:
        df = pd.read_excel(file_path)
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return
    
    # Preprocess
    df['category'] = df['question'].apply(classify_question)
    df['is_correct'] = df.apply(is_correct, axis=1)
    df['latency'] = pd.to_numeric(df['latency'], errors='coerce')
    
    # Group by Category
    print("\n" + "="*50)
    print("ACCURACY BY QUESTION TYPE")
    print("="*50)
    
    stats = df.groupby('category', observed=True).agg(
        total=('is_correct', 'count'),
        correct=('is_correct', 'sum'),
        mean_latency=('latency', 'mean')
    )
    
    stats['accuracy'] = stats['correct'] / stats['total']
    stats['accuracy_pct'] = stats['accuracy'].apply(lambda x: f"{x:.2%}")
    stats['mean_latency'] = stats['mean_latency'].apply(lambda x: f"{x:.2f}s")
    
    # Sort by total count
    stats = stats.sort_values('total', ascending=False)
    
    print(stats[['total', 'correct', 'accuracy_pct', 'mean_latency']].to_string())
    
    # Save tagged data for review
    output_file = "evaluation_with_types.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\nDetailed results with types saved to {output_file}")

if __name__ == "__main__":
    analyze_by_type()

