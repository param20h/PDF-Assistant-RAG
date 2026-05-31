from app.rag.tools import CALCULATOR_TOOL, calculate_expression, execute_tool


def test_calculator_tool_evaluates_basic_expression():
    assert calculate_expression("1000 - 250") == "750"
    assert calculate_expression("10 + 5 * 2") == "20"
    assert calculate_expression("10 / 4") == "2.5"


def test_calculator_tool_rejects_unsafe_expression():
    try:
        calculate_expression("__import__('os').system('echo x')")
    except ValueError as exc:
        assert "Invalid calculator expression" in str(exc) or "Unsupported expression" in str(exc)
    else:
        assert False, "Unsafe expressions should not be evaluated"


def test_execute_tool_with_expression_argument():
    result = execute_tool("calculator", {"expression": "12 * 3"})
    assert result == "36"


def test_calculator_tool_metadata():
    assert CALCULATOR_TOOL["function"]["name"] == "calculator"
    assert "expression" in CALCULATOR_TOOL["function"]["parameters"]["properties"]
