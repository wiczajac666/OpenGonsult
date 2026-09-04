"""Graph Algorithms Module.

Functions:
- shortest_path(): Find paths through graph
- centrality(): Calculate node importance
- clustering_coefficient(): Measure clustering in graph
- community_detection(): Find communities/groups in graph
- betweenness_centrality(): Measure node importance by path flow
- degree_centrality(): Simple degree-based importance
- page_rank(): Google's famous algorithm (adapted for graphs!)
"""


def _import_networkx():
    """Lazy import of networkx with a helpful error message."""
    try:
        import networkx as nx
        return nx
    except ImportError:
        raise ImportError(
            "networkx is required for graph algorithms. "
            "Install it with: pip install networkx"
        )


def shortest_path(graph, source, target):
    """Find shortest path between two nodes.

    Args:
        graph: Graph object (NetworkX or custom)
        source: Starting node
        target: Ending node

    Returns:
        List of nodes in shortest path
    """
    if hasattr(graph, 'graph'):  # NetworkX graph
        nx = _import_networkx()
        return nx.shortest_path(graph.graph, source, target)
    else:  # Custom graph object
        from collections import deque

        queue = deque([(source, [source])])
        visited = {source}

        while queue:
            current, path = queue.popleft()

            if current == target:
                return path

            for neighbor in graph.get_neighbors(current, direction="out"):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None  # No path found


def centrality(graph, method='betweenness'):
    """Calculate node centrality measures.

    Args:
        graph: Graph object (NetworkX or custom)
        method: Type of centrality ('degree', 'betweenness', 'closeness')

    Returns:
        Dictionary of {node: centrality_score}
    """
    if hasattr(graph, 'graph'):  # NetworkX graph
        nx = _import_networkx()
        nx_graph = graph.graph

        if method == 'degree':
            return nx.degree_centrality(nx_graph)
        elif method == 'betweenness':
            return nx.betweenness_centrality(nx_graph)
        elif method == 'closeness':
            return nx.closeness_centrality(nx_graph)
        else:
            raise ValueError(f"Unknown centrality method: {method}")
    else:
        # For custom graphs, calculate degree centrality
        if method == 'degree':
            degrees = {}
            for node in graph.nodes():
                degrees[node] = graph.degree(node)
            max_degree = max(degrees.values()) if degrees else 1
            return {node: deg / (max_degree or 1) for node, deg in degrees.items()}
        elif method == 'betweenness':
            # Simplified betweenness calculation
            return _simplified_betweenness(graph)
        else:
            raise ValueError(f"Unknown centrality method: {method}")


def clustering_coefficient(graph):
    """Calculate clustering coefficient of graph.

    Args:
        graph: Graph object (NetworkX or custom)

    Returns:
        Float: Average clustering coefficient (0-1)
    """
    if hasattr(graph, 'graph'):  # NetworkX graph
        nx = _import_networkx()
        return nx.average_clustering(graph.graph)
    else:
        # Calculate for custom graphs
        total = 0
        count = 0

        for node in graph.nodes():
            neighbors = list(graph.get_neighbors(node, direction="both"))
            if len(neighbors) < 2:
                continue

            # Count triangles
            triangles = 0
            for i, n1 in enumerate(neighbors):
                for n2 in neighbors[i+1:]:
                    if graph.has_edge(n1, n2):
                        triangles += 1

            possible = len(neighbors) * (len(neighbors) - 1) / 2
            total += triangles / possible if possible > 0 else 0
            count += 1

        return total / count if count > 0 else 0


