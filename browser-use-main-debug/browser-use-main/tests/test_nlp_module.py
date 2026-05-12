# -*- coding: utf-8 -*-
"""
NLP 模块全面测试脚本
测试所有 NLP 功能并报告结果
"""
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

from browser_use.nlp import (
    NLUPipeline, IntentClassifier, EntityExtractor,
    SemanticParser, EnhancedDSLParser, natural_language_to_dsl,
    Intent, EntityType, CommandType
)

# 测试结果统计
test_results = {"passed": 0, "failed": 0, "errors": []}

def test(name: str, func):
    """执行单个测试并记录结果"""
    try:
        print(f"\n{'='*60}")
        print(f"测试: {name}")
        print('='*60)
        result = func()
        if result:
            print(f"  PASSED")
            test_results["passed"] += 1
            return True
        else:
            print(f"  FAILED")
            test_results["failed"] += 1
            return False
    except Exception as e:
        print(f"  ERROR: {e}")
        test_results["errors"].append((name, str(e)))
        test_results["failed"] += 1
        return False

def assert_equal(actual, expected, msg=""):
    """断言相等"""
    if actual != expected:
        print(f"  Assertion Failed: {msg}")
        print(f"    Expected: {expected}")
        print(f"    Actual: {actual}")
        return False
    return True

def assert_contains(container, item, msg=""):
    """断言包含"""
    if item not in container:
        print(f"  Assertion Failed: {msg}")
        print(f"    Expected '{item}' in container")
        return False
    return True

def assert_true(value, msg=""):
    """断言为真"""
    if not value:
        print(f"  Assertion Failed: {msg}")
        return False
    return True

# ============================================================
# 测试意图分类器
# ============================================================

def test_intent_classifier_navigate():
    """测试导航意图识别"""
    classifier = IntentClassifier()
    
    tests = [
        ("打开 https://example.com", Intent.NAVIGATE),
        ("访问 https://github.com", Intent.NAVIGATE),
        ("goto https://baidu.com", Intent.NAVIGATE),
        ("返回", Intent.NAVIGATE_BACK),
        ("后退", Intent.NAVIGATE_BACK),
        ("前进", Intent.NAVIGATE_FORWARD),
        ("刷新", Intent.NAVIGATE_REFRESH),
    ]
    
    all_passed = True
    for text, expected_intent in tests:
        result = classifier.classify(text)
        print(f"  '{text}' -> {result.intent.value} (confidence: {result.confidence:.2f})")
        if result.intent != expected_intent:
            print(f"    Expected: {expected_intent.value}")
            all_passed = False
    
    return all_passed

def test_intent_classifier_click_input():
    """测试点击和输入意图"""
    classifier = IntentClassifier()
    
    tests = [
        ("点击 #login-btn", Intent.CLICK),
        ("click .submit", Intent.CLICK),
        ("双击 元素", Intent.DOUBLE_CLICK),
        ("右键 元素", Intent.RIGHT_CLICK),
        ("悬停 元素", Intent.HOVER),
        ("输入 #username admin", Intent.INPUT),
        ("清空 #search", Intent.CLEAR),
        ("按键 Enter", Intent.PRESS_KEY),
        ("选择 #country China", Intent.SELECT),
    ]
    
    all_passed = True
    for text, expected_intent in tests:
        result = classifier.classify(text)
        print(f"  '{text}' -> {result.intent.value} (confidence: {result.confidence:.2f})")
        if result.intent != expected_intent:
            print(f"    Expected: {expected_intent.value}")
            all_passed = False
    
    return all_passed

def test_intent_classifier_page_operations():
    """测试页面操作意图"""
    classifier = IntentClassifier()
    
    tests = [
        ("截图", Intent.SCREENSHOT),
        ("screenshot", Intent.SCREENSHOT),
        ("滚动 下", Intent.SCROLL),
        ("scroll up", Intent.SCROLL),
        ("滚动到 元素", Intent.SCROLL_TO),
        ("等待 2", Intent.WAIT),
        ("等待加载完成", Intent.WAIT_LOAD),
        ("等待可见 元素", Intent.WAIT_VISIBLE),
    ]
    
    all_passed = True
    for text, expected_intent in tests:
        result = classifier.classify(text)
        print(f"  '{text}' -> {result.intent.value} (confidence: {result.confidence:.2f})")
        if result.intent != expected_intent:
            print(f"    Expected: {expected_intent.value}")
            all_passed = False
    
    return all_passed

