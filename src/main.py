import pandas as pd
import argparse
from pathlib import Path
from cleaners.check_vocab import check_vocab
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
    args = parser.parse_args()

    if args.output is None:
        args.output = OUTPUT_DIR / f"{args.input.stem}_cleaned.csv"

    if args.concepts is None:
        args.concepts = REFERENCES_DIR / (
            f"{args.resource_model_type.value.replace('_', ' ').title()}_concepts.json"
        )

    df = pd.read_csv(args.input, dtype_backend="pyarrow")  # use_nullable_dtypes=True)

    concepts = json.load(open(args.concepts))
    resource_model = json.load(open(args.resource_model_file))

    concepts_nodes = check_vocab(df, resource_model, concepts)
    print(concepts_nodes)


if __name__ == "__main__":
    main()
