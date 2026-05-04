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
    TimerMode,
    WorkCycle,
    CycleSegment,
    CycleStatus
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
    cycle_segment_id: Optional[int]

    class Config:
        from_attributes = True


class CycleSegmentResponse(BaseModel):
    id: int
    work_cycle_id: int
    segment_order: int
    segment_type: str
    duration_seconds: int
    is_completed: bool
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class WorkCycleCreate(BaseModel):
    name: Optional[str] = Field("默认循环", max_length=100, description="循环名称")
    total_pomodoros: int = Field(4, gt=0, le=20, description="总番茄钟数量")
    work_duration_minutes: int = Field(25, gt=0, le=60, description="工作时长（分钟）")
    short_break_duration_minutes: int = Field(5, gt=0, le=30, description="短休息时长（分钟）")
    long_break_duration_minutes: int = Field(15, gt=0, le=60, description="长休息时长（分钟）")


class WorkCycleResponse(BaseModel):
    id: int
    name: Optional[str]
    total_pomodoros: int
    completed_pomodoros: int
    work_duration_minutes: int
    short_break_duration_minutes: int
    long_break_duration_minutes: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    segments: List[CycleSegmentResponse] = []

    class Config:
        from_attributes = True


class WorkCycleUpdateStatus(BaseModel):
    status: str = Field(..., description="新状态: pending, running, completed, cancelled")


class CycleSegmentComplete(BaseModel):
    cycle_segment_id: int = Field(..., description="循环阶段ID")


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


def generate_cycle_segments(work_cycle: WorkCycle) -> List[CycleSegment]:
    segments = []
    segment_order = 0
    
    for i in range(work_cycle.total_pomodoros):
        segment_order += 1
        segments.append(CycleSegment(
            work_cycle_id=work_cycle.id,
            segment_order=segment_order,
            segment_type=TimerMode.WORK,
            duration_seconds=work_cycle.work_duration_minutes * 60,
            is_completed=False
        ))
        
        if i < work_cycle.total_pomodoros - 1:
            segment_order += 1
            if (i + 1) % 4 == 0:
                segments.append(CycleSegment(
                    work_cycle_id=work_cycle.id,
                    segment_order=segment_order,
                    segment_type=TimerMode.LONG_BREAK,
                    duration_seconds=work_cycle.long_break_duration_minutes * 60,
                    is_completed=False
                ))
            else:
                segments.append(CycleSegment(
                    work_cycle_id=work_cycle.id,
                    segment_order=segment_order,
                    segment_type=TimerMode.SHORT_BREAK,
                    duration_seconds=work_cycle.short_break_duration_minutes * 60,
                    is_completed=False
                ))
    
    return segments


def build_work_cycle_response(work_cycle: WorkCycle) -> WorkCycleResponse:
    segments_response = []
    for segment in work_cycle.segments:
        segments_response.append(CycleSegmentResponse(
            id=segment.id,
            work_cycle_id=segment.work_cycle_id,
            segment_order=segment.segment_order,
            segment_type=segment.segment_type.value,
            duration_seconds=segment.duration_seconds,
            is_completed=segment.is_completed,
            completed_at=segment.completed_at
        ))
    
    return WorkCycleResponse(
        id=work_cycle.id,
        name=work_cycle.name,
        total_pomodoros=work_cycle.total_pomodoros,
        completed_pomodoros=work_cycle.completed_pomodoros,
        work_duration_minutes=work_cycle.work_duration_minutes,
        short_break_duration_minutes=work_cycle.short_break_duration_minutes,
        long_break_duration_minutes=work_cycle.long_break_duration_minutes,
        status=work_cycle.status.value,
        created_at=work_cycle.created_at,
        completed_at=work_cycle.completed_at,
        segments=segments_response
    )


