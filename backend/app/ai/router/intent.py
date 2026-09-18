"""意图分类器：判断用户到底想干嘛。"""
class IntentClassifier:
    def classify(self, content: str) -> str:
        """目前用简单的规则匹配，后续可以替换成 LLM 判断。"""
        content_lower = content.lower()
        
        if any(k in content_lower for k in ["总结", "摘要", "概括"]):
            return "text_summary"
        elif any(k in content_lower for k in ["翻译", "英文", "英语"]):
            return "text_translate"
        elif any(k in content_lower for k in ["润色", "改写", "优化"]):
            return "text_polish"
        else:
            return "text_general"  # 默认通用处理

# 实例化
intent_classifier = IntentClassifier()