from dataclasses import asdict

from flask import Blueprint, jsonify, request

from app.services.schedule_service import ScheduleService

schedules_bp = Blueprint("schedules", __name__)
schedule_service = ScheduleService()


@schedules_bp.get("/schedules")
def list_schedules():
    try:
        schedules = schedule_service.search(request.args)
    except ValueError as error:
        return jsonify(
            {"error": {"code": "INVALID_PARAMETER", "message": str(error)}}
        ), 422
    return jsonify([asdict(schedule) for schedule in schedules])
