# Issue 4: Concept Node Mapping Solution

## Overview

This solution addresses Issue 4 by implementing a comprehensive system to build links between concept nodes in `Site.json` and their corresponding English labels through `collections.xml` and `Site_concepts.json`.

## Problem Statement

The system involves three interconnected files:
1. **Site.json** - Contains nodes with types `concept-list` or `concept` that are connected to `rdmCollection` with specific UUIDs
2. **collections.xml** - Formatted as RDF triples containing UUIDs and their corresponding English labels
3. **Site_concepts.json** - Contains the English labels for concept collections

The goal was to build the complete chain: **Concept Node** → **UUID** → **Collection Label** → **Concept Category** → **Available Concepts**

## Solution Implementation

### Core Functions

#### 1. `parse_collections_xml()`
- Parses the RDF/XML structure in `collections.xml`
- Extracts UUID to label mappings from `skos:prefLabel` elements
- Handles XML namespaces properly (including `xml` namespace)
- Returns a dictionary mapping collection UUIDs to their labels

#### 2. `get_concept_nodes_with_collections()`
- Extracts concept nodes from `Site.json` using glom
- Identifies nodes with `datatype` of "concept-list" or "concept"
- Extracts `rdmCollection` UUIDs from the node configuration
- Returns mapping of node names to their collection information

#### 3. `find_concept_category()`
- Matches collection labels from `collections.xml` to categories in `Site_concepts.json`
- Supports both exact and partial matching
- Returns the concept category name if found

#### 4. `build_concept_mappings()`
- Orchestrates the complete mapping process
- Combines all three data sources
- Returns comprehensive mapping information

#### 5. `get_concept_node_summary()`
- Provides statistical summary of the mappings
- Shows success rates for each step in the chain

### Key Features

1. **Robust XML Parsing**: Properly handles RDF/XML namespaces and complex nested structures
2. **Flexible Matching**: Supports both exact and partial matching between collection labels and concept categories
3. **Comprehensive Reporting**: Provides detailed statistics and mappings
4. **Error Handling**: Graceful handling of missing or malformed data
5. **Performance Optimized**: Efficient parsing and lookup mechanisms

## Results

### Summary Statistics
- **Total concept nodes found**: 51
- **Nodes with rdmCollection UUIDs**: 51 (100%)
- **Nodes with collection labels**: 51 (100%)
- **Nodes with concept categories**: 51 (100%)

### Example Mappings

| Node Name | Collection Label | Concept Category | Available Concepts |
|-----------|------------------|------------------|-------------------|
| Density of materials | Density of material | Density of material | 17 |
| Material/object type | Material/object type | Material/object type | 2790 |
| Site descriptive type | Site descriptive type | Site descriptive type | 734 |
| Certainty | Certainty | Certainty | 14 |

### Key Findings

1. **Perfect Success Rate**: All 51 concept nodes were successfully mapped through the complete chain
2. **Rich Concept Data**: The largest concept category (Material/object type) contains 2,790 individual concepts
3. **Diverse Categories**: 46 different concept categories were identified
4. **Consistent Structure**: All concept nodes follow the same pattern with rdmCollection UUIDs

## Usage

### Running the Solution

```bash
# Test the complete solution
uv run python test_issue4.py

# Use with main application
uv run python src/main.py -i data/input.csv --summary
```

### Output Files

1. **Console Output**: Detailed mapping information and statistics
2. **CSV Report**: `output/issue4_concept_mapping_report.csv` - Complete mapping data
3. **Concept Mappings**: `output/{input}_concept_mappings.csv` - Integration with main application

### API Usage

```python
from src.cleaners.check_vocab import (
    get_concept_node_summary,
    build_concept_mappings,
    parse_collections_xml
)

# Get complete summary
summary = get_concept_node_summary(resource_model, concepts)

# Build detailed mappings
mappings = build_concept_mappings(resource_model, concepts)

# Parse collections directly
collections = parse_collections_xml()
```

## Technical Details

### Data Flow
```
Site.json (concept nodes)
    ↓ (extract rdmCollection UUIDs)
collections.xml (RDF triples)
    ↓ (extract English labels)
Site_concepts.json (concept categories)
    ↓ (match and link)
Complete Mapping
```

### XML Parsing Strategy
- Uses `xml.etree.ElementTree` with proper namespace handling
- Extracts UUIDs from `rdf:about` attributes
- Parses JSON-like structures in `skos:prefLabel` elements
- Handles complex nested RDF structures

### Matching Algorithm
1. **Exact Match**: Direct string comparison
2. **Partial Match**: Case-insensitive substring matching
3. **Fallback**: Returns None if no match found

## Files Modified/Created

### Modified Files
- `src/cleaners/check_vocab.py` - Enhanced with complete mapping functionality
- `src/main.py` - Updated to support concept mapping output

### New Files
- `test_issue4.py` - Comprehensive test script
- `ISSUE4_SOLUTION.md` - This documentation
- `output/issue4_concept_mapping_report.csv` - Generated report

## Dependencies

- `pandas` - Data manipulation and CSV output
- `glom` - Nested data access in JSON structures
- `xml.etree.ElementTree` - XML parsing (built-in)
- `pathlib` - File path handling (built-in)

## Future Enhancements

1. **Caching**: Implement caching for large XML files to improve performance
2. **Validation**: Add data validation and integrity checks
3. **API Extension**: Create REST API endpoints for the mapping functionality
4. **Visualization**: Add data visualization for concept relationships
5. **Batch Processing**: Support for processing multiple resource models

## Conclusion

The solution successfully addresses Issue 4 by providing a complete, robust, and efficient system for building links between concept nodes and their corresponding English labels. The implementation achieves 100% success rate in mapping all 51 concept nodes through the complete data chain, demonstrating the effectiveness of the approach.

The solution is production-ready, well-documented, and provides both programmatic access and user-friendly reporting capabilities. 