def community_detection(graph, method='louvain'):
    """Detect communities in graph.

    Args:
        graph: Graph object (NetworkX or custom)
        method: Algorithm to use ('louvain', 'girvan_newman')

    Returns:
        Dictionary of {node: community_id}
    """
    if hasattr(graph, 'graph'):  # NetworkX graph
        nx_graph = graph.graph

        if method == 'louvain':
            try:
                from networkx.algorithms.community import louvain_communities
                communities = louvain_communities(nx_graph)
                node_to_community = {}
                for i, community in enumerate(communities):
                    for node in community:
                        node_to_community[node] = i
                return node_to_community
            except ImportError:
                # Fallback to greedy modularity
                from networkx.algorithms.community import greedy_modularity_communities
                communities = list(greedy_modularity_communities(nx_graph))
        elif method == 'girvan_newman':
            from networkx.algorithms.community import girvan_newman
            communities = [frozenset(c) for c in girvan_newman(nx_graph, num_spans=2)]
        else:
            communities = [frozenset(nx_graph.nodes())]

        # Convert to node->community mapping
        node_to_community = {}
        for i, community in enumerate(communities):
            if isinstance(community, (set, frozenset)):
                for node in community:
                    node_to_community[node] = i
            else:
                for node in community:
                    node_to_community[node] = i

        return node_to_community
    else:
        # Simplified community detection for custom graphs
        return _simple_communities(graph)


def betweenness_centrality(graph):
    """Calculate betweenness centrality (alias for centrality with method='betweenness')"""
    return centrality(graph, 'betweenness')


def degree_centrality(graph):
    """Calculate degree centrality (alias for centrality with method='degree')"""
    return centrality(graph, 'degree')


def page_rank(graph, alpha=0.85, max_iter=100, tol=1e-6):
    """Calculate PageRank scores.

    Args:
        graph: Graph object (NetworkX or custom)
        alpha: Damping factor (default 0.85)
        max_iter: Maximum iterations
        tol: Convergence tolerance

    Returns:
        Dictionary of {node: page_rank_score}
    """
    if hasattr(graph, 'graph'):  # NetworkX graph
        nx = _import_networkx()
        return nx.pagerank(graph.graph, alpha=alpha, max_iter=max_iter, tol=tol)
    else:
        # Simplified PageRank for custom graphs
        nodes = list(graph.nodes())
        n = len(nodes)

        if n == 0:
            return {}

        # Initialize ranks
        rank = {node: 1.0 / n for node in nodes}

        for _ in range(max_iter):
            new_rank = {}

            for node in nodes:
                incoming_sum = 0

                # Sum contributions from all nodes that link to this node
                for other_node in nodes:
                    if graph.has_edge(other_node, node):
                        out_degree = len(graph.get_neighbors(other_node)) or 1
                        incoming_sum += rank[other_node] / out_degree

                new_rank[node] = (1 - alpha) / n + alpha * incoming_sum

            # Check convergence
            diff = sum(abs(new_rank[n] - rank[n]) for n in nodes)
            rank = new_rank

            if diff < tol:
                break

        return rank


def _simplified_betweenness(graph):
    """Simplified betweenness centrality calculation for directed graphs."""
    nodes = list(graph.nodes())
    betweenness = {node: 0.0 for node in nodes}

    for source in nodes:
        # BFS from source
        stack = []
        pred = {node: [] for node in nodes}
        sigma = {node: 0 for node in nodes}
        sigma[source] = 1
        dist = {node: -1 for node in nodes}
        dist[source] = 0

        queue = [source]
        while queue:
            v = queue.pop(0)
            stack.append(v)

            # Use outgoing edges only for directed betweenness
            neighbors = graph.get_neighbors(v, direction="out")
            for w in neighbors:
                if dist[w] < 0:
                    queue.append(w)
                    dist[w] = dist[v] + 1

                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)

        # Accumulate betweenness using incoming edges
        delta = {node: 0.0 for node in nodes}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])

            if w != source:
                betweenness[w] += delta[w]

    # Normalize
    n = len(nodes)
    if n > 2:
        norm = 1.0 / ((n - 1) * (n - 2))
        for node in betweenness:
            betweenness[node] *= norm

    return betweenness


def _simple_communities(graph):
    """Simple community detection based on connected components"""
    nodes = list(graph.nodes())
    visited = set()
    communities = {}

    def bfs(start):
        queue = [start]
        component = []

        while queue:
            node = queue.pop(0)
            if node in visited:
                continue

            visited.add(node)
            component.append(node)

            for neighbor in graph.get_neighbors(node):
                if neighbor not in visited:
                    queue.append(neighbor)

        return component

    community_id = 0
    for node in nodes:
        if node not in visited:
            component = bfs(node)
            for n in component:
                communities[n] = community_id
            community_id += 1

    return communities
