"""Smoke test for AeroTrace modules."""

import sys

def test_imports():
    print("[1/5] Testing Models...")
    from agent.models import ErrorAnalysis, AgentState
    ea = ErrorAnalysis(
        is_technical_issue=True,
        confidence_score=0.98,
        issue_summary="Test problem",
        suggested_fix="pip install test"
    )
    assert ea.is_technical_issue is True

    print("[2/5] Testing MCP Context...")
    from context.mcp_context import get_active_workspace_context
    ctx = get_active_workspace_context()
    print(f"       MCP context fetched: {list(ctx.keys())}")

    print("[3/5] Testing Agent Reasoning Engine...")
    from agent.agent import analyze_fused_context
    res1 = analyze_fused_context("ModuleNotFoundError: No module named 'requests'")
    assert res1.is_technical_issue is True
    assert "pip install requests" in res1.suggested_fix
    print(f"       Agent Python Error Result: {res1.suggested_fix}")

    res2 = analyze_fused_context(
        screen_text="ConnectionRefusedError: [Errno 111] port 5432",
        mcp_context=ctx
    )
    assert "docker start" in res2.suggested_fix or "5432" in res2.issue_summary
    print(f"       Agent MCP Fusion Result: {res2.suggested_fix}")

    res3 = analyze_fused_context("Welcome to our brand new web application")
    assert res3.is_technical_issue is False
    print(f"       Agent Normal Text Result: is_technical={res3.is_technical_issue}")

    print("[4/5] Testing Screen Capture...")
    from capture.screen import capture_cursor_region
    img = capture_cursor_region(100, 100)
    assert img is not None
    print(f"       Captured screen crop: {img.size}")

    print("[5/5] Testing OCR Module...")
    from capture.ocr import extract_text_from_image
    txt = extract_text_from_image(img)
    print(f"       OCR extracted text length: {len(txt)}")

    print("\n[PASS] ALL 5 SMOKE TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    test_imports()
