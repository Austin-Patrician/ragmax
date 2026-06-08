from ragmax.domain.indexing.entities import IndexNode
from ragmax.infrastructure.qdrant.vector_index_writer import _payload_from_node


def test_qdrant_payload_marks_child_node_role() -> None:
    node = IndexNode(
        node_id="child-1",
        source_id="source-1",
        notebook_id="notebook-1",
        text="Child text",
        modality="text",
        content_type="paragraph",
        parent_node_id="parent-1",
    )

    payload = _payload_from_node(
        node,
        collection_name="ragmax_text_nodes",
        embedding_model="hash-test",
    )

    assert payload["node_role"] == "child"


def test_qdrant_payload_marks_leaf_node_role() -> None:
    node = IndexNode(
        node_id="leaf-1",
        source_id="source-1",
        notebook_id="notebook-1",
        text="Leaf text",
        modality="text",
        content_type="paragraph",
    )

    payload = _payload_from_node(
        node,
        collection_name="ragmax_text_nodes",
        embedding_model="hash-test",
    )

    assert payload["node_role"] == "leaf"
