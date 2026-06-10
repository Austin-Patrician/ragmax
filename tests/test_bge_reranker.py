import pytest

from ragmax.application.retrieval.dtos import RetrievalCitation, RetrievedNode
from ragmax.core.exceptions import ConfigurationError
from ragmax.domain.indexing.entities import IndexNode
from ragmax.infrastructure.retrieval.rerankers import bge_reranker
from ragmax.infrastructure.retrieval.rerankers.bge_reranker import BGECrossEncoderReranker


class FakeCrossEncoder:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.predict_calls = 0

    def predict(
        self,
        inputs,
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> list[float]:
        del batch_size, show_progress_bar
        self.predict_calls += 1
        return self.scores[: len(inputs)]


@pytest.mark.asyncio
async def test_bge_reranker_loads_model_on_first_request_only() -> None:
    factory_calls = 0
    fake_model = FakeCrossEncoder([0.2, 1.4])

    def factory(model_name: str, device: str, max_length: int) -> FakeCrossEncoder:
        nonlocal factory_calls
        assert model_name == "test-model"
        assert device == "cpu"
        assert max_length == 256
        factory_calls += 1
        return fake_model

    reranker = BGECrossEncoderReranker(
        model_name="test-model",
        device="cpu",
        batch_size=2,
        max_length=256,
        cross_encoder_factory=factory,
    )

    assert factory_calls == 0
    nodes = (
        _retrieved_node("node-1", "refund policy"),
        _retrieved_node("node-2", "approval workflow"),
    )

    first = await reranker.rerank(query="approval", nodes=nodes, top_k=2)
    second = await reranker.rerank(query="approval", nodes=nodes, top_k=1)

    assert factory_calls == 1
    assert fake_model.predict_calls == 2
    assert [item.retrieved_node.node.node_id for item in first] == ["node-2", "node-1"]
    assert [item.retrieved_node.node.node_id for item in second] == ["node-2"]


@pytest.mark.asyncio
async def test_bge_default_factory_reuses_cached_model_across_instances(monkeypatch) -> None:
    factory_calls = 0
    fake_model = FakeCrossEncoder([0.2])

    def load_model(model_name: str, device: str, max_length: int) -> FakeCrossEncoder:
        nonlocal factory_calls
        assert model_name == "cached-model"
        assert device == "cpu"
        assert max_length == 256
        factory_calls += 1
        return fake_model

    bge_reranker._cached_cross_encoder.cache_clear()
    monkeypatch.setattr(bge_reranker, "_load_cross_encoder", load_model)

    first = BGECrossEncoderReranker(model_name="cached-model", max_length=256)
    second = BGECrossEncoderReranker(model_name="cached-model", max_length=256)
    nodes = (_retrieved_node("node-1", "refund policy"),)

    await first.rerank(query="refund", nodes=nodes, top_k=1)
    await second.rerank(query="refund", nodes=nodes, top_k=1)

    assert factory_calls == 1
    assert fake_model.predict_calls == 2
    bge_reranker._cached_cross_encoder.cache_clear()


@pytest.mark.asyncio
async def test_bge_reranker_raises_configuration_error_when_lazy_load_fails() -> None:
    def factory(model_name: str, device: str, max_length: int):
        del model_name, device, max_length
        raise RuntimeError("model cache missing")

    reranker = BGECrossEncoderReranker(cross_encoder_factory=factory)

    with pytest.raises(ConfigurationError, match="failed to load"):
        await reranker.rerank(
            query="approval",
            nodes=(_retrieved_node("node-1", "approval workflow"),),
            top_k=1,
        )


def _retrieved_node(node_id: str, text: str) -> RetrievedNode:
    node = IndexNode(
        node_id=node_id,
        source_id="source-1",
        notebook_id="notebook-1",
        text=text,
        modality="text",
        content_type="paragraph",
    )
    return RetrievedNode(
        node=node,
        score=0.5,
        collection_name="ragmax_text_nodes",
        citation=RetrievalCitation(
            source_id=node.source_id,
            node_id=node.node_id,
            filename="guide.md",
            page_label=None,
            section_path=(),
        ),
    )
