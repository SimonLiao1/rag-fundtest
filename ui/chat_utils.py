"""
Chat Assistant Utility Functions

This module provides utility functions for the chat assistant feature,
including RAG instance management, source formatting, and error handling.
"""

from typing import Dict, List, Optional
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Global RAG instance (lazy loading)
_rag_instance = None


def get_rag():
    """
    Get or initialize the FundRAG instance (lazy loading).
    
    Returns:
        FundRAG: The initialized RAG pipeline instance
        
    Raises:
        Exception: If RAG initialization fails
    """
    global _rag_instance
    
    if _rag_instance is None:
        try:
            logger.info("Initializing FundRAG instance...")
            from rag_pipeline_v3 import FundRAG
            _rag_instance = FundRAG()
            logger.info("FundRAG instance initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize FundRAG: {e}")
            raise Exception(f"RAG系统初始化失败: {str(e)}")
    
    return _rag_instance


def format_sources(metadata_list: List[Dict], retrieved_docs: List[Dict]) -> str:
    """
    Format retrieved document sources into readable Markdown format.
    
    Args:
        metadata_list: List of metadata dictionaries containing book, chapter info
        retrieved_docs: List of retrieved documents with content and rerank scores
        
    Returns:
        str: Formatted Markdown string with source citations
        
    Example:
        >>> sources_md = format_sources(metadata, docs)
        >>> print(sources_md)
        📚 **引用来源**:
        
        **[1]** 证券投资基金·上册 | 第5章 | 置信度: 0.89
        > 开放式基金申购费率一般为0.6%-1.5%...
    """
    if not metadata_list or not retrieved_docs:
        return ""
    
    sources_md = "\n\n---\n\n📚 **引用来源**:\n\n"
    
    for i, (meta, doc) in enumerate(zip(metadata_list, retrieved_docs), 1):
        # Extract metadata
        book = meta.get('book', 'Unknown')
        chapter = meta.get('chapter', 'Unknown')
        rerank_score = doc.get('rerank_score', 0.0)
        
        # Get text snippet (first 150 characters for better readability)
        content = doc.get('content', '')
        snippet = content[:150] + "..." if len(content) > 150 else content
        
        # Format source entry with better spacing and styling
        sources_md += f"**[{i}]** {book} | {chapter}\n\n"
        sources_md += f"<b>Confidence:</b> {rerank_score:.2f}\n\n"
        sources_md += f"<b>Evidence:</b>\n<span style='font-size: 0.9em; color: #666;'>> {snippet}</span>\n\n"
    
    return sources_md


def format_chat_message(role: str, content: str) -> tuple:
    """
    Format a chat message for Gradio Chatbot component.
    
    Args:
        role: Message role ('user' or 'assistant')
        content: Message content
        
    Returns:
        tuple: (role_prefix, content) formatted for Chatbot display
        
    Example:
        >>> msg = format_chat_message('user', '什么是开放式基金？')
        >>> # Returns: ('👤 用户', '什么是开放式基金？')
    """
    role_icons = {
        'user': '👤 用户',
        'assistant': '🤖 助手'
    }
    
    role_prefix = role_icons.get(role, role)
    return (role_prefix, content)


def handle_rag_error(error: Exception) -> str:
    """
    Handle RAG-related errors and return user-friendly error messages.
    
    Args:
        error: The exception that occurred
        
    Returns:
        str: User-friendly error message
        
    Example:
        >>> try:
        ...     rag.query(question)
        ... except Exception as e:
        ...     error_msg = handle_rag_error(e)
    """
    error_str = str(error)
    
    # Check for specific error patterns
    if "未在教材中找到相关信息" in error_str or "未找到" in error_str:
        return "❌ **未找到相关信息**\n\n未在教材中找到与您的问题相关的内容，请尝试换个问法或提供更多上下文。"
    
    elif "API" in error_str or "调用失败" in error_str:
        return "⚠️ **系统繁忙**\n\n服务暂时不可用，请稍后重试。如果问题持续存在，请联系管理员。"
    
    elif "初始化" in error_str:
        return "⚠️ **系统初始化失败**\n\n系统正在启动中，请稍等片刻后重试。"
    
    else:
        # Generic error
        logger.error(f"Unhandled RAG error: {error_str}")
        return f"⚠️ **发生错误**\n\n{error_str}\n\n请稍后重试或联系管理员。"


def truncate_history(history: List, max_rounds: int = 50) -> List:
    """
    Truncate chat history to prevent memory issues.
    
    Args:
        history: List of chat message tuples
        max_rounds: Maximum number of rounds to keep
        
    Returns:
        List: Truncated history
    """
    if len(history) > max_rounds:
        logger.info(f"Truncating history from {len(history)} to {max_rounds} rounds")
        return history[-max_rounds:]
    return history


def validate_input(text: str) -> tuple:
    """
    Validate user input before processing.
    
    Args:
        text: User input text
        
    Returns:
        tuple: (is_valid: bool, error_message: str)
        
    Example:
        >>> is_valid, error = validate_input("  ")
        >>> # Returns: (False, "输入不能为空")
    """
    if not text or not text.strip():
        return False, "输入不能为空，请输入您的问题。"
    
    if len(text) > 2000:
        return False, "输入过长（超过2000字），请精简您的问题。"
    
    return True, ""
