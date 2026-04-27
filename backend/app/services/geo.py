LVIV_BOUNDS = {
    "min_lat": 49.77,
    "max_lat": 49.90,
    "min_lng": 23.90,
    "max_lng": 24.10,
}


def is_within_lviv(lat: float, lng: float) -> bool:
    return (
        LVIV_BOUNDS["min_lat"] <= lat <= LVIV_BOUNDS["max_lat"]
        and LVIV_BOUNDS["min_lng"] <= lng <= LVIV_BOUNDS["max_lng"]
    )
