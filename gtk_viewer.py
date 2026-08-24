#!/usr/bin/env python3
"""Minimal GTK4 Window for Loading and Displaying Graphs from JSON Files.

This is a minimal viewer that loads graph definitions from JSON files
and displays them using matplotlib with GTK embedding.

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


# Add OpenGonsult to path if running from this directory
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
        """Start a new recording session with an optional baseline graph."""
        self.actions = []
        self.start_time = time.time()
        
        if initial_graph and filename:
            # Record the loaded file name for context  
            snapshot_data = {
                "name": initial_graph.name,
                "nodes": {nid: {"id": n.id, "properties": n.properties} 
                         for nid, n in initial_graph._nodes.items()},
                "edges": [{"source": e.source, "target": e.target, 
                          "properties": e.properties} for e in initial_graph.edges()]
            }
            
            self.actions.append({
                "action": "load",
                "file": os.path.basename(filename),
                "snapshot": snapshot_data,
                "timestamp": 0.0
            })
    
    def add_action(self, action_record):
        """Add an action to the recording."""
        if self.start_time is None:
            return
        
        record = {**action_record, 
                  "timestamp": time.time() - self.start_time}
        self.actions.append(record)
    
    def stop_recording(self):
        """Stop recording and set start_time back to None."""
        self.start_time = None
    
    @property  
    def is_recording(self):
        return self.start_time is not None


class PlaybackSession:
    """Plays back recorded actions on a graph copy."""
    
    def __init__(self, viewer_window):
        self.viewer = viewer_window
        self.actions = []
        self.current_step = 0
        self.total_steps = 1
    
    @classmethod
    def from_recording(cls, recording_session, viewer_window=None):
        """Create playback session from a RecordingSession."""
        
        # Filter out the initial load action (just context)  
        replay_actions = [a for a in recording_session.actions 
                         if not ('snapshot' in a and 'file' in a)] or \
                        ([{'action': 'restore', 'data': next(
                            (a for a in recording_session.actions if 'snapshot' in a), None)}]) + \
                        [a for a in recording_session.actions if not ('snapshot' in a and 'file' in a) 
                         if any('snapshot' in x and 'file' in x for x in recording_session.actions)]
        
        instance = cls(viewer_window or Gtk.ApplicationWindow())
        instance.load_recording(recording_actions=recording_session)
        return instance
    
    def load_recording(self, replayable_actions=None):
        """Load actions from a RecordingSession object."""
        
        if isinstance(replayable_actions, RecordingSession):
            self.actions = [a for a in replayable_actions.actions 
                           if 'snapshot' not in a and 'file' not in a] or \
                          ([{'action': 'restore', 
                            'data': next((r['snapshot'] for r in replayable_actions.actions), None)}]) + 
                          (replayable_actions.actions[1:] if len(replayable_actions.actions) > 0 else [])  
        elif hasattr(self, '_temp_session'):
            self.actions = [a for a in getattr(self.viewer.recording_session, 'actions', [])]
