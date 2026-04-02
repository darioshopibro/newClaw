#!/usr/bin/env python3
"""
airtable_venues.py - Fetch padel venues from Airtable by city.

Usage:
  python3 airtable_venues.py --city Dubai
  python3 airtable_venues.py --city Dubai --priority   # DubaiPriority table (sorted)
  python3 airtable_venues.py --list-cities              # List available cities

Output: JSON array of venues
"""

import os
import sys
import json
import argparse
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from logger import venues_log as log

# Airtable config
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY", "")
AIRTABLE_BASE_ID = "appGJPPF2t2bhoFZg"  # Padel base
AIRTABLE_API_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"

# Fallback: read from /etc/environment if env var not set
if not AIRTABLE_API_KEY:
    try:
        with open("/etc/environment", "r") as f:
            for line in f:
                if line.startswith("AIRTABLE_API_KEY="):
                    AIRTABLE_API_KEY = line.strip().split("=", 1)[1].strip('"').strip("'")
                    break
    except Exception:
        pass

# City → Table ID mapping
CITY_TABLES = {
    "dubai": "tblEM74rGjwhsHtrr",
    "dubai_priority": "tblpclziWv6EZuxGe",
    "jurmala": "tbluNHFaqzu5XEoqX",
    "lisbon": "tblhwDOLUIokL00bk",
    "tel_aviv": "tblCvLG2cHsgXR2SX",
    "belgrade": "tblwUAHDjTTfwrx5d",
}

# Display names
CITY_DISPLAY = {
    "dubai": "Dubai",
    "jurmala": "Jurmala",
    "lisbon": "Lisbon",
    "tel_aviv": "Tel Aviv",
    "belgrade": "Belgrade",
}

# Fields to fetch for regular city tables
VENUE_FIELDS = [
    "Name",
    "Phone",
    "Playtomic Website",
    "Primary Booking Method",
    "Secondary Booking Method",
    "Availability Methods",
    "WA link",
    "Website Link",
    "Location",
    "Indoor/outdoor",
    "Opening hours",
]

# DubaiPriority has different field names
PRIORITY_FIELDS = [
    "Priority",
    "Name",
    "Phone",
    "Playtomic Website",
    "Preferred Method",
    "Availability Methods",
    "WA link",
    "Website Link",
    "Location",
    "Price per 1hr",
    "Showers",
]


def normalize_city(city: str) -> str:
    """Normalize city name to key."""
    city_lower = city.lower().strip().replace(" ", "_")
    # Handle common variations
    aliases = {
        "tel aviv": "tel_aviv",
        "telaviv": "tel_aviv",
        "tel-aviv": "tel_aviv",
    }
    return aliases.get(city.lower().strip(), city_lower)


def fetch_venues(table_id: str, fields: list, sort_field: str = None) -> list:
    """Fetch records from Airtable table."""
    if not AIRTABLE_API_KEY:
        log("ERROR: AIRTABLE_API_KEY environment variable not set")
        return []

    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }

    params = {}
    if fields:
        params["fields[]"] = fields
    if sort_field:
        params["sort[0][field]"] = sort_field
        params["sort[0][direction]"] = "asc"

    all_records = []
    offset = None

    while True:
        if offset:
            params["offset"] = offset

        try:
            resp = requests.get(
                f"{AIRTABLE_API_URL}/{table_id}",
                headers=headers,
                params=params,
                timeout=15,
            )

            if resp.status_code != 200:
                log(f"Airtable API error {resp.status_code}: {resp.text[:200]}")
                return []

            data = resp.json()
            records = data.get("records", [])
            all_records.extend(records)

            offset = data.get("offset")
            if not offset:
                break

        except Exception as e:
            log(f"Airtable fetch error: {e}")
            return []

    return all_records


def parse_venue(record: dict, is_priority: bool = False) -> dict:
    """Parse Airtable record into clean venue dict."""
    fields = record.get("fields", {})

    venue = {
        "id": record.get("id", ""),
        "name": fields.get("Name", "Unknown"),
        "phone": str(fields.get("Phone", "")),
        "playtomic_url": fields.get("Playtomic Website", ""),
        "availability_methods": fields.get("Availability Methods", []),
        "wa_link": fields.get("WA link", ""),
        "website": fields.get("Website Link", ""),
        "location": fields.get("Location", ""),
        "indoor_outdoor": fields.get("Indoor/outdoor", ""),
        "opening_hours": fields.get("Opening hours", ""),
    }

    if is_priority:
        venue["priority"] = fields.get("Priority", 999)
        venue["price_per_hour"] = fields.get("Price per 1hr", "")
        venue["showers"] = fields.get("Showers", False)
        venue["preferred_method"] = fields.get("Preferred Method", [])
        venue["primary_booking"] = fields.get("Preferred Method", [])
        venue["secondary_booking"] = []
    else:
        venue["primary_booking"] = fields.get("Primary Booking Method", [])
        venue["secondary_booking"] = fields.get("Secondary Booking Method", [])

    # Clean up: ensure booking methods are lists
    if isinstance(venue["primary_booking"], str):
        venue["primary_booking"] = [venue["primary_booking"]]
    if isinstance(venue["secondary_booking"], str):
        venue["secondary_booking"] = [venue["secondary_booking"]]
    if isinstance(venue["availability_methods"], str):
        venue["availability_methods"] = [venue["availability_methods"]]

    return venue


def get_venues(city: str, use_priority: bool = False) -> list:
    """Get venues for a city."""
    city_key = normalize_city(city)

    if use_priority and city_key == "dubai":
        table_id = CITY_TABLES["dubai_priority"]
        fields = PRIORITY_FIELDS
        sort_field = "Priority"
        is_priority = True
        log(f"Fetching Dubai priority venues")
    elif city_key in CITY_TABLES:
        table_id = CITY_TABLES[city_key]
        fields = VENUE_FIELDS
        sort_field = "Name"
        is_priority = False
        log(f"Fetching venues for {city_key}")
    else:
        log(f"Unknown city: {city}")
        return []

    records = fetch_venues(table_id, fields, sort_field)
    venues = [parse_venue(r, is_priority) for r in records]

    # Filter out venues without a name
    venues = [v for v in venues if v["name"] and v["name"] != "Unknown"]

    log(f"Found {len(venues)} venues for {city_key}")
    return venues


def list_cities() -> list:
    """List available cities."""
    return [
        {"key": k, "name": CITY_DISPLAY.get(k, k)}
        for k in CITY_DISPLAY.keys()
    ]


def main():
    parser = argparse.ArgumentParser(description="Fetch padel venues from Airtable")
    parser.add_argument("--city", help="City name (Dubai, Belgrade, Lisbon, Tel Aviv, Jurmala)")
    parser.add_argument("--priority", action="store_true", help="Use DubaiPriority table (Dubai only)")
    parser.add_argument("--list-cities", action="store_true", help="List available cities")

    args = parser.parse_args()

    if args.list_cities:
        cities = list_cities()
        print(json.dumps(cities, indent=2))
        return

    if not args.city:
        parser.error("--city is required (or use --list-cities)")
        return

    venues = get_venues(args.city, args.priority)
    print(json.dumps(venues, indent=2))


if __name__ == "__main__":
    main()
