import gradio as gr
from ui.components import create_ui_components, get_custom_css
from ui.callbacks import bind_callbacks
from ui.chat_components import create_chat_ui_components, create_mode_toggle_button
from ui.chat_callbacks import bind_chat_callbacks

def main():
    # 1. Get CSS
    css = get_custom_css()
    
    # 2. Build App
    with gr.Blocks(title="Fund Question Generator") as app:
        
        # Header with mode toggle button
        with gr.Row():
            with gr.Column(scale=4):
                gr.Markdown(
                    """
                    # 📚 Knowledge-driven Question Generator (KQG)
                    **Fund Certification Exam Prep Copilot**
                    """
                )
            with gr.Column(scale=1, min_width=150):
                # Mode toggle button (right-aligned)
                mode_toggle_btn = create_mode_toggle_button()
        
        # State to track current mode
        current_mode = gr.State(value="question_gen")
        
        # Question Generation Page (default visible)
        with gr.Group(visible=True) as question_gen_page:
            components_dict = create_ui_components()
            bind_callbacks(app, components_dict)
        
        # Chat Assistant Page (initially hidden)
        with gr.Group(visible=False) as chat_page:
            chat_components = create_chat_ui_components()
            bind_chat_callbacks(chat_components)
        
        # Bind mode toggle event
        def toggle_mode(mode):
            if mode == "question_gen":
                # Switch to chat mode
                return {
                    mode_toggle_btn: gr.update(value="📝 题目生成"),
                    question_gen_page: gr.update(visible=False),
                    chat_page: gr.update(visible=True),
                    current_mode: "chat"
                }
            else:
                # Switch to question gen mode
                return {
                    mode_toggle_btn: gr.update(value="🤖 问答助手"),
                    question_gen_page: gr.update(visible=True),
                    chat_page: gr.update(visible=False),
                    current_mode: "question_gen"
                }
        
        mode_toggle_btn.click(
            fn=toggle_mode,
            inputs=[current_mode],
            outputs=[mode_toggle_btn, question_gen_page, chat_page, current_mode]
        )
    
    return app, css

if __name__ == "__main__":
    app, css = main()
    app.launch(
        server_name="127.0.0.1", 
        server_port=7860, 
        share=False,
        css=css,
        theme=gr.themes.Default(primary_hue="blue", secondary_hue="slate")
    )
