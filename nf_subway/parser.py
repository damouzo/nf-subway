"""
Parser for Nextflow console output.

Extracts process execution information from the live Nextflow output stream.
"""

import re
from typing import Optional, Dict
from .colors import ProcessStatus


class NextflowOutputParser:
    """
    Parses Nextflow console output to extract process information.
    
    Recognizes patterns like:
    - executor >  local (1)
    - [4c/d3a7e8] process > PROCESS_NAME (1) [  0%] 0 of 1
    - [4c/d3a7e8] process > PROCESS_NAME (1) [100%] 1 of 1 ✔
    - [4c/d3a7e8] CACHED: PROCESS_NAME (1)
    """
    
    # Regex patterns for Nextflow output (robust, all variants)
    #   - [hash] [process >] NAME [(N)] [[percent]] [x of y] [✔/FAILED/CACHED]
    #   - [hash] NAME ...etc (no "process >")
    #   Supports almost every real-world log format.
    PROCESS_PATTERN = re.compile(
        r'\[(?P<task_id>[a-f0-9]{2}/[a-f0-9]{6})\]'                # [4c/d3a7e8]
        r'\s+'
        r'(?:(?:process|PROCESS)\s*[>:])?\s*'                     # (optional "process >")
        r'(?P<process_name>\S+)'                                    # process name
        r'(?:\s*\((?P<task_num>\d+)\))?'                         # optional (N)
        r'(?:\s*\[(?P<progress>\d+%?)?\])?'                      # optional [progress]
        r'(?:\s*(?P<count>\d+\s+of\s+\d+))?'                    # optional count
        r'(?P<suffix>.*)$',                                         # anything after, to detect status
        re.IGNORECASE
    )
    # CACHED pattern unchanged, but now case-insensitive
    CACHED_PATTERN = re.compile(
        r'\[([a-f0-9]{2}/[a-f0-9]{6})\]\s+(?:CACHED|cached):\s*(\S+)',
        re.IGNORECASE
    )
    # COMPLETION remains
    COMPLETION_PATTERN = re.compile(
        r'\[([a-f0-9]{2}/[a-f0-9]{6})\].*?(\S+)\s*\((\d+)\)\s*\[.*?(\d+\.\d+)s\]'
    )
    # FAILED/ERROR detection
    FAILURE_PATTERN = re.compile(
        r'(?:ERROR|FAILED|Error executing process).*?[>\s]+[\'"]?(\S+)[\'"]?',
        re.IGNORECASE
    )
    WORKFLOW_COMPLETE = re.compile(
        r'(?:Completed at|Workflow completed|Pipeline completed)',
        re.IGNORECASE
    )
    
    def __init__(self):
        self.seen_processes: Dict[str, dict] = {}
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """
        Parse a single line of Nextflow output.
        
        Returns a dict with process information if the line contains relevant data,
        otherwise None.
        
        Dict structure:
        {
            'process': str,          # Process name
            'status': ProcessStatus, # Current status
            'task_id': str,          # Task hash (e.g., '4c/d3a7e8')
            'progress': str,         # Progress percentage or count
            'duration': float,       # Duration in seconds (if completed)
        }
        """
        line = line.strip()
        
        # Check for cached process
        cached_match = self.CACHED_PATTERN.search(line)
        if cached_match:
            task_id, process_name = cached_match.groups()
            annotation = f"[{task_id}] process > {process_name} [CACHED]"
            return {
                'process': process_name,
                'status': ProcessStatus.CACHED,
                'task_id': task_id,
                'progress': '100%',
                'duration': 0.0,
                'job_id': task_id,
                'annotation': annotation,
            }
        
        # Check for process execution line (robust to variants)
        process_match = self.PROCESS_PATTERN.search(line)
        if process_match:
            gd = process_match.groupdict()
            task_id = gd.get('task_id')
            process_name = gd.get('process_name')
            task_num = gd.get('task_num')
            progress = gd.get('progress')
            count = gd.get('count')
            suffix = gd.get('suffix') or ''
            # Compose annotation in always-the-same way (match log visually)
            annotation = f"[{task_id}] process > {process_name}"
            if task_num:
                annotation += f" ({task_num})"
            if progress:
                annotation += f" [{progress}]"
            if count:
                annotation += f" {count}"

            detected_status = ProcessStatus.RUNNING
            # If cached, completed, or failed are present in suffix, assign accordingly
            if 'cached' in suffix.lower():
                detected_status = ProcessStatus.CACHED
            elif '\u2714' in line or 'completed' in suffix.lower() or '✔' in suffix:
                detected_status = ProcessStatus.COMPLETED
            elif 'failed' in suffix.lower():
                detected_status = ProcessStatus.FAILED
            elif progress and (progress == '0%' or progress == '0'):
                detected_status = ProcessStatus.PENDING
            elif not progress and not count:
                detected_status = ProcessStatus.PENDING

            # Pick progress to display for graph (percent beats count, else fallback)
            prog_display = progress or count or '0%'
            return {
                'process': process_name,
                'status': detected_status,
                'task_id': task_id,
                'progress': prog_display,
                'duration': None,
                'job_id': task_id,
                'annotation': annotation,
            }
        
        # Check for completion with duration
        completion_match = self.COMPLETION_PATTERN.search(line)
        if completion_match:
            task_id, process_name, task_num, duration = completion_match.groups()
            annotation = f"[{task_id}] process > {process_name} ({task_num}) [100%] COMPLETED"
            return {
                'process': process_name,
                'status': ProcessStatus.COMPLETED,
                'task_id': task_id,
                'progress': '100%',
                'duration': float(duration),
                'job_id': task_id,
                'annotation': annotation,
            }
        
        # Check for failure
        failure_match = self.FAILURE_PATTERN.search(line)
        if failure_match:
            process_name = failure_match.group(1)
            annotation = f"process > {process_name} [FAILED]"
            return {
                'process': process_name,
                'status': ProcessStatus.FAILED,
                'task_id': None,
                'progress': 'FAILED',
                'duration': None,
                'job_id': None,
                'annotation': annotation,
            }
        
        # Check for workflow completion
        if self.WORKFLOW_COMPLETE.search(line):
            return {
                'event': 'workflow_complete',
            }
        
        return None
    
    def parse_and_update(self, line: str) -> Optional[Dict]:
        """
        Parse a line and update internal state.
        
        Returns the parsed process info if new or updated.
        """
        parsed = self.parse_line(line)
        
        if not parsed or 'process' not in parsed:
            return parsed
        
        process_name = parsed['process']
        task_id = parsed.get('task_id')
        
        # Create unique key for this task
        key = f"{process_name}:{task_id}" if task_id else process_name
        
        # Check if this is new or updated information
        if key not in self.seen_processes:
            self.seen_processes[key] = parsed
            return parsed
        
        # Update if status changed or duration added
        existing = self.seen_processes[key]
        if (parsed['status'] != existing['status'] or 
            (parsed.get('duration') and not existing.get('duration'))):
            self.seen_processes[key] = parsed
            return parsed
        
        return None
    
    def reset(self):
        """Reset the parser state."""
        self.seen_processes.clear()


class NextflowTraceParser:
    """
    Parser for Nextflow trace files.
    
    Provides more detailed information about task execution including:
    - Resource usage (CPU, memory)
    - Exit status
    - Exact timestamps
    """
    
    def __init__(self, trace_file: str):
        self.trace_file = trace_file
    
    def parse_trace(self) -> Dict[str, Dict]:
        """
        Parse the trace file and return task information.
        
        Returns a dict mapping task_id -> task_info.
        """
        import csv
        
        tasks = {}
        
        try:
            with open(self.trace_file, 'r') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    task_id = row.get('hash', '')
                    if task_id:
                        tasks[task_id] = {
                            'name': row.get('name', ''),
                            'status': row.get('status', ''),
                            'exit': row.get('exit', ''),
                            'duration': float(row.get('duration', 0)) / 1000.0,  # ms to s
                            'realtime': float(row.get('realtime', 0)) / 1000.0,
                            'cpu_percent': row.get('%cpu', ''),
                            'memory': row.get('peak_rss', ''),
                        }
        except FileNotFoundError:
            pass  # Trace file doesn't exist yet
        
        return tasks
