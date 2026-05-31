"""Agent tools for the PDF Assistant RAG backend."""

import ast
import operator as op
from typing import Any

from huggingface_hub.inference._generated.types.chat_completion import (
    ChatCompletionInputFunctionDefinition,
    ChatCompletionInputTool,
)

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
    """Safely evaluate a simple arithmetic expression.

    This tool only permits numeric literals and arithmetic operators.
    It does not execute arbitrary code.
    """
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


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a registered tool by name."""
    if name != "calculator":
        raise ValueError(f"Unknown tool: {name}")

    expression = arguments.get("expression")
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("The calculator tool requires a non-empty 'expression' string.")

    return calculate_expression(expression)


CALCULATOR_TOOL = ChatCompletionInputTool(
    function=ChatCompletionInputFunctionDefinition(
        name="calculator",
        description=(
            "Safely evaluate a numeric arithmetic expression for financial calculations. "
            "Use only numeric values and arithmetic operators like +, -, *, /, %, //, and **."
        ),
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": (
                        "A valid arithmetic expression to evaluate, for example '1000 - 250' or "
                        "'(revenue - expenses) * 0.2'."
                    ),
                }
            },
            "required": ["expression"],
        },
    ),
    type="tool",
)

TOOL_PROMPT = (
    "Use the calculator tool for all numeric arithmetic operations in the user query. "
    "The tool accepts a single 'expression' field and returns the evaluated numeric result. "
    "Do not attempt to compute arithmetic without the tool."
)

TOOLS = [CALCULATOR_TOOL]