@app.post("/api/cycles", response_model=WorkCycleResponse)
async def create_work_cycle(
    cycle: WorkCycleCreate,
    db: Session = Depends(get_db)
):
    db_cycle = WorkCycle(
        name=cycle.name,
        total_pomodoros=cycle.total_pomodoros,
        completed_pomodoros=0,
        work_duration_minutes=cycle.work_duration_minutes,
        short_break_duration_minutes=cycle.short_break_duration_minutes,
        long_break_duration_minutes=cycle.long_break_duration_minutes,
        status=CycleStatus.PENDING,
        created_at=datetime.utcnow()
    )
    db.add(db_cycle)
    db.commit()
    db.refresh(db_cycle)
    
    segments = generate_cycle_segments(db_cycle)
    for segment in segments:
        db.add(segment)
    db.commit()
    
    db.refresh(db_cycle)
    return build_work_cycle_response(db_cycle)


@app.get("/api/cycles", response_model=List[WorkCycleResponse])
async def get_work_cycles(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(WorkCycle)
    if status:
        try:
            status_enum = CycleStatus(status.upper().replace("-", "_"))
            query = query.filter(WorkCycle.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的状态值")
    
    cycles = query.order_by(WorkCycle.created_at.desc()).offset(skip).limit(limit).all()
    
    return [build_work_cycle_response(cycle) for cycle in cycles]


@app.get("/api/cycles/{cycle_id}", response_model=WorkCycleResponse)
async def get_work_cycle(
    cycle_id: int,
    db: Session = Depends(get_db)
):
    cycle = db.query(WorkCycle).filter(WorkCycle.id == cycle_id).first()
    if cycle is None:
        raise HTTPException(status_code=404, detail="循环不存在")
    
    return build_work_cycle_response(cycle)


@app.put("/api/cycles/{cycle_id}/status", response_model=WorkCycleResponse)
async def update_cycle_status(
    cycle_id: int,
    status_update: WorkCycleUpdateStatus,
    db: Session = Depends(get_db)
):
    cycle = db.query(WorkCycle).filter(WorkCycle.id == cycle_id).first()
    if cycle is None:
        raise HTTPException(status_code=404, detail="循环不存在")
    
    try:
        new_status = CycleStatus(status_update.status.upper().replace("-", "_"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="无效的状态。有效状态: pending, running, completed, cancelled"
        )
    
    cycle.status = new_status
    
    if new_status == CycleStatus.COMPLETED:
        cycle.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(cycle)
    
    return build_work_cycle_response(cycle)


@app.post("/api/cycles/{cycle_id}/segments/{segment_id}/complete", response_model=WorkCycleResponse)
async def complete_cycle_segment(
    cycle_id: int,
    segment_id: int,
    db: Session = Depends(get_db)
):
    cycle = db.query(WorkCycle).filter(WorkCycle.id == cycle_id).first()
    if cycle is None:
        raise HTTPException(status_code=404, detail="循环不存在")
    
    segment = db.query(CycleSegment).filter(
        CycleSegment.id == segment_id,
        CycleSegment.work_cycle_id == cycle_id
    ).first()
    
    if segment is None:
        raise HTTPException(status_code=404, detail="阶段不存在")
    
    if segment.is_completed:
        raise HTTPException(status_code=400, detail="该阶段已完成")
    
    segment.is_completed = True
    segment.completed_at = datetime.utcnow()
    
    if segment.segment_type == TimerMode.WORK:
        cycle.completed_pomodoros += 1
    
    all_segments_completed = all(s.is_completed for s in cycle.segments)
    if all_segments_completed:
        cycle.status = CycleStatus.COMPLETED
        cycle.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(cycle)
    
    return build_work_cycle_response(cycle)


@app.delete("/api/cycles/{cycle_id}")
async def delete_work_cycle(
    cycle_id: int,
    db: Session = Depends(get_db)
):
    cycle = db.query(WorkCycle).filter(WorkCycle.id == cycle_id).first()
    if cycle is None:
        raise HTTPException(status_code=404, detail="循环不存在")
    
    db.delete(cycle)
    db.commit()
    return {"message": "循环已删除", "id": cycle_id}


if __name__=="__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4444)
