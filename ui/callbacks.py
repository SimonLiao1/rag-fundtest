import gradio as gr
import pandas as pd
import os
from scripts.generate_questions import QuestionGenerationPipeline

# Global Pipeline Instance (Lazy load)
pipeline = None

def get_pipeline():
    global pipeline
    if pipeline is None:
        pipeline = QuestionGenerationPipeline()
    return pipeline

def format_chapter_name(full_label):
    """Parses 'Book - Chapter' back to just 'Chapter' if needed, or keeps as is."""
    if " - " in full_label:
        return full_label.split(" - ", 1)[1] # Return the part after the first hyphen
    return full_label

def on_generate_click(chapters, types, num_questions, progress=gr.Progress()):
    """
    Event handler for the Generate button.
    """
    pipe = get_pipeline()
    
    # 1. Parse Inputs
    selected_chapters = None
    if chapters:
        selected_chapters = [format_chapter_name(c) for c in chapters]
        
    target_num = int(num_questions)
    
    # Start Progress
    progress(0.05, desc="Initializing...")
    
    # 2. Run Batch
    progress(0.1, desc="Fetching Chunks & Filtering...")
    
    def update_ui_progress(current, total):
        # Calculate ratio 
        if total <= 0: total = 1
        ratio = min(current / total, 1.0)
        
        # Scale progress from 0.1 to 0.95
        # This ensures we see movement even if it jumps from 1 to 2
        display_ratio = 0.1 + (ratio * 0.85)
        
        progress(display_ratio, desc=f"Generating... {current}/{total}")
    
    try:
        # Generate
        results = pipe.run_batch(
            chapters=selected_chapters, 
            num_questions=target_num, 
            target_types=types,
            max_workers=4,
            progress_callback=update_ui_progress
        )
        
        progress(0.98, desc="Finalizing...")
        
        # 3. Save
        jsonl_path, excel_path = pipe.save_results(results, output_dir="data")
        
        # 4. Format Output for Table
        df_data = []
        for q in results:
            # Format Question with Options
            options_text = ""
            if q.options:
                options_text = "\n".join([f"**{k}.** {v}" for k, v in q.options.items()])
            
            full_question_text = f"**{q.question}**\n\n{options_text}"
            
            source_str = f"{q.source_metadata.get('chapter', 'Unknown')}"
            
            df_data.append([
                full_question_text,
                q.answer,
                q.question_type,
                source_str,
                q.verification_score,
                q.explanation
            ])
            
        status_msg = f"### ✅ Success\nGenerated {len(results)} questions."
        
        return {
            "status_box": status_msg,
            "results_table": df_data,
            "file_jsonl": jsonl_path,
            "file_excel": excel_path,
            "file_jsonl_viz": gr.update(visible=True),
            "file_excel_viz": gr.update(visible=True)
        }
        
    except Exception as e:
        error_msg = f"### ❌ Error\n{str(e)}"
        return {
            "status_box": error_msg,
            "results_table": [],
            "file_jsonl": None,
            "file_excel": None,
            "file_jsonl_viz": gr.update(visible=False),
            "file_excel_viz": gr.update(visible=False)
        }

def bind_callbacks(app, components):
    """
    Binds the UI events to backend logic.
    """
    btn = components["btn_generate"]
    
    inputs = [
        components["chapter_selector"],
        components["type_selector"],
        components["num_questions"]
    ]
    
    # Wrapper to unpack dict to tuple if needed, or simple direct return
    def wrapper(ch, ty, n, prog=gr.Progress()):
        res = on_generate_click(ch, ty, n, prog)
        return (
            res["status_box"],
            res["results_table"],
            res["file_jsonl"],
            res["file_excel"],
            res["file_jsonl_viz"], 
            res["file_excel_viz"]
        )

    btn.click(
        fn=wrapper,
        inputs=inputs,
        outputs=[
            components["status_box"],
            components["results_table"],
            components["file_jsonl"],
            components["file_excel"],
            components["file_jsonl"], # For visibility update
            components["file_excel"]  # For visibility update
        ],
        show_progress="full"  # Show only the global progress bar
    )
