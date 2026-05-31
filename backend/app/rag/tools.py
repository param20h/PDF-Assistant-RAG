"""
Custom tools for the Agentic RAG system.
Defines PDF Search, Web Research, and Math tools.
"""
import json
import logging
import ast
import operator as op
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from app.rag.retriever import retrieve
from app.rag.graph_retriever import get_entity_context

logger = logging.getLogger(__name__)

# ── Math Helper ──────────────────────────────────────

_ALLOWED_OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def _evaluate_ast(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _evaluate_ast(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("Only numeric values are allowed in calculator expressions.")

    if isinstance(node, ast.BinOp):
        left = _evaluate_ast(node.left)
        right = _evaluate_ast(node.right)
        operator = type(node.op)
        if operator not in _ALLOWED_OPERATORS:
            raise ValueError(f"Operator {operator.__name__} is not allowed.")
        return _ALLOWED_OPERATORS[operator](left, right)

    if isinstance(node, ast.UnaryOp):
        operator = type(node.op)
        if operator not in _ALLOWED_OPERATORS:
            raise ValueError(f"Operator {operator.__name__} is not allowed.")
        operand = _evaluate_ast(node.operand)
        return _ALLOWED_OPERATORS[operator](operand)

    raise ValueError("Unsupported expression in calculator tool.")


def calculate_expression(expression: str) -> str:
    """Safely evaluate a simple arithmetic expression."""
    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid calculator expression: {exc}") from exc

    if not isinstance(parsed, ast.Expression):
        raise ValueError("Expression must be a single arithmetic expression.")

    result = _evaluate_ast(parsed)

    if result.is_integer():
        return str(int(result))

    return str(result)

# ── LangChain Tools ──────────────────────────────────

class PDFSearchSchema(BaseModel):
    query: str = Field(description="The search query to look for in the PDF documents.")

class PDFSearchTool(BaseTool):
    name: str = "pdf_search"
    description: str = (
        "Useful for searching and retrieving relevant information from uploaded PDF documents. "
        "Use this for any questions about the content of the documents."
    )
    args_schema: Type[BaseModel] = PDFSearchSchema
    
    user_id: str
    document_id: Optional[str] = None
    # We'll store sources here to retrieve them after agent execution
    last_sources: List[Dict[str, Any]] = []

    def _run(self, query: str) -> str:
        """Execute the search."""
        try:
            chunks = retrieve(
                query=query,
                user_id=self.user_id,
                document_id=self.document_id,
            )
            
            # Save for later retrieval
            self.last_sources = chunks
            
            if not chunks:
                return "No relevant information found in the documents."

            # Format chunks for the LLM
            context_parts = []
            for i, chunk in enumerate(chunks, 1):
                context_parts.append(
                    f"Excerpt {i} ({chunk['filename']}, Page {chunk['page']}):\n{chunk['text']}"
                )
            
            # Also try to get GraphRAG context
            graph_context = get_entity_context(
                query=query,
                user_id=self.user_id,
                document_id=self.document_id,
            )
            
            main_context = "\n\n".join(context_parts)
            if graph_context:
                return f"{main_context}\n\nAdditional Relationships found:\n{graph_context}"
            
            return main_context
        except Exception as e:
            logger.error(f"PDFSearchTool error: {e}")
            return f"Error searching documents: {str(e)}"

class MathSchema(BaseModel):
    expression: str = Field(description="The mathematical expression to evaluate (e.g., '2 + 2' or '(1000 - 250) * 0.2').")

class MathTool(BaseTool):
    name: str = "calculator"
    description: str = (
        "Useful for performing mathematical calculations and evaluating numerical expressions. "
        "Use this when the user asks for sums, differences, or complex math based on document data."
    )
    args_schema: Type[BaseModel] = MathSchema

    def _run(self, expression: str) -> str:
        """Execute the math evaluation safely using ast-based evaluator."""
        try:
            result = calculate_expression(expression)
            return f"Result: {result}"
        except Exception as e:
            return f"Error evaluating expression: {str(e)}. Please ensure it's a valid numerical expression."

# Placeholder for Web Search Tool (to be implemented in Issue #220)
class WebSearchSchema(BaseModel):
    query: str = Field(description="The query to search the live web for.")

class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Useful for fact-checking information or finding live data from the internet. "
        "Use this only when the PDF content is insufficient or outdated."
    )
    args_schema: Type[BaseModel] = WebSearchSchema

    def _run(self, query: str) -> str:
        return "Web search is currently in maintenance mode. Please rely on document content."
