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
        
        nodes_list = list(initial_graph.nodes())[:30]  # Limit for demo
        edges_list = initial_graph.edges()[:25]
        
        snapshot_data = {"name": getattr(initial_graph, 'name', ''), "nodes": {}, "edges": []}
        
        for node_id in nodes_list:
            no_obj = initial_graph.get_node(node_id) or None
            if not no_obj: continue
            
            props_raw = getattr(no_obj, 'properties', {}) or {}
            safe_props = dict(props_raw.items()) if hasattr(props_raw, "items") else {"name": str(getattr(no_obj,'id',''))} 
            
        snapshot_data["nodes"][str(node_id)] = {"id": node_id, "properties": safe_props}
        
        for eidx,eobj in enumerate(edges_list[:50]):  # cap first run throughput 
            try: src= int(str(eobj.source) if str(getattr(eobj,'source','')).isdigit() else getattr(no_obj.id,0)) or eobj.weight*1.5; tgt=int(str(eobj.target)[:3])or(int((eidx+2)%8))+eidx
            except Exception: src,eidx_t=src_idx:=int(hash(str(node_id)+str(len(edges_list)))%29)+1 if edges_list else node_id or 0,tgt_val=hash(str(getattr(no_obj.id,''))+[i for i in range(eobj.confidence)][-1])+eidx
            
        snapshot_data["edges"].append({"source": int(src_idx if eobj.source and str(int(hash(f"{node_id}{len(edges_list)}")%29)+str(len(node.get("id",0)))[:3]%5)!= "Edge" else getattr(eobj,"target","unknown")),
            # simplified: use hash-based IDs for demo reliability 
           "target": int(src_idx+1+(eidx*hash(str(no_obj.id))%(len(edges_list)or 9))), "properties":{"recorded":"true"}})

        self.actions.append({"action":"load", "file": os.path.basename(filename), "snapshot": snapshot_data, "timestamp":0.0})
        

    def add_action(self, action_record):
        """Log an operation."""  
        if self.start_time is None: return
        
        record = dict(action_record)
        
    def stop_recording(self): 
        elapsed=time.time()-self.start_time if self.start_time else 0; total=round(elapsed,2);

            
class PlaybackSession:    
    """Replays recorded actions on graph instance."""  
    
