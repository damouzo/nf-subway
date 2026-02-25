"""
Real-time monitoring of Nextflow pipeline execution.

Integrates the parser, graph, and renderer to provide live visualization.
"""

import sys
import time
import threading
from typing import Optional, TextIO
from queue import Queue, Empty

from .graph import SubwayGraph
from .parser import NextflowOutputParser
from .renderer import SubwayLiveRenderer
from .colors import ProcessStatus


class NextflowMonitor:
    """
    Monitors Nextflow output in real-time and updates the subway graph.
    
    Can be used as a subprocess wrapper that intercepts stdout, or as
    a standalone monitor that reads from a file/stream.
    """
    
    def __init__(self, 
                 input_stream: Optional[TextIO] = None,
                 show_original: bool = True,
                 refresh_rate: int = 4,
                 orientation: str = 'auto'):
        """
        Initialize the monitor.
        
        Args:
            input_stream: Stream to read Nextflow output from (default: stdin)
            show_original: Whether to show original Nextflow output
            refresh_rate: Refresh rate for the live display (updates per second)
            orientation: Visualization layout ('vertical', 'horizontal', or 'auto')
        """
        self.input_stream = input_stream or sys.stdin
        self.show_original = show_original
        self.refresh_rate = refresh_rate
        self.orientation = orientation
        
        self.graph = SubwayGraph()
        self.parser = NextflowOutputParser()
        self.renderer = None
        self.is_running = False
        
        # Thread-safe queue for output lines
        self.output_queue = Queue()
        
        # Track previous process for simple dependency inference
        self.last_process = None
        self.last_top_level_process = None
        self.workflow_last_processes = {}
        self.open_workflow_tails = {}
    
    def start(self):
        """Start monitoring the input stream."""
        self.is_running = True
        
        # Start the live renderer with orientation
        self.renderer = SubwayLiveRenderer(self.graph, self.refresh_rate, orientation=self.orientation)
        self.renderer.start()
        
        # Start reading thread
        reader_thread = threading.Thread(target=self._read_input, daemon=True)
        reader_thread.start()
        
        # Main update loop
        try:
            self._update_loop()
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop monitoring."""
        self.is_running = False
        if self.renderer:
            self.renderer.stop()
    
    def _read_input(self):
        """Read input stream in a separate thread."""
        try:
            for line in self.input_stream:
                if not self.is_running:
                    break
                
                # Add to queue for processing
                self.output_queue.put(line)
                
                # Show original output if requested
                if self.show_original:
                    sys.stdout.write(line)
                    sys.stdout.flush()
        except Exception as e:
            # Stream closed or error
            self.output_queue.put(None)  # Signal end
    
    def _update_loop(self):
        """Main update loop that processes output and updates display."""
        update_interval = 1.0 / self.refresh_rate
        last_update = time.time()
        pipeline_complete = False
        
        while self.is_running:
            # Process all available lines
            lines_processed = 0
            try:
                while lines_processed < 100:  # Batch process
                    line = self.output_queue.get(timeout=0.01)
                    
                    if line is None:  # End signal
                        self.is_running = False
                        break
                    
                    # Check if pipeline completed
                    if self._process_line(line):
                        pipeline_complete = True
                    
                    lines_processed += 1
            except Empty:
                pass
            
            # Update display at fixed rate
            current_time = time.time()
            if current_time - last_update >= update_interval:
                if self.renderer:
                    self.renderer.update()
                last_update = current_time
            
            # If pipeline completed and no more input, exit gracefully
            if pipeline_complete and self.output_queue.empty():
                time.sleep(1)  # Final update display
                self.is_running = False
                break
            
            # Small sleep to prevent CPU spinning
            time.sleep(0.01)
    
    def _process_line(self, line: str):
        """Process a single line of output. Returns True if pipeline completed."""
        parsed = self.parser.parse_and_update(line)
        
        if not parsed:
            # Check for pipeline completion in raw line
            if 'Pipeline completed' in line or 'Execution status: OK' in line:
                self._mark_workflow_complete()
                return True  # Signal completion
            return False
        
        # Handle workflow completion event
        if parsed.get('event') == 'workflow_complete':
            self._mark_workflow_complete()
            return True  # Signal completion
        
        # Extract process information
        process_name = parsed.get('process')
        status = parsed.get('status')
        task_id = parsed.get('task_id')
        duration = parsed.get('duration')
        annotation = parsed.get('annotation')
        
        if process_name and status:
            is_new_process = process_name not in self.graph.nodes

            # Update or add the process
            self.graph.update_process(
                process_name,
                status,
                duration=duration,
                annotation=annotation
            )
            
            if is_new_process:
                self._infer_dependency(process_name)
            
            # Update last seen process
            self.last_process = process_name
        
        return False

    def _mark_workflow_complete(self):
        """Finalize node statuses when workflow completion is detected."""
        for process in self.graph.get_ordered_processes():
            if process.status in {ProcessStatus.RUNNING, ProcessStatus.PENDING}:
                self.graph.update_process(process.name, ProcessStatus.COMPLETED)

    def _infer_dependency(self, process_name: str):
        """Infer likely dependencies to produce a readable git-graph style layout."""
        if ":" in process_name:
            workflow_name = process_name.split(":", 1)[0]
            workflow_key = self._normalize_workflow_key(workflow_name)
            previous_in_workflow = self.workflow_last_processes.get(workflow_name)

            if previous_in_workflow is None:
                previous_in_workflow = self.workflow_last_processes.get(workflow_key)

            if previous_in_workflow and previous_in_workflow != process_name:
                self.graph.add_dependency(previous_in_workflow, process_name)
            elif self.last_top_level_process and self.last_top_level_process != process_name:
                self.graph.add_dependency(self.last_top_level_process, process_name)

            self.workflow_last_processes[workflow_name] = process_name
            self.workflow_last_processes[workflow_key] = process_name
            self.open_workflow_tails[workflow_key] = process_name
            return

        # Top-level process (without subworkflow prefix)
        if self.open_workflow_tails:
            for tail_name in sorted(set(self.open_workflow_tails.values())):
                if tail_name != process_name:
                    self.graph.add_dependency(tail_name, process_name)
            self.open_workflow_tails.clear()
        elif self.last_top_level_process and self.last_top_level_process != process_name:
            self.graph.add_dependency(self.last_top_level_process, process_name)

        self.last_top_level_process = process_name

    @staticmethod
    def _normalize_workflow_key(workflow_name: str) -> str:
        """
        Normalize subworkflow prefixes when Nextflow truncates them with ellipsis.

        Example:
            ALI…ASED_QUANTIFICATION
            ALI…D_QUANTIFICATION
            ALI…QUANTIFICATION
        become a stable key based on leading token + suffix.
        """
        normalized = workflow_name.strip().lower()
        if "…" not in normalized:
            return normalized

        left, right = normalized.split("…", 1)
        left_token = left[:3]
        right_token = right[-20:]
        return f"{left_token}:{right_token}"


class FileMonitor(NextflowMonitor):
    """
    Monitor that reads from a file (useful for monitoring .nextflow.log).
    
    Follows the file as it grows (like `tail -f`).
    """
    
    def __init__(self, log_file: str, orientation: str = 'auto', **kwargs):
        # Open file for reading
        self.log_file = log_file
        super().__init__(input_stream=None, orientation=orientation, **kwargs)
    
    def _read_input(self):
        """Read from log file, following as it grows."""
        try:
            warned_missing = False
            while self.is_running:
                try:
                    with open(self.log_file, 'r') as f:
                        # Seek to end if file exists
                        f.seek(0, 2)
                        warned_missing = False

                        while self.is_running:
                            line = f.readline()
                            if line:
                                self.output_queue.put(line)

                                if self.show_original:
                                    sys.stdout.write(line)
                                    sys.stdout.flush()
                            else:
                                # No new data, wait a bit
                                time.sleep(0.1)
                    break
                except FileNotFoundError:
                    if not warned_missing:
                        print(f"Log file not found yet: {self.log_file}. Waiting for creation...", file=sys.stderr)
                        warned_missing = True
                    time.sleep(0.5)
        except Exception as e:
            print(f"Error reading log file: {e}", file=sys.stderr)
            self.output_queue.put(None)


def monitor_nextflow_stdout(orientation='auto', refresh_rate=4, show_original=True):
    """
    Convenience function to monitor Nextflow output from stdin.
    
    Usage:
        nextflow run pipeline.nf | nf-subway
    """
    monitor = NextflowMonitor(
        input_stream=sys.stdin,
        show_original=show_original,
        refresh_rate=refresh_rate,
        orientation=orientation
    )
    
    try:
        monitor.start()
    except KeyboardInterrupt:
        monitor.stop()
        sys.exit(0)


def monitor_nextflow_logfile(log_file: str, orientation='auto', refresh_rate=4, show_original=False):
    """
    Convenience function to monitor Nextflow log file.
    
    Usage:
        nf-subway --log .nextflow.log
    """
    monitor = FileMonitor(
        log_file=log_file,
        show_original=show_original,
        refresh_rate=refresh_rate,
        orientation=orientation
    )
    
    try:
        monitor.start()
    except KeyboardInterrupt:
        monitor.stop()
        sys.exit(0)