def test_intent_classifier_assert_get():
    """测试断言和获取意图"""
    classifier = IntentClassifier()
    
    tests = [
        ("获取文本 内容", Intent.GET_TEXT),
        ("获取URL", Intent.GET_URL),
        ("获取标题", Intent.GET_TITLE),
        ("断言可见 #btn", Intent.ASSERT_VISIBLE),
        ("断言文本 #msg 你好", Intent.ASSERT_TEXT),
        ("断言URL google", Intent.ASSERT_URL),
        ("断言标题 主页", Intent.ASSERT_TITLE),
    ]
    
    all_passed = True
    for text, expected_intent in tests:
        result = classifier.classify(text)
        print(f"  '{text}' -> {result.intent.value} (confidence: {result.confidence:.2f})")
        if result.intent != expected_intent:
            print(f"    Expected: {expected_intent.value}")
            all_passed = False
    
    return all_passed

def test_intent_classifier_iframe_tab():
    """测试 iframe 和标签页意图"""
    classifier = IntentClassifier()
    
    tests = [
        ("iframe #content", Intent.IFRAME),
        ("iframe点击 按钮", Intent.IFRAME_CLICK),
        ("iframe输入 body 你好", Intent.IFRAME_INPUT),
        ("退出iframe", Intent.EXIT_IFRAME),
        ("新标签页", Intent.NEW_TAB),
        ("关闭标签页", Intent.CLOSE_TAB),
        ("接受弹窗", Intent.ACCEPT_ALERT),
        ("拒绝弹窗", Intent.DISMISS_ALERT),
    ]
    
    all_passed = True
    for text, expected_intent in tests:
        result = classifier.classify(text)
        print(f"  '{text}' -> {result.intent.value} (confidence: {result.confidence:.2f})")
        if result.intent != expected_intent:
            print(f"    Expected: {expected_intent.value}")
            all_passed = False
    
    return all_passed

# ============================================================
# 测试实体识别器
# ============================================================

def test_entity_extractor_urls():
    """测试 URL 识别"""
    extractor = EntityExtractor()
    
    tests = [
        ("打开 https://example.com", "https://example.com"),
        ("访问 http://test.com/path", "http://test.com/path"),
        ("goto https://google.com/search?q=test", "https://google.com/search?q=test"),
    ]
    
    all_passed = True
    for text, expected_url in tests:
        entities = extractor.extract_all(text)
        urls = [e.value for e in entities if e.type == EntityType.URL]
        print(f"  '{text}' -> URLs: {urls}")
        if expected_url not in urls:
            print(f"    Expected URL not found: {expected_url}")
            all_passed = False
    
    return all_passed

def test_entity_extractor_selectors():
    """测试选择器识别"""
    extractor = EntityExtractor()
    
    tests = [
        ("点击 #submit-btn", ["#submit-btn"]),
        ("输入 [name=username] admin", ["[name=username]"]),
        ("点击 文本=登录", ["登录"]),
        ("悬停 role=button[name=submit]", ["role=button[name=submit]"]),
    ]
    
    all_passed = True
    for text, expected in tests:
        entities = extractor.extract_all(text)
        selectors = [e.value for e in entities if e.type == EntityType.CSS_SELECTOR or e.type == EntityType.TEXT_SELECTOR or e.type == EntityType.ROLE_SELECTOR]
        print(f"  '{text}' -> Selectors: {selectors}")
        for exp in expected:
            if exp not in str(selectors):
                print(f"    Expected selector not found: {exp}")
                all_passed = False
    
    return all_passed

def test_entity_extractor_dates():
    """测试日期识别"""
    extractor = EntityExtractor()
    
    tests = [
        ("今天是 2024-01-15", "2024-01-15"),
        ("日期 2024/05/20", "2024/05/20"),
        ("出生 1990年10月1日", "1990年10月1日"),
    ]
    
    all_passed = True
    for text, expected_date in tests:
        entities = extractor.extract_all(text)
        dates = [e.value for e in entities if e.type == EntityType.DATE]
        print(f"  '{text}' -> Dates: {dates}")
        if expected_date not in dates:
            print(f"    Expected date not found: {expected_date}")
            all_passed = False
    
    return all_passed

def test_entity_extractor_phones():
    """测试电话号码识别"""
    extractor = EntityExtractor()
    
    tests = [
        ("电话 13800138000", "13800138000"),
        ("手机 +86 13912345678", None),  # 规范化后的格式不确定
    ]
    
    all_passed = True
    for text, expected_phone in tests:
        entities = extractor.extract_all(text)
        phones = [e.value for e in entities if e.type == EntityType.PHONE]
        print(f"  '{text}' -> Phones: {phones}")
        if expected_phone and expected_phone not in phones:
            print(f"    Expected phone not found: {expected_phone}")
            all_passed = False
        elif not expected_phone and len(phones) == 0:
            print(f"    No phone extracted")
            all_passed = False
    
    return all_passed

