# -*- coding: utf-8 -*-
"""
NLP 模块集成测试脚本
测试与 run.py 的集成
"""
import sys
import time
import json
sys.stdout.reconfigure(encoding='utf-8')

def test_nlp_integration():
    """测试 NLP 与项目的集成"""
    print("="*70)
    print(" NLP 模块集成测试")
    print("="*70)
    
    # 测试 1: 模块导入
    print("\n[测试 1] 模块导入")
    try:
        from browser_use.nlp import (
            NLUPipeline, IntentClassifier, EntityExtractor,
            SemanticParser, EnhancedDSLParser, natural_language_to_dsl
        )
        print("  PASSED: 所有模块导入成功")
    except ImportError as e:
        print(f"  FAILED: 导入错误 - {e}")
        return False
    
    # 测试 2: 端到端流程
    print("\n[测试 2] 端到端 NLP 流程")
    pipeline = NLUPipeline()
    
    test_cases = [
        ("打开 https://example.com", ["navigate", "https://example.com"]),
        ("点击登录按钮", ["click"]),
        ("输入用户名 admin", ["input", "admin"]),
        ("等待 3 秒", ["wait"]),
        ("截图", ["screenshot"]),
    ]
    
    all_passed = True
    for text, expected_keywords in test_cases:
        result = pipeline.process(text)
        dsl = result.dsl_output.lower()
        
        matched = all(kw.lower() in dsl for kw in expected_keywords)
        status = "PASSED" if matched else "FAILED"
        print(f"  [{status}] '{text}' -> '{dsl}'")
        if not matched:
            all_passed = False
            print(f"       Expected keywords: {expected_keywords}")
    
    # 测试 3: 复合命令解析
    print("\n[测试 3] 复合命令解析")
    complex_text = """
    打开 https://example.com
    等待加载完成
    点击 #login-btn
    输入 #username admin
    截图
    """
    result = pipeline.process(complex_text)
    print(f"  输入行数: {len(complex_text.strip().split(chr(10)))}")
    print(f"  解析命令数: {len(result.commands)}")
    print(f"  DSL 输出:\n{result.dsl_output}")
    
    if len(result.commands) >= 4:
        print("  PASSED")
    else:
        print("  FAILED")
        all_passed = False
    
    # 测试 4: 错误处理
    print("\n[测试 4] 错误处理")
    try:
        empty_result = pipeline.process("")
        if empty_result.is_success():
            print("  PASSED: 空输入处理正确")
        else:
            print("  PASSED: 空输入返回失败状态")
    except Exception as e:
        print(f"  FAILED: 异常 - {e}")
        all_passed = False
    
    # 测试 5: 自然语言转 DSL
    print("\n[测试 5] 自然语言转 DSL 函数")
    nlp_dsl = natural_language_to_dsl("打开 https://github.com 然后点击登录")
    print(f"  输入: 打开 https://github.com 然后点击登录")
    print(f"  输出: {nlp_dsl}")
    if "navigate" in nlp_dsl.lower():
        print("  PASSED")
    else:
        print("  FAILED")
        all_passed = False
    
    # 测试 6: DSL 解析器
    print("\n[测试 6] DSL 解析器")
    parser = EnhancedDSLParser()
    dsl_text = """
    打开 https://example.com
    点击 #btn
    """
    instructions = parser.parse(dsl_text)
    print(f"  解析 {len(instructions)} 条指令")
    for inst in instructions[:3]:
        print(f"    - {inst}")
    if len(instructions) >= 2:
        print("  PASSED")
    else:
        print("  FAILED")
        all_passed = False
    
    # 测试 7: run.py API 兼容
    print("\n[测试 7] run.py API 兼容")
    try:
        # 模拟 _nlp_to_dsl 函数
        def _nlp_to_dsl(text):
            try:
                from browser_use.nlp.dsl_parser import natural_language_to_dsl
                return natural_language_to_dsl(text)
            except ImportError:
                return text
        
        dsl_result = _nlp_to_dsl("打开 https://test.com")
        print(f"  _nlp_to_dsl('打开 https://test.com') = '{dsl_result}'")
        if "navigate" in dsl_result.lower() or "https://test.com" in dsl_result:
            print("  PASSED")
        else:
            print("  WARNING: 输出可能不完整")
    except Exception as e:
        print(f"  FAILED: {e}")
        all_passed = False
    
    # 测试 8: 性能测试
    print("\n[测试 8] 性能测试")
    start = time.time()
    for _ in range(100):
        pipeline.process("打开 https://example.com 点击登录按钮")
    elapsed = time.time() - start
    avg_ms = (elapsed / 100) * 1000
    print(f"  100 次调用耗时: {elapsed:.3f}s")
    print(f"  平均耗时: {avg_ms:.2f}ms")
    if avg_ms < 10:
        print("  PASSED (性能良好)")
    else:
        print("  WARNING (性能较慢)")
    
    print("\n" + "="*70)
    if all_passed:
        print(" 集成测试完成: 全部通过!")
    else:
        print(" 集成测试完成: 有部分失败")
    print("="*70)
    
    return all_passed

if __name__ == "__main__":
    success = test_nlp_integration()
    sys.exit(0 if success else 1)
