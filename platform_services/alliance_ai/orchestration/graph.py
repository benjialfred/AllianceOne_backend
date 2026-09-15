from typing import List, Dict, Set
from .state import ExecutionPlan, ExecutionStep, ExecutionStatus

class DependencyGraph:
    """
    Handles the execution order of steps based on a Directed Acyclic Graph (DAG) of dependencies.
    """
    
    def get_executable_steps(self, plan: ExecutionPlan) -> List[ExecutionStep]:
        """
        Returns a list of steps that are ready to be executed.
        A step is ready if it is PENDING and all its dependencies have SUCCEEDED.
        """
        executable = []
        
        # Build a lookup for step status
        step_status: Dict[str, ExecutionStatus] = {
            step.step_id: step.status for step in plan.steps
        }
        
        for step in plan.steps:
            if step.status != ExecutionStatus.PENDING:
                continue
                
            # Check dependencies
            can_execute = True
            for dep_id in step.dependencies:
                status = step_status.get(dep_id)
                if status != ExecutionStatus.SUCCEEDED:
                    can_execute = False
                    break
                    
            if can_execute:
                executable.append(step)
                
        return executable

    def validate_graph(self, plan: ExecutionPlan) -> bool:
        """
        Validates the graph for circular dependencies or missing references.
        Returns True if valid, False otherwise.
        """
        # Check missing dependencies
        step_ids = {step.step_id for step in plan.steps}
        for step in plan.steps:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    return False # Invalid reference

        # Check for cycles using DFS
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        
        adjacency_list: Dict[str, List[str]] = {
            step.step_id: step.dependencies for step in plan.steps
        }

        def is_cyclic(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in adjacency_list.get(node, []):
                if neighbor not in visited:
                    if is_cyclic(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
                    
            rec_stack.remove(node)
            return False

        for node in step_ids:
            if node not in visited:
                if is_cyclic(node):
                    return False

        return True
