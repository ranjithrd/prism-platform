from fastapi import FastAPI, Request, Depends
from sqlmodel import select, desc
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

from src.common.db import Trace, get_session
from src.controllers import devices_router, traces_router, queries_router
from src.services.startup import handle_on_startup

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def on_startup():
    handle_on_startup()


app.include_router(devices_router)
app.include_router(traces_router)
app.include_router(queries_router)


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, session=Depends(get_session)):
    traces = session.exec(select(Trace).order_by(desc(Trace.trace_timestamp))).all()

    return RedirectResponse("/traces", status_code=303)
