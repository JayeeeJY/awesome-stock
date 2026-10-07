"""Authenticated projection for the static Academy library."""

from awesome_stock.academy.library import AcademyDocument, build_academy_library
from awesome_stock.api.contracts import ApiResponse, problem_from_exception


def _document(item: AcademyDocument) -> dict[str, object]:
    return {
        "document_id": item.document_id,
        "category": item.category,
        "category_label": item.category_label,
        "title": item.title,
        "short_title": item.short_title,
        "lead": item.lead,
        "definition": item.definition,
        "reading_points": item.reading_points,
        "misreads": item.misreads,
        "checklist": item.checklist,
        "diagram": item.diagram,
        "formula": item.formula,
    }


def library_response(runtime, *, access_token: str, request_id: object = None) -> ApiResponse:
    try:
        failure = runtime.portfolio(access_token, request_id=request_id)
        if failure.problem is not None:
            return failure
        library = build_academy_library()
        return ApiResponse(200, data={
            "mode": "static_knowledge",
            "persistence": False,
            "ai_generated": False,
            "external_provider": False,
            "live_market_data": False,
            "investment_advice": False,
            "documents": tuple(_document(item) for item in library.documents),
        })
    except Exception as error:
        return ApiResponse.failure(problem_from_exception(error, request_id=request_id))
