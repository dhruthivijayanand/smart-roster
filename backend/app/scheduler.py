"""Solver selection. Both backends enforce the same mandatory allocation model."""
try:
    import ortools
except ImportError:
    from .milp_scheduler import solve
else:
    from .cp_sat_scheduler import solve as cp_solve
    def solve(*args, **kwargs):
        result=cp_solve(*args, **kwargs)
        result['solver_name']='OR-Tools CP-SAT'
        return result
