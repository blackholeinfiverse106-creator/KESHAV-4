from typing import Dict, List, Set
from app.schemas import PropagationOutput

class PropagationEngine:
    @staticmethod
    def validate_root_cause(root_cause: str, blocked_task_id: str, dependency_graph: Dict[str, List[str]]) -> bool:
        """
        Phase 1: Validate that root_cause is part of the dependency chain leading to blocked_task_id.
        Using deterministic BFS from root_cause to see if blocked_task_id is reachable.
        """
        if root_cause == blocked_task_id:
            return True
            
        visited: Set[str] = set()
        queue: List[str] = []
        
        if root_cause in dependency_graph:
            initial_deps = sorted(dependency_graph[root_cause])
            for dep in initial_deps:
                if dep not in visited:
                    visited.add(dep)
                    queue.append(dep)
        
        while queue:
            current_task = queue.pop(0)
            if current_task == blocked_task_id:
                return True
                
            if current_task in dependency_graph:
                neighbors = sorted(dependency_graph[current_task])
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
                        
        return False

    @staticmethod
    def compute_downstream_path(blocked_task_id: str, dependency_graph: Dict[str, List[str]]) -> List[str]:
        """
        Phase 2: Computes the full downstream path using a deterministic Breadth-First Search.
        Strict ordering is enforced by sorting neighbors.
        No duplicates are allowed.
        """
        impacted_tasks: List[str] = []
        visited: Set[str] = set()
        queue: List[str] = []
        
        if blocked_task_id in dependency_graph:
            initial_deps = sorted(dependency_graph[blocked_task_id])
            for dep in initial_deps:
                if dep not in visited:
                    visited.add(dep)
                    queue.append(dep)
                    impacted_tasks.append(dep)
                    
        while queue:
            current_task = queue.pop(0)
            if current_task in dependency_graph:
                # Enforce determinism by sorting neighbors
                neighbors = sorted(dependency_graph[current_task])
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
                        impacted_tasks.append(neighbor)
                        
        return impacted_tasks

    @staticmethod
    def compute_dependency_output(input_data: dict) -> dict:
        """
        Generates the decision-grade dependency intelligence output.
        Expects a dictionary containing:
        - blocked_task_id
        - root_cause
        - trace_id
        - timestamp
        - dependency_graph
        """
        blocked_task_id = str(input_data.get("blocked_task_id", ""))
        root_cause = str(input_data.get("root_cause", ""))
        trace_id = str(input_data.get("trace_id", ""))
        timestamp = str(input_data.get("timestamp", ""))
        raw_graph = input_data.get("dependency_graph", {})
        
        # Sanitize dependency_graph to handle broken structures
        dependency_graph: Dict[str, List[str]] = {}
        if isinstance(raw_graph, dict):
            for k, v in raw_graph.items():
                if isinstance(v, list):
                    dependency_graph[str(k)] = [str(x) for x in v]
                else:
                    dependency_graph[str(k)] = []
        
        # Phase 1: Root Cause Validation Engine
        # If invalid, produce deterministic failure-safe response
        is_valid = PropagationEngine.validate_root_cause(root_cause, blocked_task_id, dependency_graph)
        if not is_valid:
            output = PropagationOutput(
                blocked_task_id=blocked_task_id,
                root_cause=root_cause,
                impacted_tasks=[],
                impact_score=0,
                severity="LOW",
                resolution_signal="REJECTED:INVALID_ROOT_CAUSE",
                trace_id=trace_id,
                timestamp=timestamp
            )
            return output.model_dump()
        
        # Phase 2: Propagation Truth Verifier
        impacted_tasks = PropagationEngine.compute_downstream_path(blocked_task_id, dependency_graph)
        
        # Phase 3: Zero-State Handling
        impact_score = len(impacted_tasks)
        
        # Severity thresholds
        if impact_score < 3:
            severity = "LOW"
        elif impact_score < 10:
            severity = "MEDIUM"
        else:
            severity = "HIGH"
            
        resolution_signal = f"UNBLOCK_DEPENDENCY:{root_cause}"
            
        output = PropagationOutput(
            blocked_task_id=blocked_task_id,
            root_cause=root_cause,
            impacted_tasks=impacted_tasks,
            impact_score=impact_score,
            severity=severity,
            resolution_signal=resolution_signal,
            trace_id=trace_id,
            timestamp=timestamp
        )
        
        return output.model_dump()
# this is the testing pushing from the other machine ]0]0]0]0]0]0]0