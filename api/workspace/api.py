from ninja import Router

from workspace.models import Lawyer
from workspace.schemas import LawyerOut

router = Router()


@router.get("/lawyers", response=list[LawyerOut])
def list_lawyers(request):
    return Lawyer.objects.order_by("name")
