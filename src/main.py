import pandas as pd
import argparse
from pathlib import Path
from cleaners.check_vocab import check_vocab, get_concept_node_summary
import json
from enum import Enum

OUTPUT_DIR = Path("output")
REFERENCES_DIR = Path("references")


class ResourceModel(Enum):
    ACTOR = "actor"
    ADMINISTRATIVE_MODEL = "administrative_model"
    CHRONOLOGY = "chronology"
    INFORMATION = "information"
    MAEASAM_GRID = "maeasam_grid"
    REMOTE_SENSING = "remote_sensing"
    SITE = "site"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=Path, required=True)
    parser.add_argument("-o", "--output", type=Path, default=None)
    parser.add_argument(
        "-rt",
        "--resource_model_type",
        type=ResourceModel,
        default=ResourceModel.SITE,
        choices=list(ResourceModel),
    )
    parser.add_argument("-c", "--concepts", type=Path, default=None)
    parser.add_argument("-rf", "--resource_model_file", type=Path, default=None)
    parser.add_argument(
        "--summary", action="store_true", help="Show concept mapping summary"
    )
    args = parser.parse_args()

    if args.output is None:
        args.output = OUTPUT_DIR / f"{args.input.stem}_cleaned.csv"

    if args.concepts is None:
        args.concepts = REFERENCES_DIR / (
            f"{args.resource_model_type.value.replace('_', ' ').title()}_concepts.json"
        )
    if args.resource_model_file is None:
        args.resource_model_file = REFERENCES_DIR / (
            f"{args.resource_model_type.value.replace('_', ' ').title()}.json"
        )

    # Load data
    df = pd.read_csv(args.input, dtype_backend="pyarrow")

    with open(args.concepts) as f:
        concepts = json.load(f)
    with open(args.resource_model_file) as f:
        resource_model = json.load(f)

    # Get concept mappings
    concept_mappings_df = check_vocab(df, resource_model, concepts)

    if args.summary:
        # Show detailed summary
        summary = get_concept_node_summary(resource_model, concepts)

        print("\n" + "=" * 80)
        print("CONCEPT NODE MAPPING SUMMARY")
        print("=" * 80)
        print(f"Total concept nodes found: {summary['total_concept_nodes']}")
        print(f"Nodes with rdmCollection UUIDs: {summary['nodes_with_collections']}")
        print(f"Nodes with collection labels: {summary['nodes_with_labels']}")
        print(f"Nodes with concept categories: {summary['nodes_with_concepts']}")
        print("\nDetailed Mappings:")
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

        print("\n" + "=" * 80)

    # Save the concept mappings to a separate file
    mappings_output = OUTPUT_DIR / f"{args.input.stem}_concept_mappings.csv"
    concept_mappings_df.to_csv(mappings_output, index=False)
    print(f"\nConcept mappings saved to: {mappings_output}")

    # Display the mappings DataFrame
    print(f"\nConcept Node Mappings ({len(concept_mappings_df)} nodes):")
    print("-" * 80)
    print(concept_mappings_df.to_string(index=False))

    # Continue with original functionality
    concepts_nodes = concept_mappings_df["node_name"].tolist()
    print(f"\nConcept nodes found: {concepts_nodes}")


if __name__ == "__main__":
    main()
