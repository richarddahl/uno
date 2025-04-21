#!/usr/bin/env python
"""
Bounded Context Visualization Tool.

This script generates visual representations of the domain's bounded contexts
and their relationships using the DOT graph functionality.
"""
import argparse
import os
import sys
from pathlib import Path
import tempfile
import webbrowser

# Ensure the src directory is in the Python path
sys.path.append(str(Path(__file__).parent.parent))

from uno.core.domain.context_definitions import get_dot_graph, analyze_dependencies


def save_graph(output_path: str, view: bool = False, format: str = "png") -> None:
    """Generate and save the context map visualization."""
    try:
        import graphviz
    except ImportError:
        print("Error: graphviz Python package not installed.")
        print("Install it with: pip install graphviz")
        print("Note: You also need the Graphviz binary installed on your system.")
        sys.exit(1)
    
    # Get the DOT graph
    dot_graph = get_dot_graph()
    
    # Create a graphviz Source object
    graph = graphviz.Source(dot_graph)
    
    # Save the graph
    try:
        output_file = graph.render(output_path, format=format, cleanup=True)
        print(f"Context map visualization saved to {output_file}")
        
        if view:
            webbrowser.open(f"file://{os.path.abspath(output_file)}")
    except Exception as e:
        print(f"Error rendering graph: {e}")
        print("Saving DOT graph source instead.")
        with open(f"{output_path}.dot", "w") as f:
            f.write(dot_graph)
        print(f"DOT graph source saved to {output_path}.dot")


def analyze_context_map() -> None:
    """Analyze and display context map dependencies."""
    analysis = analyze_dependencies()
    
    print("=== Bounded Context Dependency Analysis ===\n")
    
    print("Core Domains:")
    for context in analysis['core_domains']:
        print(f"  - {context}")
    
    print("\nMost Depended Upon Contexts:")
    for context, count in analysis['most_depended_upon']:
        print(f"  - {context}: {count} incoming dependencies")
    
    print("\nContexts with Most Dependencies:")
    for context, count in analysis['most_dependencies']:
        print(f"  - {context}: {count} outgoing dependencies")
    
    print("\nPotential Coupling Issues:")
    if analysis.get('potential_coupling_issues'):
        for issue in analysis['potential_coupling_issues']:
            print(f"  - {issue}")
    else:
        print("  No issues detected")


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description="Bounded Context Visualization Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a PNG visualization
  python src/scripts/visualize_contexts.py
  
  # Generate SVG and open in browser
  python src/scripts/visualize_contexts.py --format svg --view
  
  # Analyze context dependencies
  python src/scripts/visualize_contexts.py --analyze
  
  # Generate visualization and perform analysis
  python src/scripts/visualize_contexts.py --view --analyze
"""
    )
    
    parser.add_argument('--output', '-o', default='context_map', 
                      help='Output file path (without extension)')
    parser.add_argument('--format', '-f', default='png', choices=['png', 'svg', 'pdf'],
                      help='Output file format')
    parser.add_argument('--view', '-v', action='store_true',
                      help='Open visualization in browser after generation')
    parser.add_argument('--analyze', '-a', action='store_true',
                      help='Analyze context dependencies')
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_context_map()
    
    # Generate visualization if no explicit analyze flag or both are requested
    if not args.analyze or (args.analyze and args.view):
        save_graph(args.output, view=args.view, format=args.format)


if __name__ == "__main__":
    main()