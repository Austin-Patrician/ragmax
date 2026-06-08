from ragmax.infrastructure.qdrant.sparse_encoder import SparseTextEncoder


def test_sparse_encoder_handles_mixed_chinese_and_english_text() -> None:
    encoder = SparseTextEncoder()

    sparse_vector, terms = encoder.encode("RAGFlow 项目需要 退款审批 workflow")

    assert sparse_vector.indices
    assert sparse_vector.values
    assert len(sparse_vector.indices) == len(sparse_vector.values)
    assert len(set(sparse_vector.indices)) == len(sparse_vector.indices)
    assert "ragflow" in terms


def test_sparse_encoder_is_stable_across_calls() -> None:
    encoder = SparseTextEncoder()

    first_vector, first_terms = encoder.encode("退款 审批 approval")
    second_vector, second_terms = encoder.encode("退款 审批 approval")

    assert first_vector.indices == second_vector.indices
    assert first_vector.values == second_vector.values
    assert first_terms == second_terms
