"""Token计数和编码抽象模块，用于精确的Token级别文本处理"""

from typing import Protocol


class Tokenizer(Protocol):
    """Tokenizer协议，定义Token计数和编码的标准接口

    所有chunker使用此接口进行Token级别的文本处理，确保精确的chunk大小控制。
    """

    def encode(self, text: str) -> list[int]:
        """将文本编码为Token ID列表

        Args:
            text: 待编码的文本

        Returns:
            Token ID列表
        """
        ...

    def decode(self, tokens: list[int]) -> str:
        """将Token ID列表解码为文本

        Args:
            tokens: Token ID列表

        Returns:
            解码后的文本
        """
        ...

    def count_tokens(self, text: str) -> int:
        """计算文本中的Token数量

        Args:
            text: 待计算的文本

        Returns:
            Token数量
        """
        ...


class TiktokenTokenizer:
    """基于tiktoken的Tokenizer实现，用于OpenAI兼容的Token计数

    使用tiktoken库进行Token编码，默认使用cl100k_base编码（GPT-4/GPT-3.5-turbo）。

    Examples:
        >>> tokenizer = TiktokenTokenizer("cl100k_base")
        >>> tokens = tokenizer.encode("Hello, world!")
        >>> count = tokenizer.count_tokens("Hello, world!")
        >>> text = tokenizer.decode(tokens)
    """

    def __init__(self, model_name: str = "cl100k_base") -> None:
        """初始化TiktokenTokenizer

        Args:
            model_name: tiktoken编码名称，常用值：
                - "cl100k_base" (GPT-4, GPT-3.5-turbo)
                - "p50k_base" (Codex)
                - "r50k_base" (GPT-3)
        """
        try:
            import tiktoken
        except ImportError as e:
            raise ImportError(
                "tiktoken is required for TiktokenTokenizer. "
                "Install it with: pip install tiktoken"
            ) from e

        self._encoding = tiktoken.get_encoding(model_name)
        self.model_name = model_name

    def encode(self, text: str) -> list[int]:
        """将文本编码为Token ID列表"""
        return self._encoding.encode(text)

    def decode(self, tokens: list[int]) -> str:
        """将Token ID列表解码为文本"""
        return self._encoding.decode(tokens)

    def count_tokens(self, text: str) -> int:
        """计算文本中的Token数量"""
        return len(self._encoding.encode(text))

    def __repr__(self) -> str:
        return f"TiktokenTokenizer(model_name={self.model_name!r})"
