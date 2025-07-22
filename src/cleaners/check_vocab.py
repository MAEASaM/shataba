import pandas as pd
import xml.etree.ElementTree as ET
from glom import glom
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

# Regex patterns for parsing JSON-like structures in XML
ID_PATTERN = re.compile(r'"id":\s*"([^"]+)"')
"""Regex pattern to extract the value of the "id" field from a JSON-like string in XML.
Matches strings of the format: '"id": "some_value"'.
Captures the value of the "id" field (e.g., 'some_value')."""
VALUE_PATTERN = re.compile(r'"value":\s*"([^"]+)"')
"""Regex pattern to extract the value of the "value" field from a JSON-like string in XML.
Matches strings of the format: '"value": "some_value"'.
Captures the value of the "value" field (e.g., 'some_value')."""

console = Console()


def validate_and_clean_concept_values(
    df: pd.DataFrame, resource_model: dict, concepts: dict
) -> Tuple[pd.DataFrame, Dict]:
    """
    Validate concept values against acceptable concepts and remove offending values.

    Args:
        df: Input DataFrame
        resource_model: Site.json structure
        concepts: Site_concepts.json structure

    Returns:
        Tuple of (cleaned_dataframe, validation_report)
    """
    # Get concept mappings to identify which columns are concept fields
    concept_mappings = build_concept_mappings(resource_model, concepts)

    # Create a mapping of column names to their concept categories
    column_to_concept = {}
    for node_name, mapping in concept_mappings.items():
        concept_category = mapping.get("concept_category")
        if concept_category:
            # Map the node name to its concept category
            column_to_concept[node_name] = concept_category

    validation_report = {
        "total_rows": len(df),
        "columns_checked": [],
        "offending_values_found": 0,
        "offending_values_removed": 0,
        "details": {},
    }

    # Create a copy of the dataframe and convert to object dtype to avoid PyArrow issues
    cleaned_df = df.copy()

    def normalize_value(value):
        """Normalize a value for comparison by removing non-alphanumeric characters and converting to lowercase."""
        if pd.isna(value) or value == "":
            return ""
        # Convert to string, remove non-alphanumeric characters, convert to lowercase
        return re.sub(r"[^a-zA-Z0-9]", "", str(value).lower())

    # Check each concept column
    for column_name, concept_category in column_to_concept.items():
        # Find the actual column in the dataframe (case-insensitive matching)
        matching_column = None
        for actual_column in cleaned_df.columns:
            if actual_column.lower() == column_name.lower():
                matching_column = actual_column
                break

        if matching_column:
            validation_report["columns_checked"].append(matching_column)

            # Get acceptable values for this concept category and normalize them
            acceptable_values_raw = set(concepts.get(concept_category, {}).values())
            acceptable_values_normalized = {
                normalize_value(val) for val in acceptable_values_raw
            }

            # Convert column to string type to avoid PyArrow issues
            column_data = cleaned_df[matching_column].astype("string[pyarrow]")

            # Normalize the column data for comparison
            column_data_normalized = column_data.apply(normalize_value)

            # Find offending values (values that don't match any normalized acceptable value)
            offending_mask = ~column_data_normalized.isin(
                acceptable_values_normalized
            ) & (column_data_normalized != "")

            if offending_mask.any():
                offending_count = offending_mask.sum()
                validation_report["offending_values_found"] += offending_count
                validation_report["details"][matching_column] = {
                    "concept_category": concept_category,
                    "offending_count": offending_count,
                    "offending_values": column_data[offending_mask].unique().tolist(),
                    "acceptable_count": len(acceptable_values_raw),
                    "sample_acceptable_values": list(acceptable_values_raw)[
                        :5
                    ],  # Show first 5 acceptable values
                }

                # Convert the column to object dtype to allow string assignment
                cleaned_df[matching_column] = cleaned_df[matching_column].astype(
                    "string[pyarrow]"
                )

                # Remove offending values by setting them to empty string
                cleaned_df.loc[offending_mask, matching_column] = ""
                validation_report["offending_values_removed"] += offending_count

                console.print(
                    Panel(
                        Text(
                            f"Found {offending_count} offending values in column '{matching_column}' "
                            f"(concept category: {concept_category}). Values removed.",
                            style="yellow",
                        ),
                        title="Validation Warning",
                    )
                )

    return cleaned_df, validation_report


