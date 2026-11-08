"""Import a local journal into the hosted journal's base dataset."""
import argparse
import base64
import hashlib
import json
from pathlib import Path


def import_history(source, destination):
    journal = json.loads(source.read_text(encoding="utf-8-sig"))
    assets = destination / "photos"
    assets.mkdir(parents=True, exist_ok=True)
    for workout in journal["workouts"]:
        # Chat links identify the private conversation rather than a training record.
        workout.pop("source_url", None)
    prefix = "data:image/webp;base64,"
    for dish in journal.get("food_options", []):
        photo = dish.get("photo")
        if not photo or not photo.startswith(prefix):
            continue
        content = base64.b64decode(photo[len(prefix):], validate=True)
        if content[:4] != b"RIFF" or content[8:12] != b"WEBP":
            raise ValueError(f"Invalid WebP photo for {dish['name']}")
        filename = hashlib.sha256(content).hexdigest() + ".webp"
        (assets / filename).write_bytes(content)
        dish["photo"] = "/photos/" + filename
    target = destination / "journal.json"
    draft = target.with_suffix(".tmp")
    draft.write_text(json.dumps(journal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    draft.replace(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    import_history(args.source, Path(__file__).resolve().parent / "data")
