LVIV_BOUNDS = {
    "min_lat": 49.77,
    "max_lat": 49.9,
    "min_lng": 23.9,
    "max_lng": 24.1,
}


def is_within_lviv(lat: float, lng: float) -> bool:
    return (
        LVIV_BOUNDS["min_lat"] <= lat <= LVIV_BOUNDS["max_lat"]
        and LVIV_BOUNDS["min_lng"] <= lng <= LVIV_BOUNDS["max_lng"]
    )
