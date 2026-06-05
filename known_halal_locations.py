KNOWN_HALAL_LOCATIONS = [
    {
        "university": "Korea University",
        "location": "Aegineung Cafeteria, 2F",
        "note": "Korea University reports halal food at Aegineung Cafeteria. Ask staff for today’s halal menu and certification details.",
        "source": "Korea University Sustainability / Cafeteria information",
    },
    {
        "university": "Seoul National University",
        "location": "Gamgol Cafeteria, Building 101 / Asia Center area",
        "note": "SNU has reported halal meal options at Gamgol Cafeteria. Ask staff for current availability.",
        "source": "Korea.net / SNU campus food information",
    },
]


def get_known_halal_locations() -> list[dict]:
    return KNOWN_HALAL_LOCATIONS


if __name__ == "__main__":
    for item in get_known_halal_locations():
        print(f"{item['university']} — {item['location']}")
        print(item["note"])
        print(f"Source: {item['source']}")
        print()