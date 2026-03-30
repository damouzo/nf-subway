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

        # task_id -> node_key: lets status updates find the right graph node
        self._task_id_to_node_key: dict = {}

        # Dependency inference state
        self.last_process = None
        self.last_top_level: Optional[str] = None   # node_key of last main-branch node
        self._last_in_workflow: dict = {}            # norm_prefix -> node_key
        self._open_workflow_tails: dict = {}        # norm_prefix -> node_key
    
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
            if 'Pipeline completed' in line or 'Execution status: OK' in line:
                self._mark_workflow_complete()
                return True
            return False

        if parsed.get('event') == 'workflow_complete':
            self._mark_workflow_complete()
            return True

        process_name = parsed.get('process')
        status = parsed.get('status')
        task_id = parsed.get('task_id')
        task_num = parsed.get('task_num')
        duration = parsed.get('duration')
        annotation = parsed.get('annotation')

        if not process_name or not status:
            return False

        # Resolve stable node key for this task instance
        if task_id and task_id in self._task_id_to_node_key:
            node_key = self._task_id_to_node_key[task_id]
        else:
            node_key = f"{process_name} ({task_num})" if task_num else process_name
            if task_id:
                self._task_id_to_node_key[task_id] = node_key

        workflow_prefix = process_name.split(":", 1)[0] if ":" in process_name else None
        if workflow_prefix:
            workflow_prefix = self._normalize_workflow_key(workflow_prefix)

        is_new = node_key not in self.graph.nodes

        self.graph.update_process(
            node_key,
            status,
            duration=duration,
            annotation=annotation,
            workflow_prefix=workflow_prefix,
            base_name=process_name,
        )

        if is_new:
            self._infer_dependency(node_key, process_name)

        self.last_process = node_key
        return False

    def _mark_workflow_complete(self):
        """Finalize node statuses when workflow completion is detected."""
        for process in self.graph.get_ordered_processes():
            if process.status in {ProcessStatus.RUNNING, ProcessStatus.PENDING}:
                self.graph.update_process(process.name, ProcessStatus.COMPLETED)

    def _infer_dependency(self, node_key: str, process_name: str):
        """Infer likely parent dependency for a newly added node."""
        if ":" in process_name:
            workflow_name = process_name.split(":", 1)[0]
            workflow_key = self._normalize_workflow_key(workflow_name)

            prev = self._last_in_workflow.get(workflow_name) or self._last_in_workflow.get(workflow_key)

            if prev and prev != node_key:
                self.graph.add_dependency(prev, node_key)
            elif self.last_top_level and self.last_top_level != node_key:
                self.graph.add_dependency(self.last_top_level, node_key)

            self._last_in_workflow[workflow_name] = node_key
            self._last_in_workflow[workflow_key] = node_key
            self._open_workflow_tails[workflow_key] = node_key
            return

        # Top-level process: merge from all open workflow tails
        if self._open_workflow_tails:
            for tail in sorted(set(self._open_workflow_tails.values())):
                if tail != node_key:
                    self.graph.add_dependency(tail, node_key)
            self._open_workflow_tails.clear()
        elif self.last_top_level and self.last_top_level != node_key:
            self.graph.add_dependency(self.last_top_level, node_key)

        self.last_top_level = node_key

    @staticmethod
    def _normalize_workflow_key(workflow_name: str) -> str:
        """
        Canonical key for a workflow name, robust to Nextflow's variable middle-truncation.

        Nextflow truncates long subworkflow prefixes to fit its display column, preserving
        a few chars from the start and end. The amount preserved from the end varies per
        process, so we key only on the stable prefix before the ellipsis.

        Examples:
            ALI…QUANTIFICATION:ALIGN_READS  → key "ali"
            ALI…NTIFICATION:COUNT_FEATURES  → key "ali"  (same workflow)
            ALIGNMENT_BASED_QUANTIFICATION  → key "alignment_based_quantification"
        """
        name = workflow_name.strip().lower()
        if "…" in name:
            return name.split("…")[0]
        return name


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
