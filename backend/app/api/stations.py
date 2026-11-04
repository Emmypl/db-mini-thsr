from dataclasses import asdict

from flask import Blueprint, jsonify

from app.services.station_service import StationService

stations_bp = Blueprint("stations", __name__)
station_service = StationService()


@stations_bp.get("/stations")
def list_stations():
    """Return station IDs and names, ordered north to south by stations.seq."""
    return jsonify([asdict(station) for station in station_service.list_stations()])
