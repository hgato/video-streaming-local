import json
import os
import sys

import requests

RENAMER_URL = os.environ.get("RENAMER_URL", "http://renamer-service:8000")
VIDEOS_URL = os.environ.get("VIDEOS_URL", "http://videos-service:8001")


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.main <input.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    file = data["file"]
    name = data["name"]
    year = str(data["year"])

    print(f"Renaming {file!r} -> {name!r} ({year})")
    resp = requests.post(f"{RENAMER_URL}/", json={"file": file, "name": name, "year": int(year)})
    resp.raise_for_status()
    renamed = resp.json()["renamed"]
    print(f"Renamed to {renamed!r}")

    print("Saving video record")
    resp = requests.post(
        f"{VIDEOS_URL}/internal/videos",
        json={"name": name, "year": year, "filename": renamed},
    )
    resp.raise_for_status()
    video = resp.json()
    print(f"Done: id={video['id']} name={video['name']} year={video['year']} filename={renamed}")


if __name__ == "__main__":
    main()
