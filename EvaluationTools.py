import pandas as pd
import argparse
import sys
import io
import time

def evaluate(input_file="rawdoc/validation.csv", output_file="evaluation_results.xlsx", limit=None):
    print(f"Loading validation set from {input_file}...", flush=True)
    
    # Lazy import to avoid long wait before first print
    print("Importing RAG modules (this may take a few seconds)...", flush=True)
    from rag_pipeline_v3 import FundRAG

    try:
        # Load CSV or Excel
        if input_file.endswith('.csv'):
            df = pd.read_csv(input_file)
        else:
            df = pd.read_excel(input_file)
            
        if limit:
            df = df.head(limit)
            print(f"Limiting evaluation to first {limit} questions.")
            
        # Standardize columns
        # Expect: question, answer (optional), maybe options A/B/C/D
        # For simple QA, we just need 'question'
        if 'question' not in df.columns:
            # Try to guess or fallback
            if '题目' in df.columns:
                df.rename(columns={'题目': 'question'}, inplace=True)
            elif '问题' in df.columns:  # Handle "问题" column
                df.rename(columns={'问题': 'question'}, inplace=True)
            else:
                print("Error: Input file must have a 'question', '题目', or '问题' column.")
                return

        print("Initializing RAG system...")
        rag = FundRAG()
        
        results = []
        print(f"Starting evaluation on {len(df)} questions...")
        
        for index, row in df.iterrows():
            question = row['question']
            std_answer = row.get('answer', '') or row.get('答案', '')
            
            print(f"[{index+1}/{len(df)}] Q: {question[:30]}...")
            
            start_time = time.time()
            try:
                # Query RAG
                rag_output = rag.query(question)
                full_response = rag_output['full_response']
                
                # Simple parsing of Answer from response text
                # Looking for "Answer: X" or "答案：X"
                # This is a heuristic parsing.
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
                results.append({
                    "question": question,
                    "error": str(e)
                })

        # Save Results
        result_df = pd.DataFrame(results)
        result_df.to_excel(output_file, index=False)
        print(f"Evaluation complete. Results saved to {output_file}")
        
        # Simple Accuracy Calc (if std_answer exists)
        if 'std_answer' in result_df.columns and not result_df['std_answer'].isna().all():
            # Loose matching: check if std_answer (e.g. "A") is contained in pred_answer
            correct = 0
            total = 0
            for _, row in result_df.iterrows():
                std = str(row['std_answer']).strip().upper()
                pred = str(row['pred_answer']).strip().upper()
                if not std: continue
                
                total += 1
                if std in pred: # Loose match "A" in "A. xxx"
                    correct += 1
            
            if total > 0:
                print(f"Estimated Accuracy: {correct}/{total} ({correct/total:.2%})")

    except Exception as e:
        print(f"Evaluation failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="rawdoc/validation_set.xlsx", help="Path to input CSV/Excel")
    parser.add_argument("--output", default="evaluation_results.xlsx", help="Path to output Excel")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions to evaluate")
    args = parser.parse_args()
    
    evaluate(args.input, args.output, args.limit)

