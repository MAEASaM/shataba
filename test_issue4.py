#!/usr/bin/env python3
"""
Test script for Issue 4: Concept Node Mapping

This script demonstrates the solution for building links between concept nodes
in Site.json and their corresponding English labels through collections.xml
and Site_concepts.json.
"""

import json
import pandas as pd
from pathlib import Path
import sys

sys.path.append("src")

from cleaners.check_vocab import (
    get_concept_node_summary,
    parse_collections_xml,
    get_concept_nodes_with_collections,
    find_concept_category,
)


def test_issue4_solution():
    """Test the complete solution for issue 4."""

    print("=" * 80)
    print("ISSUE 4: CONCEPT NODE MAPPING SOLUTION")
    print("=" * 80)

    # Load the reference files
    references_dir = Path("references")

    # Load Site.json
    site_json_path = references_dir / "Site.json"
    if not site_json_path.exists():
        print(f"Error: {site_json_path} not found")
        return

    with open(site_json_path) as f:
        resource_model = json.load(f)

    # Load Site_concepts.json
    concepts_json_path = references_dir / "Site_concepts.json"
    if not concepts_json_path.exists():
        print(f"Error: {concepts_json_path} not found")
        return

    with open(concepts_json_path) as f:
        concepts = json.load(f)

    print(f"\n1. Loaded resource model from: {site_json_path}")
    print(f"2. Loaded concepts from: {concepts_json_path}")

    # Test parsing collections.xml
    print("\n3. Parsing collections.xml...")
    collections_mapping = parse_collections_xml()
    print(f"   Found {len(collections_mapping)} collection mappings")

    # Show some examples of collection mappings
    print("\n   Example collection mappings:")
    for i, (uuid, info) in enumerate(list(collections_mapping.items())[:5]):
        print(f"   {i + 1}. UUID: {uuid}")
        print(f"      Label: {info.get('label', 'N/A')}")
        print(f"      Label ID: {info.get('label_id', 'N/A')}")

    # Test getting concept nodes with collections
    print("\n4. Extracting concept nodes with collections...")
    concept_nodes = get_concept_nodes_with_collections(resource_model)
    print(f"   Found {len(concept_nodes)} concept nodes")

    # Show concept nodes with collections
    print("\n   Concept nodes with rdmCollection UUIDs:")
    for node_name, node_info in concept_nodes.items():
        if node_info.get("rdm_collection_uuid"):
            print(f"   - {node_name}")
            print(f"     Node ID: {node_info.get('node_id')}")
            print(f"     rdmCollection: {node_info.get('rdm_collection_uuid')}")

            # Get the collection label
            collection_info = collections_mapping.get(
                node_info.get("rdm_collection_uuid"), {}
            )
            collection_label = collection_info.get("label", "Not found")
            print(f"     Collection Label: {collection_label}")

            # Find concept category
            concept_category = find_concept_category(collection_label, concepts)
            if concept_category:
                print(f"     Concept Category: {concept_category}")
                concept_count = len(concepts.get(concept_category, {}))
                print(f"     Available Concepts: {concept_count}")
            else:
                print(f"     Concept Category: Not found")
            print()

    # Test the complete summary
    print("\n5. Generating complete summary...")
    summary = get_concept_node_summary(resource_model, concepts)

    print(f"\nSUMMARY RESULTS:")
    print(f"   Total concept nodes: {summary['total_concept_nodes']}")
    print(f"   Nodes with rdmCollection UUIDs: {summary['nodes_with_collections']}")
    print(f"   Nodes with collection labels: {summary['nodes_with_labels']}")
    print(f"   Nodes with concept categories: {summary['nodes_with_concepts']}")

    # Show detailed mappings
    print(f"\nDETAILED MAPPINGS:")
    print("-" * 80)

    for node_name, mapping in summary["mappings"].items():
        print(f"\nNode: {node_name}")
        print(f"  Node ID: {mapping['node_id']}")
        print(f"  Has Collection: {mapping['has_collection']}")
        print(f"  Has Label: {mapping['has_label']}")
        print(f"  Has Concepts: {mapping['has_concepts']}")

        if mapping["collection_label"]:
            print(f"  Collection Label: {mapping['collection_label']}")

        if mapping["concept_category"]:
            print(f"  Concept Category: {mapping['concept_category']}")
            concept_count = len(concepts.get(mapping["concept_category"], {}))
            print(f"  Available Concepts: {concept_count}")

    print("\n" + "=" * 80)
    print("ISSUE 4 SOLUTION COMPLETE")
    print("=" * 80)

    # Save results to output
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Create a summary report
    report_data = []
    for node_name, mapping in summary["mappings"].items():
        report_data.append(
            {
                "node_name": node_name,
                "node_id": mapping["node_id"],
                "has_collection": mapping["has_collection"],
                "has_label": mapping["has_label"],
                "has_concepts": mapping["has_concepts"],
                "collection_label": mapping["collection_label"],
                "concept_category": mapping["concept_category"],
            }
        )

    report_df = pd.DataFrame(report_data)
    report_path = output_dir / "issue4_concept_mapping_report.csv"
    report_df.to_csv(report_path, index=False)
    print(f"\nDetailed report saved to: {report_path}")

    return summary


if __name__ == "__main__":
    test_issue4_solution()