def create_validation_report_table(validation_report: dict) -> Table:
    """Create a rich table for the validation report."""
    table = Table(
        title="Concept Validation Report", show_header=True, header_style="bold red"
    )

    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="green")

    metrics = [
        ("Total Rows Processed", validation_report["total_rows"]),
        ("Columns Checked", len(validation_report["columns_checked"])),
        ("Offending Values Found", validation_report["offending_values_found"]),
        ("Offending Values Removed", validation_report["offending_values_removed"]),
    ]

    for metric, count in metrics:
        table.add_row(metric, str(count))

    return table


def create_offending_values_table(validation_report: dict) -> Table:
    """Create a rich table showing detailed offending values."""
    if not validation_report["details"]:
        return None

    table = Table(
        title="Detailed Offending Values", show_header=True, header_style="bold yellow"
    )

    table.add_column("Column", style="cyan", no_wrap=True)
    table.add_column("Concept Category", style="blue")
    table.add_column("Offending Count", justify="right", style="red")
    table.add_column("Acceptable Count", justify="right", style="green")
    table.add_column("Sample Offending Values", style="dim")
    table.add_column("Sample Acceptable Values", style="green")

    for column_name, details in validation_report["details"].items():
        sample_values = details["offending_values"][:3]  # Show first 3 values
        sample_text = ", ".join(sample_values)
        if len(details["offending_values"]) > 3:
            sample_text += f" ... (+{len(details['offending_values']) - 3} more)"

        sample_acceptable = details.get("sample_acceptable_values", [])
        sample_acceptable_text = ", ".join(sample_acceptable[:3])
        if len(sample_acceptable) > 3:
            sample_acceptable_text += f" ... (+{len(sample_acceptable) - 3} more)"

        table.add_row(
            column_name,
            details["concept_category"],
            str(details["offending_count"]),
            str(details["acceptable_count"]),
            sample_text,
            sample_acceptable_text,
        )

    return table


