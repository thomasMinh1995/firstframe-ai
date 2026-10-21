from fastapi import APIRouter, HTTPException

from app.application.dataset_review import reviewed_scenarios
from app.application.demo import DemoScenario, DemoSummary

router = APIRouter(prefix="/api/demo", tags=["local demo"])


@router.get("/scenarios", response_model=list[DemoSummary])
def list_scenarios(curated: bool = False):
    return reviewed_scenarios(curated)


@router.get("/scenarios/{scenario_id}", response_model=DemoScenario)
def get_scenario(scenario_id: str, curated: bool = False):
    for scenario in reviewed_scenarios(curated):
        if scenario.id == scenario_id:
            return scenario
    raise HTTPException(404, "Kịch bản không còn trong dữ liệu demo. Hãy tải lại danh sách.")
