import pandas as pd
from glom import glom


def check_vocab(
    df: pd.DataFrame, resource_model: dict[str, dict[str, list[dict[str, str]]]], concepts: dict[str, list[str]]
) -> pd.DataFrame:
    concepts_nodes = get_type_concept(resource_model)
    return concepts_nodes


def get_type_concept(resource_model: dict[str, dict[str, list[dict[str, str]]]]) -> list[str]:
    nodes = glom(resource_model, "graph.0.nodes")
    concepts_nodes = []
    for node in nodes:
        if node["datatype"] in ["concept-list", "concept"]:
            concepts_nodes.append(node["name"])
    return concepts_nodes
