from __future__ import annotations

import asyncio
import json

from app.database import SessionLocal
from app.source_updater import check_sources


async def main() -> None:
    db = SessionLocal()
    try:
        result = await check_sources(db)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
