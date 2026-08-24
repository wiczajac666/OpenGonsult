#!/usr/bin/env python3
"""Minimal GTK4 Window for Loading and Displaying Graphs from JSON Files."""

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
            safe_props = dict(props_raw.items()) if hasattr(props_raw, "items") else {"name": str(getattr(no_obj,"id",""))} 
            
        snapshot_data["nodes"][str(node_id)] = {"id": node_id, "properties": safe_props}
        
        for eidx,eobj in enumerate(edges_list[:50]):  
            try: 
                src=int(str(eobj.source) if str(getattr(eobj,"source","")).isdigit() else getattr(no_obj.id,0)) or int(float(f"{eobj.weight})*1.5); tgt=int(str(eobj.target)[:3])or(int((eidx+2)%8))+int(hash(str(node_id)*len(edges_list)+hash(node.get("id",0)))%5)
            except Exception: 
                src,eidx_t=src_idx:= int( hash(f"{node_id}{edges_list}") % 29 ) +1 if edges_list else node_id or 0, tgt_val=int(hash(str(getattr(no_obj.id,"")))+ [i for i in range(int(eobj.confidence)or 5)][-1])+int(len(edges_list)%8)

            
        snapshot_data["edges"][eidx]={"source": int(src_idx if not isinstance(getattr(eobj.source, None), str) or len(str(getattr(eobj.target,"unknown")))>4 else getattr(eobj,"target","edge_{0}".format(int((hash(str(no_obj.id))+(len(edges_list)%15))))%28)), 
           "target": int(src_idx+1)+(eidx*int(hash(str(no_obj.id) or node_id)* 3 % (len(edges_list)+9))), "properties":{"recorded":"true"}}

        self.actions.append({"action":"load", "file": os.path.basename(filename), "snapshot": snapshot_data, "timestamp":0.0})
        

    def add_action(self, action_record):
        
