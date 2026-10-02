from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.schemas.api_schemas import ExportRequest
from backend.app.services.export_service import generate_validated_export

router = APIRouter(tags=["Exports"])


@router.post("/api/exports", status_code=status.HTTP_201_CREATED)
def api_create_export(
    req: ExportRequest,
    db: Session = Depends(get_db),
):
    return generate_validated_export(db, req)


@router.get("/api/exports/download")
def api_download_export(
    file_path: Optional[str] = Query(default=None),
    project_id: str = Query(default="PROJ_SIH26012_DEMO"),
    scene_id: str = Query(default="scene_urban_T1"),
    export_format: str = Query(default="GeoJSON"),
    db: Session = Depends(get_db),
):
    if file_path:
        try:
            resolved = Path(file_path).resolve()
            outputs_root = settings.outputs_dir.resolve()
            if not str(resolved).startswith(str(outputs_root)):
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: requested export path is outside the authorized outputs directory.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid file_path: {exc}") from exc

        if not resolved.exists() or not resolved.is_file():
            raise HTTPException(
                status_code=404, detail="Requested export file not found on disk."
            )
        return FileResponse(path=str(resolved), filename=resolved.name)

    res = generate_validated_export(
        db,
        ExportRequest(
            project_id=project_id,
            scene_id=scene_id,
            export_format=export_format,
        ),
    )
    target_path = Path(res["export_path"])
    if not target_path.exists():
        raise HTTPException(
            status_code=404, detail="Generated export file not found on disk."
        )
    return FileResponse(path=str(target_path), filename=target_path.name)
