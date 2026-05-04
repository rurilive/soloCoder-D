from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import os

from database import (
    get_db, 
    TimerRecord, 
    TimerMode
)

app = FastAPI(title="番茄工作法计时器")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(
    loader=FileSystemLoader(templates_dir),
    autoescape=select_autoescape(["html", "xml"])
)


class TimerRecordCreate(BaseModel):
    mode: str = Field(..., description="计时模式: work, short-break, long-break, custom")
    duration_seconds: int = Field(..., gt=0, description="倒计时时长（秒）")
    note: Optional[str] = Field(None, max_length=255, description="备注信息")


class TimerRecordResponse(BaseModel):
    id: int
    mode: str
    duration_seconds: int
    completed_at: datetime
    note: Optional[str]

    class Config:
        from_attributes = True


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    template = env.get_template("index.html")
    return HTMLResponse(content=template.render(request=request))


@app.post("/api/records", response_model=TimerRecordResponse)
async def create_timer_record(
    record: TimerRecordCreate,
    db: Session = Depends(get_db)
):
    try:
        mode_enum = TimerMode(record.mode.replace("-", "_").upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="无效的模式。有效模式: work, short-break, long-break, custom"
        )
    
    db_record = TimerRecord(
        mode=mode_enum,
        duration_seconds=record.duration_seconds,
        note=record.note
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    
    response = TimerRecordResponse(
        id=db_record.id,
        mode=db_record.mode.value,
        duration_seconds=db_record.duration_seconds,
        completed_at=db_record.completed_at,
        note=db_record.note
    )
    return response


@app.get("/api/records", response_model=List[TimerRecordResponse])
async def get_timer_records(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    records = db.query(TimerRecord).order_by(
        TimerRecord.completed_at.desc()
    ).offset(skip).limit(limit).all()
    
    response_records = []
    for record in records:
        response_records.append(TimerRecordResponse(
            id=record.id,
            mode=record.mode.value,
            duration_seconds=record.duration_seconds,
            completed_at=record.completed_at,
            note=record.note
        ))
    return response_records


@app.get("/api/records/{record_id}", response_model=TimerRecordResponse)
async def get_timer_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    record = db.query(TimerRecord).filter(TimerRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    response = TimerRecordResponse(
        id=record.id,
        mode=record.mode.value,
        duration_seconds=record.duration_seconds,
        completed_at=record.completed_at,
        note=record.note
    )
    return response


@app.delete("/api/records/{record_id}")
async def delete_timer_record(
    record_id: int,
    db: Session = Depends(get_db)
):
    record = db.query(TimerRecord).filter(TimerRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    db.delete(record)
    db.commit()
    return {"message": "记录已删除", "id": record_id}


if __name__=="__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4444)
