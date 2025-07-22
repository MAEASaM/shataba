import pandas as pd
import argparse
from pathlib import Path
from cleaners.check_vocab import (
    check_vocab,
    get_concept_node_summary,
    create_offending_values_table,
)
import json
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich import print as rprint
from typing import Dict

OUTPUT_DIR = Path("output")
REFERENCES_DIR = Path("references")
console = Console()


class ResourceModel(Enum):
    ACTOR = "actor"
    ADMINISTRATIVE_MODEL = "administrative_model"
    CHRONOLOGY = "chronology"
    INFORMATION = "information"
    MAEASAM_GRID = "maeasam_grid"
    REMOTE_SENSING = "remote_sensing"
    SITE = "site"


def create_summary_table(summary: dict) -> Table:
    """Create a rich table for the concept mapping summary."""
    table = Table(
        title="Concept Node Mapping Summary",
        show_header=True,
        header_style="bold magenta",
    )

    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="green")
    table.add_column("Percentage", justify="right", style="yellow")

    total = summary["total_concept_nodes"]

    metrics = [
        ("Total Concept Nodes", summary["total_concept_nodes"], "100%"),
        (
            "Nodes with Collections",
            summary["nodes_with_collections"],
            f"{summary['nodes_with_collections'] / total * 100:.1f}%",
        ),
        (
            "Nodes with Labels",
            summary["nodes_with_labels"],
            f"{summary['nodes_with_labels'] / total * 100:.1f}%",
        ),
        (
            "Nodes with Concepts",
            summary["nodes_with_concepts"],
            f"{summary['nodes_with_concepts'] / total * 100:.1f}%",
        ),
    ]

    for metric, count, percentage in metrics:
        table.add_row(metric, str(count), percentage)

    return table


def create_mappings_table(summary: dict) -> Table:
    """Create a rich table for detailed mappings."""
    table = Table(
        title="Detailed Concept Node Mappings",
        show_header=True,
        header_style="bold blue",
    )

    table.add_column("Node Name", style="cyan", no_wrap=True)
    table.add_column("Node ID", style="dim")
    table.add_column("Collection", style="green")
    table.add_column("Label", style="yellow")
    table.add_column("Concepts", style="magenta")

    for node_name, mapping in summary["mappings"].items():
        collection_status = "✅" if mapping["has_collection"] else "❌"
        label_status = "✅" if mapping["has_label"] else "❌"
        concepts_status = "✅" if mapping["has_concepts"] else "❌"

        table.add_row(
            node_name,
            mapping["node_id"] or "N/A",
            collection_status,
            label_status,
            concepts_status,
        )

    return table


def create_concept_mappings_table(concept_mappings_df: pd.DataFrame) -> Table:
    """Create a rich table for concept mappings DataFrame."""
    table = Table(
        title="Concept Node Mappings", show_header=True, header_style="bold green"
    )

    # Add columns based on DataFrame columns
    for col in concept_mappings_df.columns:
        if col == "node_name":
            table.add_column(col, style="cyan", no_wrap=True)
        elif col == "available_concepts":
            table.add_column(col, justify="right", style="green")
        else:
            table.add_column(col, style="dim")

    # Add rows
    # Preprocess DataFrame: fill missing values and convert all values to strings
    concept_mappings_df = concept_mappings_df.fillna("N/A").astype(str)

    for row in concept_mappings_df.itertuples(index=False):
        table.add_row(*row)
    return table


def create_validation_report_table(validation_report: Dict) -> Table:
    """Create a Rich table for validation report."""
    table = Table(title="Concept Validation Report")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="magenta")

    table.add_row("Total Rows Processed", str(validation_report.get("total_rows", 0)))
    table.add_row(
        "Columns Checked", str(len(validation_report.get("columns_checked", [])))
    )
    table.add_row(
        "Offending Values Found",
        str(validation_report.get("offending_values_found", 0)),
    )
    table.add_row(
        "Offending Values Removed",
        str(validation_report.get("offending_values_removed", 0)),
    )
    table.add_row("Values Cleaned", str(validation_report.get("values_cleaned", 0)))

    return table


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

    # Show startup information
    console.print(
        Panel.fit(
            f"[bold blue]Shataba[/bold blue] - Data Cleaning Tool\n"
            f"[dim]Processing:[/dim] {args.input.name}\n"
            f"[dim]Resource Model:[/dim] {args.resource_model_type.value}",
            title="🚀 Starting Processing",
        )
    )

    # Load data with progress indication
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading data...", total=None)

        # Load CSV data
        progress.update(task, description="Loading CSV data...")
        df = pd.read_csv(args.input, dtype_backend="pyarrow")

        # Load JSON files
        progress.update(task, description="Loading concepts file...")
        with open(args.concepts) as f:
            concepts = json.load(f)

        progress.update(task, description="Loading resource model...")
        with open(args.resource_model_file) as f:
            resource_model = json.load(f)

        progress.update(task, description="Processing concept mappings...")
        concept_mappings_df, cleaned_df, validation_report = check_vocab(
            df, resource_model, concepts
        )

        progress.update(task, description="Complete!", completed=True)

    # Display validation results
    console.print("\n")
    console.print(create_validation_report_table(validation_report))

    if validation_report["offending_values_found"] > 0:
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

    # Display results
    if args.summary:
        # Show detailed summary with Rich formatting
        summary = get_concept_node_summary(resource_model, concepts)

        console.print("\n")
        console.print(create_summary_table(summary))
        console.print("\n")
        console.print(create_mappings_table(summary))

    # Save the cleaned data to the output file
    cleaned_df.to_csv(args.output, index=False)
    console.print(
        f"\n[green]✓[/green] Cleaned data saved to: [cyan]{args.output}[/cyan]"
    )

    # Save the concept mappings to a separate file
    mappings_output = OUTPUT_DIR / f"{args.input.stem}_concept_mappings.csv"
    concept_mappings_df.to_csv(mappings_output, index=False)

    console.print(
        f"\n[green]✓[/green] Concept mappings saved to: [cyan]{mappings_output}[/cyan]"
    )

    # Display the mappings DataFrame with Rich table
    console.print("\n")
    console.print(create_concept_mappings_table(concept_mappings_df))

    # Continue with original functionality
    concepts_nodes = concept_mappings_df["node_name"].tolist()

    console.print(f"\n[bold green]✓[/bold green] Processing complete!")
    console.print(f"[dim]Found {len(concepts_nodes)} concept nodes[/dim]")


if __name__ == "__main__":
    main()
