"""
Chat Assistant UI Components

This module defines the UI components for the chat assistant interface,
including chatbot display, input fields, and action buttons.
"""

import gradio as gr


def create_chat_ui_components():
    """
    Create and return the UI components for the chat assistant page.
    
    Returns:
        dict: Dictionary containing all chat UI components with keys:
            - chat_display: Gradio Chatbot component for conversation history
            - user_input: Textbox for user question input
            - send_btn: Button to submit question
            - clear_btn: Button to clear chat history
            - chat_state: State component to store conversation history
    
    Example:
        >>> components = create_chat_ui_components()
        >>> chat_display = components['chat_display']
        >>> send_btn = components['send_btn']
    """
    components = {}
    
    # Chat display area (conversation history)
    gr.Markdown("### 🤖 知识问答助手")
    gr.Markdown("输入您的问题，获取基于教材的专业解答")
    
    # Chatbot component - removed clear button, using built-in features
    components['chat_display'] = gr.Chatbot(
        label="💬 对话历史",
        height=320,
        show_label=True,
        elem_classes=["chat-history-container"],
        avatar_images=(None, None)  # No avatar images for cleaner look
    )
    
    # Input area - no title to avoid overlap
    with gr.Row():
        with gr.Column(scale=5):
            # Text input for user questions
            components['user_input'] = gr.Textbox(
                label="",
                placeholder="请输入您的问题，例如：开放式基金的申购流程是什么？",
                lines=2,
                max_lines=4,
                show_label=False,
                elem_id="chat-user-input"
            )
        
        with gr.Column(scale=1, min_width=100):
            # Send button - smaller size
            components['send_btn'] = gr.Button(
                "🚀 发送问题",
                variant="primary",
                size="sm",
                elem_id="chat-send-btn"
            )
    
    return components


def create_mode_toggle_button():
    """
    Create the mode toggle button for switching between pages.
    
    Returns:
        gr.Button: The mode toggle button component
    """
    toggle_btn = gr.Button(
        "🤖 问答助手",
        variant="primary",
        size="sm",
        elem_id="mode-toggle-btn"
    )
    
    return toggle_btn
