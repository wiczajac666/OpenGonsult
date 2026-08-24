"""Graph Core Module - Node, Edge, and DirectedGraph data structures."""

import json


class Node:
    """A graph node representing an entity."""

    def __init__(self, id_, properties=None):
        if isinstance(id_, Node):
            self.id = id_.id
            self.properties = dict(id_.properties) if id_.properties else {}
        elif isinstance(id_, str) and not id_.strip():
            self.id = 0
            self.properties = properties or {}
        elif isinstance(id_, str):
            self.id = id_  # keep as string (algorithms use string IDs)
            self.properties = properties or {}
        else:
            self.id = int(id_)
            self.properties = properties or {}

    def __repr__(self):
        name = self.properties.get("name", str(self.id))
        return f"Node({name})"

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class Edge:
    """An edge connecting two nodes in a graph."""

    def __init__(self, source, target, properties=None):
        if isinstance(source, Node):
            source = source.id
        elif not isinstance(source, str):
            source = str(int(source))
        self.source = source
        if isinstance(target, Node):
            target = target.id
        elif not isinstance(target, str):
            target = str(int(target))
        self.target = target
        self.properties = properties or {}
        self.weight = self.properties.get("weight", 1.0)
        self.label = self.properties.get("label", "")
        self.color = self.properties.get("color", "#4287f5")
        self.confidence = float(self.properties.get("confidence", 1.0))

    def __repr__(self):
        return f"Edge({self.source} -> {self.target}, weight={self.weight})"

    def __eq__(self, other):
        if not isinstance(other, Edge):
            return False
        return self.source == other.source and self.target == other.target

    def __hash__(self):
        return hash((self.source, self.target))


class DirectedGraph:
    """A directed graph with nodes and edges."""

    def __init__(self, name=""):
        self.name = name
        self._nodes = {}          # id -> Node
        self._edges = []          # list of Edge objects
        self._adjacency = {}      # source_id -> [target_id, ...]
        self._reverse_adj = {}    # target_id -> [source_id, ...]

    # ---- node management ----

    def add_node(self, node):
        """Add a node to the graph. If it already exists, updates its properties."""
        if isinstance(node, int):
            node = Node(node)
        self._nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []
        return node

    def remove_node(self, node_id):
        """Remove a node and all its incident edges."""
        node_id = int(node_id)
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        self._adjacency.pop(node_id, None)
        # remove reverse-adj entries pointing to this node
        for nid in list(self._reverse_adj):
            if node_id in self._reverse_adj[nid]:
                self._reverse_adj[nid].remove(node_id)
        # remove incident edges
        self._edges = [e for e in self._edges if e.source != node_id and e.target != node_id]
        return True

    def has_node(self, node_id):
        n = node_id.id if isinstance(node_id, Node) else node_id
        return n in self._nodes

    def get_node(self, node_id):
        n = node_id.id if isinstance(node_id, Node) else node_id
        return self._nodes.get(n)

    # ---- edge management ----

    def add_edge(self, source, target, properties=None):
        """Add a directed edge from source to target."""
        src_id = source.id if isinstance(source, Node) else int(source)
        tgt_id = target.id if isinstance(target, Node) else int(target)
        if not self.has_node(src_id):
            self.add_node(source)
        if not self.has_node(tgt_id):
            self.add_node(target)

        edge = Edge(src_id, tgt_id, properties)
        self._edges.append(edge)
        if tgt_id not in self._adjacency.get(src_id, []):
            self._adjacency.setdefault(src_id, []).append(tgt_id)
        self._reverse_adj.setdefault(tgt_id, []).append(src_id)
        return edge

    def remove_edge(self, source, target):
        """Remove a directed edge from source to target."""
        src_id = source.id if isinstance(source, Node) else int(source)
        tgt_id = target.id if isinstance(target, Node) else int(target)
        self._edges = [e for e in self._edges if not (e.source == src_id and e.target == tgt_id)]
        if tgt_id in self._adjacency.get(src_id, []):
            self._adjacency[src_id].remove(tgt_id)
        if src_id in self._reverse_adj.get(tgt_id, []):
            self._reverse_adj[tgt_id].remove(src_id)

    def has_edge(self, source, target):
        src_id = source.id if isinstance(source, Node) else int(source)
        tgt_id = target.id if isinstance(target, Node) else int(target)
        return tgt_id in (self._adjacency.get(src_id, []))

    def get_edges(self):
        """Return a list of all Edge objects."""
        return list(self._edges)

    # ---- queries ----

    def get_neighbors(self, node_id, direction="out"):
        """Return neighbor node IDs.
        direction: 'out' (default), 'in', or 'both'."""
        node_id = int(node_id)
        if direction == "out":
            return list(self._adjacency.get(node_id, []))
        elif direction == "in":
            return list(self._reverse_adj.get(node_id, []))
        else:
            out = set(self._adjacency.get(node_id, []))
            inp = set(self._reverse_adj.get(node_id, []))
            return list(out | inp)

    def get_node_count(self):
        return len(self._nodes)

    def get_edge_count(self):
        return len(self._edges)

    def nodes(self):
        """Return a dict of {id: Node} for serialization."""
        return dict(self._nodes)

    def edges(self):
        """Return the list of Edge objects."""
        return self._edges

    # ---- iteration helpers ----

    def __contains__(self, node_id):
        return int(node_id) in self._nodes

    def __iter__(self):
        return iter(self._nodes.values())

    # ---- serialization ----

    def to_dict(self):
        return {
            "name": self.name,
            "nodes": {nid: {"id": n.id, "properties": n.properties} for nid, n in self._nodes.items()},
            "edges": [
                {"source": e.source, "target": e.target, "properties": e.properties}
                for e in self._edges
            ],
        }

    @classmethod
    def from_dict(cls, data):
        graph = cls(name=data.get("name", ""))
        for nid, ndata in data.get("nodes", {}).items():
            graph.add_node(Node(ndata["id"], ndata.get("properties")))
        for edata in data.get("edges", []):
            graph.add_edge(edata["source"], edata["target"], edata.get("properties"))
        return graph

    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text):
        return cls.from_dict(json.loads(text))

    def __repr__(self):
        return f"DirectedGraph({self.name!r}, nodes={self.get_node_count()}, edges={self.get_edge_count()})"