def check_vocab(
    df: pd.DataFrame,
    resource_model: dict[str, dict[str, list[dict[str, str]]]],
    concepts: dict[str, list[str]],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Check vocabulary, validate concept values, and build concept node mappings.

    Args:
        df: Input DataFrame
        resource_model: Site.json structure
        concepts: Site_concepts.json structure

    Returns:
        Tuple of (concept_mappings_dataframe, cleaned_dataframe)
    """
    # Validate and clean concept values first
    console.print(
        Panel(
            Text(
                "Validating concept values against acceptable concepts...", style="blue"
            ),
            title="🔍 Validation Phase",
        )
    )

    cleaned_df, validation_report = validate_and_clean_concept_values(
        df, resource_model, concepts
    )

    # Display validation results
    if validation_report["offending_values_found"] > 0:
        console.print("\n")
        console.print(create_validation_report_table(validation_report))

        detailed_table = create_offending_values_table(validation_report)
        if detailed_table:
            console.print("\n")
            console.print(detailed_table)
    else:
        console.print(
            Panel(
                Text("✅ All concept values are valid!", style="green"),
                title="Validation Complete",
            )
        )

    # Get concept nodes from resource model
    concept_nodes = get_type_concept(resource_model)

    # Build the complete mapping
    concept_mappings = build_concept_mappings(resource_model, concepts)

    # Create a DataFrame with the mappings
    mapping_data = []
    for node_name, mapping in concept_mappings.items():
        mapping_data.append(
            {
                "node_name": node_name,
                "node_id": mapping.get("node_id"),
                "rdm_collection_uuid": mapping.get("rdm_collection_uuid"),
                "collection_label": mapping.get("collection_label"),
                "collection_label_id": mapping.get("collection_label_id"),
                "concept_category": mapping.get("concept_category"),
                "available_concepts": len(mapping.get("available_concepts", [])),
            }
        )

    return pd.DataFrame(mapping_data), cleaned_df


def get_type_concept(
    resource_model: dict[str, dict[str, list[dict[str, str]]]],
) -> List[str]:
    """
    Extract concept nodes from resource model.

    Args:
        resource_model: Site.json structure

    Returns:
        List of concept node names
    """
    nodes = glom(resource_model, "graph.0.nodes")
    concepts_nodes = []
    for node in nodes:
        if node.get("datatype") in ["concept-list", "concept"]:
            concepts_nodes.append(node.get("name", ""))
    return concepts_nodes


def build_concept_mappings(resource_model: dict, concepts: dict) -> Dict[str, Dict]:
    """
    Build complete mappings between concept nodes and their labels.

    Args:
        resource_model: Site.json structure
        concepts: Site_concepts.json structure

    Returns:
        Dictionary mapping node names to their complete information
    """
    # Parse collections.xml to get UUID to label mappings
    collections_mapping = parse_collections_xml()

    # Get concept nodes with their rdmCollection UUIDs
    concept_nodes = get_concept_nodes_with_collections(resource_model)

    # Build the complete mapping
    mappings = {}

    for node_name, node_info in concept_nodes.items():
        rdm_collection_uuid = node_info.get("rdm_collection_uuid")

        if rdm_collection_uuid:
            # Get collection label from collections.xml
            collection_info = collections_mapping.get(rdm_collection_uuid, {})
            collection_label = collection_info.get("label", "")
            collection_label_id = collection_info.get("label_id", "")

            # Find the concept category in Site_concepts.json
            concept_category = find_concept_category(collection_label, concepts)
            available_concepts = (
                concepts.get(concept_category, {}) if concept_category else {}
            )

            mappings[node_name] = {
                "node_id": node_info.get("node_id"),
                "rdm_collection_uuid": rdm_collection_uuid,
                "collection_label": collection_label,
                "collection_label_id": collection_label_id,
                "concept_category": concept_category,
                "available_concepts": available_concepts,
            }
        else:
            mappings[node_name] = {
                "node_id": node_info.get("node_id"),
                "rdm_collection_uuid": None,
                "collection_label": None,
                "collection_label_id": None,
                "concept_category": None,
                "available_concepts": {},
            }

    return mappings


def parse_collections_xml(
    collections_file_path: Optional[str] = "references/collections.xml",
) -> Dict[str, Dict]:
    """
    Parse collections.xml to extract UUID to label mappings.

    Args:
        collections_file_path: Path to the collections.xml file. Defaults to "references/collections.xml".

    Returns:
        Dictionary mapping collection UUIDs to their labels
    """
    collections_file = Path(collections_file_path)
    if not collections_file.exists():
        console.print(
            Panel(
                Text(
                    f"Warning: {collections_file} not found. Ensure the file exists at the expected location ('references/collections.xml') or consult the documentation for instructions on how to obtain it.",
                    style="yellow",
                ),
                title="Warning",
            )
        )
        return {}

    try:
        tree = ET.parse(collections_file)
        root = tree.getroot()

        # Define namespaces including xml namespace
        namespaces = {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "xml": "http://www.w3.org/XML/1998/namespace",
        }

        collections_mapping = {}

        # Find all skos:Collection elements
        for collection in root.findall(".//skos:Collection", namespaces):
            collection_uri = collection.get(
                "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"
            )

            if collection_uri:
                # Extract UUID from URI
                uuid = collection_uri.split("/")[-1]

                # Find the prefLabel with xml:lang="en"
                pref_label = collection.find(
                    './/skos:prefLabel[@xml:lang="en"]', namespaces
                )

                if pref_label is not None:
                    label_text = pref_label.text
                    if label_text and label_text.startswith('{"id":'):
                        try:
                            # Parse the JSON-like structure

                            id_match = ID_PATTERN.search(label_text)
                            value_match = VALUE_PATTERN.search(label_text)

                            if id_match and value_match:
                                label_id = id_match.group(1)
                                label_value = value_match.group(1)

                                collections_mapping[uuid] = {
                                    "label": label_value,
                                    "label_id": label_id,
                                }
                        except Exception as e:
                            console.print(
                                Panel(
                                    Text(
                                        f"Error parsing label for collection {uuid}. Label text: {label_text}. Error: {e}",
                                        style="red",
                                    ),
                                    title="Error",
                                )
                            )

        return collections_mapping

    except ET.ParseError as e:
        console.print(
            Panel(
                Text(
                    f"Error parsing collections.xml at {collections_file}: Malformed XML. {e}. "
                    f"Please ensure the file is well-formed XML.",
                    style="red",
                ),
                title="Error",
            )
        )
        return {}
    except FileNotFoundError as e:
        console.print(
            Panel(
                Text(
                    f"Error: collections.xml file not found at {collections_file}. {e}. "
                    f"Please check the file path and ensure the file exists.",
                    style="red",
                ),
                title="Error",
            )
        )
        return {}
    except PermissionError as e:
        console.print(
            Panel(
                Text(
                    f"Error: Permission denied when accessing collections.xml at {collections_file}. {e}. "
                    f"Please check the file permissions.",
                    style="red",
                ),
                title="Error",
            )
        )
        return {}


def get_concept_nodes_with_collections(resource_model: dict) -> Dict[str, Dict]:
    """
    Extract concept nodes with their rdmCollection UUIDs from resource model.

    Args:
        resource_model: Site.json structure

    Returns:
        Dictionary mapping node names to their collection information
    """
    nodes = glom(resource_model, "graph.0.nodes")
    concept_nodes = {}

    for node in nodes:
        if node.get("datatype") in ["concept-list", "concept"]:
            node_name = node.get("name", "")
            node_id = node.get("nodeid", "")

            # Extract rdmCollection UUID from config
            rdm_collection_uuid = None
            config = node.get("config", {})

            if isinstance(config, dict):
                rdm_collection_uuid = config.get("rdmCollection")

            concept_nodes[node_name] = {
                "node_id": node_id,
                "rdm_collection_uuid": rdm_collection_uuid,
            }

    return concept_nodes


def find_concept_category(collection_label: str, concepts: dict) -> Optional[str]:
    """
    Find the concept category in Site_concepts.json that matches the collection label.

    Args:
        collection_label: Label from collections.xml
        concepts: Site_concepts.json structure

    Returns:
        Category name if found, None otherwise
    """
    if not collection_label:
        return None

    # Direct match
    if collection_label in concepts:
        return collection_label

    # Try to find partial matches
    for category in concepts.keys():
        if (
            collection_label.lower() in category.lower()
            or category.lower() in collection_label.lower()
        ):
            return category

    return None


def get_concept_node_summary(resource_model: dict, concepts: dict) -> Dict:
    """
    Get a summary of all concept nodes and their mappings.

    Args:
        resource_model: Site.json structure
        concepts: Site_concepts.json structure

    Returns:
        Summary dictionary
    """
    collections_mapping = parse_collections_xml()
    concept_nodes = get_concept_nodes_with_collections(resource_model)

    summary = {
        "total_concept_nodes": len(concept_nodes),
        "nodes_with_collections": 0,
        "nodes_with_labels": 0,
        "nodes_with_concepts": 0,
        "mappings": {},
    }

    for node_name, node_info in concept_nodes.items():
        rdm_collection_uuid = node_info.get("rdm_collection_uuid")
        mapping_info = {
            "node_id": node_info.get("node_id"),
            "has_collection": bool(rdm_collection_uuid),
            "has_label": False,
            "has_concepts": False,
            "collection_label": None,
            "concept_category": None,
        }

        if rdm_collection_uuid:
            summary["nodes_with_collections"] += 1

            collection_info = collections_mapping.get(rdm_collection_uuid, {})
            collection_label = collection_info.get("label", "")

            if collection_label:
                mapping_info["has_label"] = True
                mapping_info["collection_label"] = collection_label
                summary["nodes_with_labels"] += 1

                concept_category = find_concept_category(collection_label, concepts)
                if concept_category:
                    mapping_info["has_concepts"] = True
                    mapping_info["concept_category"] = concept_category
                    summary["nodes_with_concepts"] += 1

        summary["mappings"][node_name] = mapping_info

    return summary
