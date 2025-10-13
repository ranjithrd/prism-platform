import uuid

from fastapi import APIRouter, Depends, Request, Form
from sqlmodel import select
from starlette.responses import HTMLResponse, RedirectResponse

from src.common.db import get_session, Config, Device
from src.common.templates import templates

app = APIRouter()


@app.get("/configs", response_class=HTMLResponse)
def read_configs(request: Request, session=Depends(get_session)):
    configs = session.exec(select(Config).order_by(Config.config_name)).all()
    devices = session.exec(select(Device).order_by(Device.device_name)).all()

    # Create list of all device serials for "Run on All Devices" functionality
    all_device_serials = [device.device_uuid or device.device_id for device in devices if
                          device.device_uuid or device.device_id]

    return templates.TemplateResponse(
        "configs/browse.html",
        context={
            "request": request,
            "configs": configs,
            "devices": devices,
            "all_device_serials": all_device_serials,
        },
    )


@app.get("/configs/add", response_class=HTMLResponse)
def read_add_config(request: Request):
    return templates.TemplateResponse(
        "configs/add.html",
        context={"request": request},
    )


@app.post("/configs/add", response_class=HTMLResponse)
async def add_config(request: Request, config_name: str = Form(...), config_text: str = Form(...),
                     session=Depends(get_session)):
    try:
        new_config = Config(
            config_id=str(uuid.uuid4()),
            config_name=config_name,
            config_text=config_text
        )
        session.add(new_config)
        session.commit()
        session.refresh(new_config)

        return RedirectResponse("/configs", status_code=303)
    except Exception as e:
        session.rollback()
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": str(e),
            }
        )


@app.get("/configs/{config_id}", response_class=HTMLResponse)
def read_config(request: Request, config_id: str, session=Depends(get_session)):
    config = session.exec(select(Config).where(Config.config_id == config_id)).first()
    if not config:
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": "No config found",
            }
        )
    return templates.TemplateResponse(
        "configs/edit.html",
        context={
            "request": request,
            "config": config,
        }
    )


@app.post("/configs/{config_id}/edit", response_class=HTMLResponse)
async def edit_config(request: Request, config_id: str, config_name: str = Form(...),
                      config_text: str = Form(...),
                      session=Depends(get_session)):
    try:
        config = session.exec(select(Config).where(Config.config_id == config_id)).first()
        if not config:
            return templates.TemplateResponse(
                "error.html",
                context={
                    "request": request,
                    "error": "No config found",
                }
            )
        config.config_name = config_name
        config.config_text = config_text
        session.commit()
        session.refresh(config)
        return RedirectResponse(f"/configs/{config_id}", status_code=303)
    except Exception as e:
        session.rollback()
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": str(e),
            }
        )


@app.post("/configs/{config_id}/delete", response_class=HTMLResponse)
async def delete_config(request: Request, config_id: str, session=Depends(get_session)):
    try:
        config = session.exec(select(Config).where(Config.config_id == config_id)).first()
        if not config:
            return templates.TemplateResponse(
                "error.html",
                context={
                    "request": request,
                    "error": "No config found",
                }
            )
        session.delete(config)
        session.commit()
        return RedirectResponse("/configs", status_code=303)
    except Exception as e:
        session.rollback()
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": str(e),
            }
        )
