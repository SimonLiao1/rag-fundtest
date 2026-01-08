import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re

def parse_confidence(response_text):
    """Extract confidence score from response text."""
    try:
        match = re.search(r"Confidence:\s*([\d\.]+)", str(response_text), re.IGNORECASE)
        if match:
            return float(match.group(1))
        return 0.0
    except:
        return 0.0

def is_correct(row):
    """Determine correctness loosely."""
    std = str(row.get('std_answer', '')).strip().upper()
    pred = str(row.get('pred_answer', '')).strip().upper()
    
    if not std or std == 'NAN': return False
    return std in pred

def analyze_detailed(file_path="evaluation_results.xlsx"):
    print(f"Reading {file_path}...")
    df = pd.read_excel(file_path)
    
    # Preprocessing
    df['confidence'] = df['full_response'].apply(parse_confidence)
    df['is_correct'] = df.apply(is_correct, axis=1)
    df['latency'] = pd.to_numeric(df['latency'], errors='coerce')
    
    # 1. Latency Analysis
    print("\n" + "="*40)
    print("LATENCY ANALYSIS (Seconds)")
    print("="*40)
    print(df['latency'].describe().to_string())
    
    # Percentiles
    print("\nPercentiles:")
    print(f"P50: {df['latency'].quantile(0.5):.2f}s")
    print(f"P90: {df['latency'].quantile(0.9):.2f}s")
    print(f"P95: {df['latency'].quantile(0.95):.2f}s")
    print(f"P99: {df['latency'].quantile(0.99):.2f}s")

    # 2. Confidence vs Accuracy
    print("\n" + "="*40)
    print("CONFIDENCE vs ACCURACY")
    print("="*40)
    
    # Binning confidence
    bins = [0, 0.5, 0.7, 0.8, 0.9, 1.01]
    labels = ['0.0-0.5', '0.5-0.7', '0.7-0.8', '0.8-0.9', '0.9-1.0']
    df['conf_bin'] = pd.cut(df['confidence'], bins=bins, labels=labels, right=False)
    
    # Group by bin
    conf_stats = df.groupby('conf_bin', observed=True).agg(
        count=('is_correct', 'count'),
        correct=('is_correct', 'sum'),
        mean_latency=('latency', 'mean')
    )
    conf_stats['accuracy'] = conf_stats['correct'] / conf_stats['count']
    
    print(conf_stats.to_string())
    
    # 3. Correlation (Latency vs Confidence)
    corr = df['latency'].corr(df['confidence'])
    print("\n" + "="*40)
    print(f"Correlation (Latency vs Confidence): {corr:.4f}")
    print("="*40)
    
    # Optional: Save charts if libraries are available (skipped here to keep it text-based for terminal)
    # But we can output a summary CSV
    summary_file = "analysis_summary.csv"
    conf_stats.to_csv(summary_file)
    print(f"\nDetailed confidence stats saved to {summary_file}")

if __name__ == "__main__":
    try:
        analyze_detailed()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

