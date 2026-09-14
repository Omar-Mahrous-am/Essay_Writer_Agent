import logging
from fastapi import APIRouter, HTTPException, status
from src.schemas.say_writer import EssayRequest, EssayResponse
from src.controllers.Essay_Writer_Agent_Controller import EssayWriterAgentController

logger = logging.getLogger(__name__)

essay_router = APIRouter(prefix="/api/v1/essay", tags=["Essay Writer"])


@essay_router.post("/say_writer", response_model=EssayResponse)
@essay_router.post("", response_model=EssayResponse)
async def say_writer(payload: EssayRequest):
    """
    Generate and iteratively refine an essay based on the provided topic.

    - **task**: Topic or prompt for the essay.
    - **max_revisions**: Max critique & revision loops (default 2).
    """
    try:
        controller = EssayWriterAgentController()
        result = controller.run(
            task=payload.task,
            max_revisions=payload.max_revisions
        )
        return EssayResponse(
            task=payload.task,
            plan=result.get("plan"),
            draft=result.get("draft"),
            critique=result.get("critique"),
            content=result.get("content", []),
            revision_number=result.get("revision_number", 1)
        )
    except Exception as e:
        logger.exception("Failed to execute essay writer workflow: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing essay writing request: {str(e)}"
        )
