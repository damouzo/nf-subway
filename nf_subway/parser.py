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
    
    # Regex patterns for Nextflow output
    # Pattern for standard process execution lines like:
    # [18/f4103b] QUALITY_CHECK (1) [100%] 3 of 3 ✔
    # [6b/27f290] ALIGNMENT_BASED_QUANTIFICATION:ALIGN_READS (3) [100%] 3 of 3 ✔
    PROCESS_PATTERN = re.compile(
        r'\[([a-f0-9]{2}/[a-f0-9]{6})\]\s+([\w:]+)\s*'
        r'(?:\((\d+)\))?\s*\[?\s*(\d+)%?\s*\]?\s*(\d+\s+of\s+\d+)?'
    )
    
    # Pattern for completion with duration
    COMPLETION_PATTERN = re.compile(
        r'\[([a-f0-9]{2}/[a-f0-9]{6})\].*?(\S+)\s*\((\d+)\)\s*\[.*?(\d+\.\d+)s\]'
    )
    
    # Pattern for cached processes
    CACHED_PATTERN = re.compile(
        r'\[([a-f0-9]{2}/[a-f0-9]{6})\]\s+(?:CACHED|cached):\s*(\S+)'
    )
    
    # Pattern for failures
    FAILURE_PATTERN = re.compile(
        r'(?:ERROR|FAILED|Error executing process).*?[>\s]+[\'"]?(\S+)[\'"]?'
    )
    
    # Pattern for workflow completion
    WORKFLOW_COMPLETE = re.compile(
        r'(?:Completed at|Workflow completed|Pipeline completed|Execution status: OK)'
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
        # Remove ANSI escape codes (colors, formatting) that Nextflow outputs
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        line = ansi_escape.sub('', line).strip()
        
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
        
        # Check for process execution line
        process_match = self.PROCESS_PATTERN.search(line)
        if process_match:
            task_id, process_name, task_num, progress, count = process_match.groups()
            # Build annotation identical to log output
            annotation = f"[{task_id}] process > {process_name}"
            if task_num:
                annotation += f" ({task_num})"
            if progress:
                annotation += f" [{progress}]"
            if count:
                annotation += f" {count}"

            # Determine status from progress
            status = ProcessStatus.RUNNING
            if progress == '100%' or (count and count.split()[0] == count.split()[-1]):
                # Check if line has completion marker
                if '\u2714' in line or 'COMPLETED' in line.upper():
                    status = ProcessStatus.COMPLETED
            elif progress == '0%' or progress == '0':
                status = ProcessStatus.PENDING
            
            return {
                'process': process_name,
                'status': status,
                'task_id': task_id,
                'progress': progress or count or '0%',
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
