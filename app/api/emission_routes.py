"""Routes for SUNAT emission - Microservice specialized endpoints"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime

from app.utils.logger import logger
from app.services.queue_manager import queue_manager
from app.services.worker_manager import worker_manager
from app.schemas import (
    EmisionRequestSeparated,
    TaskResponse, 
    StatusResponse
)


router = APIRouter(prefix="/emit", tags=["SUNAT Emission"])


class EmissionResponse(TaskResponse):
    """Response model for emission requests"""
    invoice_id: Optional[int] = None


@router.post("/invoice", response_model=EmissionResponse)
async def emit_invoice(request: EmisionRequestSeparated):
    """Emit invoice to SUNAT"""
    try:
        emission_data = {
            "type": "invoice",
            "invoice": request.invoice.model_dump(),
            "sender": request.sender.model_dump(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        task_id = await queue_manager.enqueue_task(emission_data)
        logger.info(f"Invoice emission queued with task_id: {task_id}")
        
        return EmissionResponse(
            task_id=task_id,
            status="ESPERANDO",
            message="Invoice emission queued",
            created_at=datetime.utcnow().isoformat(),
            invoice_id=getattr(request.invoice, 'id', None)
        )
        
    except Exception as e:
        logger.error(f"Error queuing invoice emission: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Emission error: {str(e)}")


@router.post("/credit-note", response_model=EmissionResponse)
async def emit_credit_note(request: EmisionRequestSeparated):
    """Emit credit note to SUNAT"""
    try:
        emission_data = {
            "type": "credit_note",
            "invoice": request.invoice.model_dump(),
            "sender": request.sender.model_dump(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        task_id = await queue_manager.enqueue_task(emission_data)
        logger.info(f"Credit note emission queued with task_id: {task_id}")
        
        return EmissionResponse(
            task_id=task_id,
            status="ESPERANDO",
            message="Credit note emission queued",
            created_at=datetime.utcnow().isoformat(),
            invoice_id=getattr(request.invoice, 'id', None)
        )
        
    except Exception as e:
        logger.error(f"Error queuing credit note emission: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Emission error: {str(e)}")


@router.get("/status/{task_id}", response_model=StatusResponse)
async def get_emission_status(task_id: str):
    """Get emission status by task ID"""
    try:
        task_status = await queue_manager.get_task_result(task_id)
        
        if not task_status:
            raise HTTPException(status_code=404, detail="Task not found")
        
        result = task_status.get("result", {})
        
        # Map scraper result to API response format
        if result.get("success"):
            status = "completed"
        elif result.get("error"):
            status = "failed"
        else:
            status = task_status.get("status", "unknown")
        
        pdf_content = result.get("pdf", {}).get("content") if result.get("pdf") else None
        
        return StatusResponse(
            task_id=task_id,
            status=status,
            message=result.get("message") or result.get("error"),
            pdf_base64=pdf_content,
            sunat_response=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status error: {str(e)}")


@router.get("/tasks", tags=["monitoring"])
async def list_active_tasks():
    """List all active emission tasks"""
    try:
        queue_stats = await queue_manager.get_queue_stats()
        worker_status = await worker_manager.get_status()
        
        return {
            "active_tasks": queue_stats.get("processing", 0),
            "pending_tasks": queue_stats.get("pending", 0),
            "workers": worker_status.get("workers", {})
        }
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Tasks error: {str(e)}")


@router.post("/retry/{task_id}", response_model=EmissionResponse)
async def retry_emission(task_id: str):
    """Retry a failed emission using the same task data"""
    try:
        original_task = await queue_manager.get_task_result(task_id)
        
        if not original_task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        original_data = original_task.get("data", {})
        if not original_data:
            raise HTTPException(
                status_code=400,
                detail=f"Task {task_id} has no valid data to retry"
            )
        
        retry_data = {
            **original_data,
            "retry_of": task_id,
            "retry_count": original_data.get("retry_count", 0) + 1,
            "created_at": datetime.utcnow().isoformat()
        }
        
        new_task_id = await queue_manager.enqueue_task(retry_data)
        logger.info(f"Retry created: {new_task_id} (original: {task_id})")
        
        return EmissionResponse(
            task_id=new_task_id,
            status="ESPERANDO",
            message=f"Retry of task {task_id} queued",
            created_at=datetime.utcnow().isoformat(),
            invoice_id=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Retry error: {str(e)}")

@router.post("/cancel/{task_id}")
async def cancel_emission(task_id: str):
    """Cancel an emission in progress"""
    try:
        success = await queue_manager.cancel_task(task_id)
        
        if success:
            logger.info(f"Task {task_id} cancelled successfully")
            return {
                "task_id": task_id,
                "status": "cancelled",
                "message": "Task cancelled successfully"
            }
        else:
            return {
                "task_id": task_id,
                "status": "not_found_or_completed",
                "message": "Task not found or already completed"
            }
            
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cancel error: {str(e)}")
