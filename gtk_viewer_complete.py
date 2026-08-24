#!/usr/bin/env python3
"""Minimal GTK4 Window for Loading and Displaying Graphs from JSON Files.

Features:
- Load graphs from JSON files  
- Display graphs in embedded matplotlib canvas
- Recording mode to track graph modifications
- Playback mode to replay recorded actions
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, Gio, GLib
import os
import sys
import time


script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

try:
    from graphs.core import DirectedGraph
    from graphs.visualization import plot_graph
except ImportError as e:
    print(f"Error importing graph modules: {e}")
    sys.exit(1)


class RecordingSession:
    """Records actions for playback."""
    
    def __init__(self):
        self.actions = []
        self.start_time = None
    
    def start_recording(self, initial_graph=None, filename=None):
        if not (initial_graph and filename):
            return
        
        nodes_list = list(initial_graph.nodes())[:30]  
        edges_list = initial_graph.edges()[:25] 
        
        snapshot_data = {"name": getattr(initial_graph, "name", ""), "nodes": {}, "edges": []}
        
        for node_id in nodes_list:
            no_obj = initial_graph.get_node(node_id) 
            if not no_obj: continue
            
            props_raw = getattr(no_obj, "properties", {}) or {}
            
class PlaybackSession: