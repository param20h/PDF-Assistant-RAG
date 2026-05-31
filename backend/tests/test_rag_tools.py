from app.rag.tools import MathTool, calculate_expression


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


def test_math_tool_run():
    tool = MathTool()
    result = tool.run({"expression": "12 * 3"})
    assert "Result: 36" in result


def test_math_tool_metadata():
    tool = MathTool()
    assert tool.name == "calculator"
    assert "mathematical calculations" in tool.description
    assert tool.args_schema is not None
