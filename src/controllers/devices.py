import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request, Form
from sqlmodel import select
from starlette.responses import HTMLResponse, RedirectResponse

from src.common.db import get_session, Device
from src.common.templates import templates

app = APIRouter()


@app.get("/devices", response_class=HTMLResponse)
def read_devices(request: Request, session=Depends(get_session)):
    devices = session.exec(select(Device).order_by(Device.device_uuid)).all()

    return templates.TemplateResponse(
        "devices/browse.html",
        context={
            "request": request,
            "devices": devices,
        },
    )


@app.get("/devices/add", response_class=HTMLResponse)
def read_devices(request: Request, session=Depends(get_session)):
    return templates.TemplateResponse(
        "devices/add.html",
        context={
            "request": request,
        },
    )


@app.post("/devices/add", response_class=HTMLResponse)
async def add_device(request: Request, device_name: str = Form(...), device_uuid: Optional[str] = Form(None),
                     session=Depends(get_session)):
    try:
        new_device = Device(
            device_id=str(uuid.uuid4()),
            device_name=device_name,
            device_uuid=device_uuid
        )
        session.add(new_device)
        session.commit()
        session.refresh(new_device)

        print(f"Added device: {new_device}")

        return RedirectResponse("/devices", status_code=303)
    except Exception as e:
        session.rollback()
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": str(e),
            }
        )


@app.get("/devices/{device_id}/edit", response_class=HTMLResponse)
def read_edit_device(request: Request, device_id: str, session=Depends(get_session)):
    device = session.exec(select(Device).where(Device.device_id == device_id)).first()
    if not device:
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": "No device found",
            }
        )
    return templates.TemplateResponse(
        "devices/edit.html",
        context={
            "request": request,
            "device": device,
        }
    )


@app.post("/devices/{device_id}/edit", response_class=HTMLResponse)
async def edit_device(request: Request, device_id: str, device_name: str = Form(...),
                      device_uuid: Optional[str] = Form(None),
                      session=Depends(get_session)):
    try:
        device = session.exec(select(Device).where(Device.device_id == device_id)).first()
        device.device_name = device_name
        device.device_uuid = device_uuid
        session.commit()
        session.refresh(device)
        return RedirectResponse("/devices", status_code=303)
    except Exception as e:
        session.rollback()
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": str(e),
            }
        )


@app.post("/devices/{device_id}/delete", response_class=HTMLResponse)
async def delete_device(request: Request, device_id: str, session=Depends(get_session)):
    device = session.exec(select(Device).where(Device.device_id == device_id)).first()
    if not device:
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
            }
        )
    session.delete(device)
    session.commit()
    return RedirectResponse("/devices", status_code=303)


@app.post("/devices/{device_id}/action/{action}", response_class=HTMLResponse)
async def device_action(request: Request, device_id: str, action: str,
                        session=Depends(get_session)):
    try:
        raise NotImplementedError("Device actions are not implemented yet")
        print(f"Device: {device_id}, Action: {action}")
        session.commit()
        session.refresh()
        return RedirectResponse("/devices", status_code=303)
    except Exception as e:
        session.rollback()
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": str(e),
            }
        )
