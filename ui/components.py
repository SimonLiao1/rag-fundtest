import gradio as gr
import os
from scripts.question_gen.db_utils import fetch_chapter_tree

def get_chapter_choices():
    """
    Returns a list of chapter strings for the Dropdown/CheckboxGroup.
    Format: "Book - Chapter"
    """
    tree = fetch_chapter_tree()
    choices = []
    for book, chapters in tree.items():
        for chapter in chapters:
            # Format: "Book - Chapter"
            label = f"{book} - {chapter}"
            choices.append(label)
    return choices

def get_custom_css():
    """
    Returns the custom CSS string.
    """
    return """
    /* --- 1. GLOBAL THEME --- */
    body, .gradio-container {
        background-color: #0b0f19 !important;
        color: #ffffff !important;
    }
    
    /* Text Colors */
    p, div, span, label, h1, h2, h3, h4, h5, h6, input, textarea {
        color: #ffffff !important;
    }
    
    /* Input Fields */
    input, textarea, select, .gr-input {
        background-color: #1f2937 !important;
        border: 1px solid #374151 !important;
    }
    
    /* Panel Styling */
    .dark-panel {
        background-color: #1f2937;
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }

    /* --- 2. TABLE STYLING --- */
    .table-wrap, table {
        background-color: #1f2937 !important;
        border-color: #374151 !important;
    }
    thead th, th {
        background-color: #374151 !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 15px !important;
        border-bottom: 2px solid #4b5563 !important;
    }
    tbody td, td {
        background-color: #111827 !important;
        color: #f3f4f6 !important; 
        border-bottom: 1px solid #374151 !important;
        font-size: 14px !important;
        vertical-align: top !important;
    }
    tbody tr:hover td {
        background-color: #1f2937 !important;
    }
    
    /* Column Widths */
    table td:first-child, table th:first-child { width: 25% !important; min-width: 250px !important; white-space: pre-wrap !important; }
    table td:nth-child(2), table th:nth-child(2) { width: 80px !important; text-align: center !important; }
    table td:nth-child(5), table th:nth-child(5) { width: 80px !important; text-align: center !important; }
    table td:last-child, table th:last-child { width: 50% !important; min-width: 350px !important; }

    /* --- 3. PROGRESS BAR CONTROL (TARGETED FIX) --- */
    
    /* Hide ALL time/timer displays globally */
    .progress-text .timer, 
    .progress-level .timer, 
    .progress-level-inner .timer,
    .eta, 
    .time-left,
    .meta-text,
    .progress-text-wrap .meta-text,
    span.meta-text-center {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        font-size: 0 !important;
        width: 0 !important;
        height: 0 !important;
    }

    /* Hide any element containing time format pattern */
    .progress-text > *:not(.progress-level) {
        display: none !important;
    }

    /* 
       Target the Status Box Container specifically to hide its progress bar completely.
       We use the ID #status-box-container defined in python.
    */
    #status-box-container .wrap,
    #status-box-container .status-tracker,
    #status-box-container .loading,
    #status-box-container .progress-bar,
    #status-box-container .progress-level,
    #status-box-container .progress-level-inner,
    #status-box-container .progress-text {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
    }
    
    /* Keep only one progress bar clean (under results table) */
    .status-tracker {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    /* --- 4. CHAT ASSISTANT STYLES --- */
    
    /* Mode Toggle Button */
    #mode-toggle-btn {
        position: absolute !important;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        z-index: 100 !important;
    }
    
    #mode-toggle-btn:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4) !important;
    }
    
    /* Chat History Container */
    .chat-history-container {
        background-color: #1f2937 !important;
        border: 1px solid #374151 !important;
        border-radius: 8px !important;
        padding: 20px !important;
        margin-bottom: 20px !important;
    }
    
    /* Chatbot message styling */
    .message-row {
        margin: 10px 0 !important;
    }
    
    /* User message bubble */
    .user-message .message {
        background-color: #1f2937 !important;
        border-left: 4px solid #2563eb !important;
        padding: 15px !important;
        border-radius: 8px !important;
    }
    
    /* Assistant message bubble */
    .bot-message .message {
        background-color: #111827 !important;
        border-left: 4px solid #10b981 !important;
        padding: 15px !important;
        border-radius: 8px !important;
    }
    
    /* Source citation styling */
    .source-citation {
        background-color: #0b0f19 !important;
        border: 2px dashed #374151 !important;
        padding: 12px !important;
        margin: 10px 0 10px 20px !important;
        border-radius: 6px !important;
        font-size: 13px !important;
        color: #9ca3af !important;
    }
    
    /* Clear chat button */
    #clear-chat-btn {
        background-color: #dc2626 !important;
        color: white !important;
        border: none !important;
        padding: 8px 16px !important;
        border-radius: 6px !important;
        cursor: pointer !important;
    }
    
    #clear-chat-btn:hover {
        background-color: #b91c1c !important;
    }
    
    /* Chat input area */
    #chat-user-input textarea {
        background-color: #1f2937 !important;
        border: 1px solid #374151 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        padding: 12px !important;
    }
    
    /* Send button */
    #chat-send-btn {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 24px !important;
        transition: all 0.3s ease !important;
    }
    
    #chat-send-btn:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4) !important;
    }
    """

def create_ui_components():
    """
    Creates and returns the UI components dictionary.
    Theme: Dark Mode (HuggingFace default dark or custom CSS)
    """
    chapter_choices = get_chapter_choices()
    
    components = {}
    
    with gr.Row():
        with gr.Column(scale=1, min_width=300, variant="panel"):
            gr.Markdown("### 🛠️ Configuration", elem_classes=["dark-panel"])
            
            # 1. Chapter Selection
            components["chapter_selector"] = gr.Dropdown(
                choices=chapter_choices,
                label="Select Chapters (Sources)",
                multiselect=True,
                info="Choose specific chapters or leave empty for random sampling from all.",
                value=None,
                interactive=True
            )
            
            # 2. Question Types
            components["type_selector"] = gr.CheckboxGroup(
                choices=["Fact", "Negative", "Scenario"],
                value=["Fact", "Negative"],
                label="Question Types",
                info="Select target question styles."
            )
            
            # 3. Quantity
            components["num_questions"] = gr.Slider(
                minimum=1, maximum=50, step=1, value=5,
                label="Target Quantity (N)",
                info="How many valid questions to generate."
            )
            
            # 4. Action
            components["btn_generate"] = gr.Button("🚀 Start Generation", variant="primary", size="lg")

        with gr.Column(scale=3):
            # Status Area
            # CRITICAL: elem_id="status-box-container" used for CSS targeting
            with gr.Row(elem_classes=["dark-panel"], elem_id="status-box-container"):
                components["status_box"] = gr.Markdown("### 🟢 Ready\nWaiting for input...", elem_id="status-text")
            
            # Results Table
            gr.Markdown("### 📝 Generated Results")
            components["results_table"] = gr.Dataframe(
                headers=["Question & Options", "Answer", "Type", "Source", "Score", "Explanation"],
                datatype=["markdown", "str", "str", "str", "number", "str"], 
                col_count=(6, "fixed"),
                interactive=False,
                wrap=True,
                elem_classes=["dark-panel"]
            )
            
            # Download Area
            with gr.Row():
                components["file_jsonl"] = gr.File(label="Download JSONL", visible=False)
                components["file_excel"] = gr.File(label="Download Excel", visible=False)

    return components
