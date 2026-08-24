"""Graph Visualization Module.

Provides plotting utilities for the graphing module using matplotlib.
"""

import matplotlib.pyplot as plt


def plot_graph(graph, layout='spring', node_size=300, edge_labels=True,
               title="Graph Visualization", output_file=None):
    """Create and optionally save a visualization of the graph.

    Args:
        graph: DirectedGraph object
        layout: Layout algorithm ('spring', 'circular', 'kamada_kawai')
        node_size: Default size for all nodes
        edge_labels: Whether to display edge weights/labels
        title: Plot title
        output_file: Optional file path (PNG/SVG/PDF) to save the plot

    Returns:
        fig, ax tuple from matplotlib
    """
    import networkx as nx

    # Convert our DirectedGraph to a NetworkX DiGraph
    nx_graph = _convert_to_networkx(graph)

    # Get layout
    if layout == 'spring':
        pos = nx.spring_layout(nx_graph, k=0.5, iterations=20, seed=42)
    elif layout == 'circular':
        pos = nx.circular_layout(nx_graph)
    else:  # kamada_kawai
        pos = nx.kamada_kawai_layout(nx_graph)

    # Extract node properties (works with both Node objects and dicts)
    from graphs.core import Node as CoreNode
    nodes_list = list(nx_graph.nodes())
    colors = []
    sizes = []
    for nid in nodes_list:
        nd = graph.get_node(nid)
        if nd is None:
            colors.append('#4287f5')
            sizes.append(node_size)
        elif isinstance(nd, CoreNode):
            props = nd.properties or {}
            colors.append(props.get('color', '#4287f5'))
            sizes.append(int(props.get('size', node_size)))
        elif isinstance(nd, dict):
            colors.append(nd.get('color', '#4287f5'))
            sizes.append(int(nd.get('size', node_size)))
        else:
            colors.append('#4287f5')
            sizes.append(node_size)

    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 8))

    nx.draw_networkx_nodes(nx_graph, pos, node_color=colors,
                           node_size=sizes, alpha=0.9, ax=ax)

    edge_list = list(nx_graph.edges())

    # Draw directed arrows
    nx.draw_networkx_edges(nx_graph, pos, arrowstyle='<-',
                           connectionstyle='arc3,rad=0.2', alpha=0.6, ax=ax)

    # Node labels (IDs or names from properties)
    from graphs.core import Node as CoreNode
    node_labels = {}
    for nid in nodes_list:
        nd = graph.get_node(nid)
        if nd is None:
            node_labels[nid] = str(nid)
        elif isinstance(nd, CoreNode):
            props = nd.properties or {}
            node_labels[nid] = props.get('name', str(nid))
        elif isinstance(nd, dict):
            node_labels[nid] = nd.get('name', str(nid))
        else:
            node_labels[nid] = str(nid)
    nx.draw_networkx_labels(nx_graph, pos, labels=node_labels, font_size=9)

    # Edge labels (weights)
    if edge_labels and edge_list:
        edge_weight_labels = {}
        for src, tgt in edge_list[:15]:  # limit labels to first 15
            weight = nx_graph.edges[src, tgt].get('weight', 1.0)
            edge_weight_labels[(src, tgt)] = f"{weight:.2f}"
        nx.draw_networkx_edge_labels(nx_graph, pos,
                                     edge_labels=edge_weight_labels if edge_weight_labels else None)

    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    plt.axis('off')

    ax.grid(True, linestyle='--', alpha=0.3, linewidth=0.5)

    if output_file:
        fig.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='#ffffff')

    return fig, ax


def _convert_to_networkx(graph):
    """Helper to convert a DirectedGraph to a NetworkX DiGraph."""
    import networkx as nx

    G = nx.DiGraph()

    for nid, node_data in graph.nodes().items():
        # Handle both Node objects and dict-based data structures  
        from graphs.core import Node as CoreNode
        if isinstance(node_data, CoreNode):
            name = node_data.properties.get("name", str(nid))
        else:
            name = node_data.get("properties", {}).get("name", str(nid))
        G.add_node(nid, name=name)

    for edge in graph.edges():
        src = edge.source
        tgt = edge.target
        weight = getattr(edge, "weight", 1.0)
        label = getattr(edge, "label", "")
        G.add_edge(src, tgt, weight=weight, label=label)

    return G


def export_to_file(fig, filename):
    """Save a matplotlib figure to file."""
    fig.savefig(filename, dpi=150, bbox_inches='tight', facecolor='#ffffff')
