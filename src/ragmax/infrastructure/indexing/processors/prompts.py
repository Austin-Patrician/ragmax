# Vision prompts
IMAGE_ANALYSIS_SYSTEM = "You are an expert image analyst. Provide detailed, accurate descriptions."

VISION_PROMPT_WITH_CONTEXT = """Analyze this image considering the surrounding context. Return JSON:

{{
    "detailed_description": "Comprehensive visual description with:
    - Overall composition and layout
    - All objects, people, text, visual elements
    - Relationships between elements and to surrounding context
    - Colors, lighting, visual style
    - Actions or activities shown
    - Technical details (charts, diagrams, etc.)
    - Always use specific names, not pronouns",
    "entity_info": {{
        "entity_name": "{entity_name}",
        "entity_type": "image",
        "summary": "Concise summary with significance and context relationship (max 100 words)"
    }}
}}

Context: {context}

Section: {section_path}
Image: {image_path}
Captions: {captions}
Footnotes: {footnotes}

Use semantic entity_name, not file names."""

TABLE_ANALYSIS_SYSTEM = "You are an expert data analyst. Provide detailed table analysis."

TABLE_PROMPT_WITH_CONTEXT = """Analyze this table considering context. Return JSON:

{{
    "detailed_description": "Table analysis with structure, key data, insights, and context relationship",
    "entity_info": {{
        "entity_name": "{entity_name}",
        "entity_type": "table",
        "summary": "Concise summary (max 100 words)"
    }}
}}

Context: {context}
Section: {section_path}
Table: {table_body}
Captions: {captions}"""
