from src.api.configurations import router as configurations_router
from src.api.devices import router as devices_router
from src.api.groupResults import router as group_results_router
from src.api.hosts import router as hosts_router
from src.api.queries import router as queries_router
from src.api.requests import router as requests_router
from src.api.results import router as results_router
from src.api.traces import router as traces_router
from src.api.worker import router as worker_router

__all__ = [
    "hosts_router",
    "devices_router",
    "configurations_router",
    "traces_router",
    "queries_router",
    "results_router",
    "requests_router",
    "group_results_router",
    "worker_router",
]