# ============================================================
# 测试语义解析器
# ============================================================

def test_semantic_parser_single():
    """测试单条命令解析"""
    parser = SemanticParser()
    
    tests = [
        ("打开 https://example.com", CommandType.NAVIGATE, {"url": "https://example.com"}),
        ("点击 #btn", CommandType.CLICK, {"selector": "#btn"}),
        ("输入 #username admin", CommandType.INPUT, {"selector": "#username", "text": "admin"}),
        ("截图", CommandType.SCREENSHOT, {}),
        ("等待 2", CommandType.WAIT, {"duration": 2}),
    ]
    
    all_passed = True
    for text, expected_cmd, expected_params in tests:
        result = parser.parse(text)
        print(f"  '{text}' -> {result.command_type.value}, params: {result.params}")
        if result.command_type != expected_cmd:
            print(f"    Expected command: {expected_cmd.value}")
            all_passed = False
        for key, value in expected_params.items():
            if result.params.get(key) != value:
                print(f"    Parameter mismatch: {key} expected {value}, got {result.params.get(key)}")
                all_passed = False
    
    return all_passed

def test_semantic_parser_composite():
    """测试复合命令解析"""
    parser = SemanticParser()
    
    text = "打开 https://example.com\n点击 登录\n输入 用户名 admin"
    result = parser.parse_composite(text)
    
    print(f"  Input: {text}")
    print(f"  Commands: {[r.command_type.value for r in result]}")
    
    expected = [CommandType.NAVIGATE, CommandType.CLICK, CommandType.INPUT]
    all_passed = len(result) == 3
    for i, exp in enumerate(expected):
        if i < len(result) and result[i].command_type != exp:
            print(f"    Command {i} expected {exp.value}, got {result[i].command_type.value}")
            all_passed = False
    
    return all_passed

def test_semantic_parser_to_dsl():
    """测试 DSL 生成"""
    parser = SemanticParser()
    
    text = "打开 https://example.com\n点击 #btn\n截图"
    commands = parser.parse_composite(text)
    dsl = parser.to_dsl(commands)
    
    print(f"  Input: {text}")
    print(f"  DSL: {dsl}")
    
    expected_parts = ["navigate", "click", "screenshot"]
    all_passed = True
    for part in expected_parts:
        if part not in dsl:
            print(f"    Missing expected part in DSL: {part}")
            all_passed = False
    
    return all_passed

# ============================================================
# 测试 NLP 管道
# ============================================================

def test_nlp_pipeline_basic():
    """测试 NLP 管道基本功能"""
    pipeline = NLUPipeline()
    
    text = "打开 https://example.com 然后点击登录按钮"
    result = pipeline.process(text)
    
    print(f"  Input: {text}")
    print(f"  DSL Output: {result.dsl_output}")
    print(f"  Primary Intent: {result.primary_intent.value if result.primary_intent else None}")
    print(f"  Entities: {[str(e) for e in result.entities]}")
    print(f"  Commands: {[cmd.command_type.value for cmd in result.commands]}")
    print(f"  Processing Time: {result.processing_time_ms:.2f}ms")
    
    return result.is_success()

def test_nlp_pipeline_multiline():
    """测试多行文本处理"""
    pipeline = NLUPipeline()
    
    text = """
    打开 https://example.com
    等待加载完成
    输入 #username admin
    点击 #submit
    截图
    """
    result = pipeline.process(text)
    
    print(f"  Lines: {len(result.commands)}")
    print(f"  Commands: {[cmd.command_type.value for cmd in result.commands]}")
    
    return len(result.commands) >= 4

def test_nlp_pipeline_entities():
    """测试实体提取"""
    pipeline = NLUPipeline()
    
    text = "打开 https://example.com 输入 user@example.com"
    result = pipeline.process(text)
    
    print(f"  Entities count: {len(result.entities)}")
    for e in result.entities:
        print(f"    - {e.type.value}: {e.value}")
    
    return len(result.entities) > 0

