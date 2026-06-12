"""默认配置 - Chunker和Parser的默认值"""

# 默认Chunker
DEFAULT_CHUNKER = "fixed_token"

# 默认Parser映射（根据media_type）
DEFAULT_PARSER_MAPPING = {
    "application/pdf": "llamaparse",
    "text/plain": "simple_directory_reader",
    "text/markdown": "simple_directory_reader",
    "text/csv": "simple_directory_reader",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "llamaparse",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "llamaparse",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "llamaparse",
    "image/jpeg": "llamaparse",
    "image/png": "llamaparse",
}

# 默认Chunk配置（每个chunker的默认参数）
DEFAULT_CHUNK_CONFIGS = {
    "fixed_token": {
        "chunk_size": 1000,
        "chunk_overlap": 100,
        "tokenizer_model": "cl100k_base",
    },
    "semantic_vector": {
        "chunk_size": 1000,
        "chunk_overlap": 0,  # 语义边界不需要overlap
        "similarity_threshold_percentile": 75,
        "tokenizer_model": "cl100k_base",
    },
    "section_aware": {
        "chunk_size": 800,
        "chunk_overlap": 100,
        "tokenizer_model": "cl100k_base",
        "keep_headings": True,
    },
    "table_aware": {
        "chunk_size": 600,
        "chunk_overlap": 80,
        "repeat_table_header": True,
        "tokenizer_model": "cl100k_base",
    },
    "ocr_page": {
        "chunk_size": 500,
        "chunk_overlap": 80,
        "preserve_bbox": True,
        "tokenizer_model": "cl100k_base",
    },
}


def get_default_parser(media_type: str) -> str:
    """根据media_type获取默认parser"""
    return DEFAULT_PARSER_MAPPING.get(media_type, "simple_directory_reader")


def get_default_chunk_config(chunker: str) -> dict:
    """根据chunker名称获取默认配置"""
    return DEFAULT_CHUNK_CONFIGS.get(chunker, DEFAULT_CHUNK_CONFIGS["fixed_token"]).copy()
