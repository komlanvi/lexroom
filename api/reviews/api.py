from ninja import Router

from reviews import clock
from reviews.schemas import PlanOut
from reviews.services.plan import get_plan

router = Router()


@router.get("/plan", response=PlanOut)
def plan(request):
    return get_plan(clock.clock.now())
