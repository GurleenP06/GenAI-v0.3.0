"""RLPM (Requirements Lifecycle Process Management) routes."""

import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/rlpm/status")
async def rlpm_status():
    try:
        from oskar.rlpm import RLPMIndexManager

        if RLPMIndexManager.is_initialized():
            mgr = RLPMIndexManager._instance
            return {
                "status": "initialized",
                "reference_chunks": len(mgr.corpus) if mgr.corpus else 0,
                "fewshot_examples": len(mgr.fewshot_examples) if mgr.fewshot_examples else 0,
                "comparisons": list(mgr.comparisons.keys()) if mgr.comparisons else [],
            }
        else:
            return {"status": "not_initialized"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/rlpm/rebuild")
async def rlpm_rebuild():
    try:
        from oskar.rlpm import RLPMKnowledgeBuilder, RLPMIndexManager

        RLPMIndexManager._initialized = False

        builder = RLPMKnowledgeBuilder()
        result = builder.build_all()

        RLPMIndexManager.initialize()

        return {"status": "rebuilt", "result": result}
    except Exception as e:
        logger.error(f"RLPM rebuild error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rlpm/comparisons")
async def rlpm_comparisons():
    try:
        from oskar.rlpm import get_rlpm_manager, ensure_rlpm_initialized

        ensure_rlpm_initialized()
        mgr = get_rlpm_manager()
        return {"comparisons": mgr.comparisons}
    except Exception as e:
        return {"error": str(e)}
