import math
import os
import pandas as pd
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1", tags=["Archive"])

# Past one-off analysis runs (simulations, manual scans) saved as flat CSVs.
# Not part of the live scoring pipeline — see project README.
ARCHIVE_DIR = "md"


def _list_archive_files():
    if not os.path.isdir(ARCHIVE_DIR):
        return []
    return sorted(f for f in os.listdir(ARCHIVE_DIR) if f.lower().endswith(".csv"))


@router.get("/archive")
async def list_archive():
    """Lists past analysis CSVs saved under md/."""
    return _list_archive_files()


@router.get("/archive/{filename}")
async def get_archive_file(filename: str):
    """Returns one archived CSV's contents as JSON (columns + rows).

    Each file in md/ has its own schema (different past scripts produced
    them) so this returns generic column/row data rather than assuming any
    fixed shape.
    """
    files = _list_archive_files()
    if filename not in files:
        raise HTTPException(status_code=404, detail=f"{filename} not found in archive.")

    df = pd.read_csv(os.path.join(ARCHIVE_DIR, filename))
    rows = df.to_dict(orient="records")
    # NaN isn't valid JSON — pandas keeps numeric columns as float64 even
    # when assigning None, so it has to be swapped out post-conversion.
    for row in rows:
        for key, value in row.items():
            if isinstance(value, float) and math.isnan(value):
                row[key] = None

    return {
        "filename": filename,
        "columns": list(df.columns),
        "rows": rows,
    }