def test_nlp_pipeline_confidence():
    """测试置信度计算"""
    pipeline = NLUPipeline()
    
    # 高置信度测试
    high_conf_text = "打开 https://example.com"
    high_result = pipeline.process(high_conf_text)
    print(f"  High confidence test: {high_conf_text}")
    print(f"    Confidence: {high_result.primary_intent_confidence:.2f}")
    
    # 低置信度测试
    low_conf_text = "做点什么"
    low_result = pipeline.process(low_conf_text)
    print(f"  Low confidence test: {low_conf_text}")
    print(f"    Confidence: {low_result.primary_intent_confidence:.2f}")
    
    return high_result.primary_intent_confidence > low_result.primary_intent_confidence

# ============================================================
# 测试自然语言转 DSL
# ============================================================

def test_natural_language_to_dsl():
    """测试自然语言转 DSL"""
    tests = [
        ("打开 https://example.com", "navigate"),
        ("点击 登录按钮", "click"),
        ("输入 用户名 admin", "input"),
    ]
    
    all_passed = True
    for text, expected_keyword in tests:
        dsl = natural_language_to_dsl(text)
        print(f"  '{text}' -> '{dsl}'")
        if expected_keyword not in dsl.lower():
            print(f"    Expected keyword '{expected_keyword}' not found")
            all_passed = False
    
    return all_passed

# ============================================================
# 测试 DSL 解析器
# ============================================================

def test_enhanced_dsl_parser():
    """测试增强 DSL 解析器"""
    parser = EnhancedDSLParser()
    
    dsl = """
    打开 https://example.com
    等待加载完成
    点击 #login
    输入 #username admin
    截图
    """
    
    instructions = parser.parse(dsl)
    
    print(f"  Parsed {len(instructions)} instructions")
    for inst in instructions:
        print(f"    - {inst}")
    
    return len(instructions) >= 4

def test_enhanced_dsl_parser_variables():
    """测试变量处理"""
    parser = EnhancedDSLParser()
    
    dsl = """
    base_url=https://example.com
    打开 $base_url
    """
    
    instructions = parser.parse(dsl)
    
    print(f"  Variables: {parser.variables}")
    print(f"  Instructions: {len(instructions)}")
    
    return "base_url" in parser.variables

# ============================================================
# 运行所有测试
# ============================================================

def main():
    print("\n" + "="*70)
    print(" NLP 模块全面测试")
    print("="*70)
    
    # 意图分类器测试
    test("意图分类器 - 导航意图", test_intent_classifier_navigate)
    test("意图分类器 - 点击输入意图", test_intent_classifier_click_input)
    test("意图分类器 - 页面操作意图", test_intent_classifier_page_operations)
    test("意图分类器 - 断言获取意图", test_intent_classifier_assert_get)
    test("意图分类器 - iframe/标签页意图", test_intent_classifier_iframe_tab)
    
    # 实体识别器测试
    test("实体识别器 - URL识别", test_entity_extractor_urls)
    test("实体识别器 - 选择器识别", test_entity_extractor_selectors)
    test("实体识别器 - 日期识别", test_entity_extractor_dates)
    test("实体识别器 - 电话识别", test_entity_extractor_phones)
    
    # 语义解析器测试
    test("语义解析器 - 单条命令", test_semantic_parser_single)
    test("语义解析器 - 复合命令", test_semantic_parser_composite)
    test("语义解析器 - DSL生成", test_semantic_parser_to_dsl)
    
    # NLP 管道测试
    test("NLP管道 - 基本功能", test_nlp_pipeline_basic)
    test("NLP管道 - 多行文本", test_nlp_pipeline_multiline)
    test("NLP管道 - 实体提取", test_nlp_pipeline_entities)
    test("NLP管道 - 置信度", test_nlp_pipeline_confidence)
    
    # 自然语言转 DSL 测试
    test("自然语言转 DSL", test_natural_language_to_dsl)
    
    # DSL 解析器测试
    test("增强 DSL 解析器", test_enhanced_dsl_parser)
    test("增强 DSL 变量处理", test_enhanced_dsl_parser_variables)
    
    # 输出统计
    print("\n" + "="*70)
    print(" 测试结果统计")
    print("="*70)
    print(f"  通过: {test_results['passed']}")
    print(f"  失败: {test_results['failed']}")
    
    if test_results['errors']:
        print(f"\n  错误详情:")
        for name, error in test_results['errors']:
            print(f"    - {name}: {error}")
    
    total = test_results['passed'] + test_results['failed']
    pass_rate = (test_results['passed'] / total * 100) if total > 0 else 0
    print(f"\n  通过率: {pass_rate:.1f}%")
    
    if test_results['failed'] == 0:
        print("\n  ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n  SOME TESTS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
