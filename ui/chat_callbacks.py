"""
Chat Assistant Callback Functions

This module contains all callback functions for the chat assistant interface,
including message sending, chat clearing, and event binding.
"""

import gradio as gr
import logging
from typing import List, Tuple, Dict, Any
from ui.chat_utils import get_rag, format_sources, handle_rag_error, validate_input, truncate_history

# Setup logging
logger = logging.getLogger(__name__)


def on_send_message(user_message: str, chat_history: List[Dict[str, str]]):
    """
    Handle user message submission and generate response with streaming output.
    
    Args:
        user_message: The user's input question
        chat_history: Current conversation history in Gradio Chatbot format
        
    Yields:
        tuple: (updated_chat_history, empty_string_for_input_clear)
    """
    # Validate input
    is_valid, error_msg = validate_input(user_message)
    if not is_valid:
        chat_history = chat_history or []
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": error_msg})
        yield chat_history, ""
        return
    
    try:
        # Initialize history if None
        if chat_history is None:
            chat_history = []
        
        # Add user message to history immediately - this shows the user's question right away
        chat_history.append({"role": "user", "content": user_message})
        yield chat_history, ""
        
        # Add placeholder for assistant response - shows we're working
        chat_history.append({"role": "assistant", "content": "🤖 正在检索相关知识..."})
        yield chat_history, ""
        
        # Get RAG instance
        rag = get_rag()
        
        # Call RAG pipeline with streaming
        logger.info(f"Processing question: {user_message[:50]}...")
        
        # Update status - show we're generating
        chat_history[-1] = {"role": "assistant", "content": "🤖 正在生成答案..."}
        yield chat_history, ""
        
        # Real streaming from LLM
        accumulated_text = ""
        evidence_sources = []
        retrieved_docs = []
        chunk_count = 0
        
        for stream_chunk in rag.query_stream(user_message):
            chunk_type = stream_chunk.get("type")
            
            if chunk_type == "metadata":
                # Initial metadata received, docs retrieved
                logger.info(f"Retrieved {stream_chunk.get('docs_found', 0)} documents")
                continue
                
            elif chunk_type == "chunk":
                # Stream LLM response in real-time
                content = stream_chunk.get("content", "")
                accumulated_text += content
                chunk_count += 1
                
                # Update every 2 chunks or when we have accumulated some text
                # This reduces update frequency and prevents truncation
                if chunk_count % 2 == 0 or len(content) > 10:
                    chat_history[-1] = {"role": "assistant", "content": accumulated_text}
                    yield chat_history, ""
                
            elif chunk_type == "sources":
                # Final sources received
                evidence_sources = stream_chunk.get("evidence_sources", [])
                retrieved_docs = stream_chunk.get("retrieved_docs", [])
        
        # Make sure we have the final accumulated text before adding sources
        if accumulated_text and chunk_count > 0:
            chat_history[-1] = {"role": "assistant", "content": accumulated_text}
            yield chat_history, ""
        
        # Format sources if available
        sources_text = format_sources(evidence_sources, retrieved_docs)
        
        # Log the final accumulated text length for debugging
        logger.info(f"Final accumulated text length: {len(accumulated_text)} chars, chunks: {chunk_count}")
        
        # Add sources to the response
        if sources_text:
            complete_response = accumulated_text + sources_text
            chat_history[-1] = {"role": "assistant", "content": complete_response}
            yield chat_history, ""
        
        # Truncate history if needed (keep last 100 messages)
        if len(chat_history) > 100:
            chat_history = chat_history[-100:]
        
        logger.info("Response generated successfully")
        
    except Exception as e:
        logger.error(f"Error in on_send_message: {e}")
        error_response = handle_rag_error(e)
        
        # Update the last assistant message with error
        if chat_history and len(chat_history) > 0 and chat_history[-1].get("role") == "assistant":
            chat_history[-1] = {"role": "assistant", "content": error_response}
        else:
            chat_history.append({"role": "assistant", "content": error_response})
        
        yield chat_history, ""


def bind_chat_callbacks(components: dict):
    """
    Bind all callback events for chat components.
    
    Args:
        components: Dictionary of UI components created by create_chat_ui_components()
    """
    # Send button click event with streaming
    components['send_btn'].click(
        fn=on_send_message,
        inputs=[
            components['user_input'],
            components['chat_display']  # Use chat_display directly for streaming
        ],
        outputs=[
            components['chat_display'],
            components['user_input']
        ],
        show_progress="minimal"  # Use minimal progress indicator
    )
    
    # Also allow Enter key to submit (Shift+Enter for new line)
    components['user_input'].submit(
        fn=on_send_message,
        inputs=[
            components['user_input'],
            components['chat_display']  # Use chat_display directly for streaming
        ],
        outputs=[
            components['chat_display'],
            components['user_input']
        ],
        show_progress="minimal"  # Use minimal progress indicator
    )
