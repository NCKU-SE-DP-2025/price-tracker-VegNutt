from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
import requests
import sentry_sdk


router = APIRouter(prefix="/api/v1/prices", tags=["prices"])


@router.get("/necessities-price")
def get_necessities_prices(
    category: Optional[str] = Query(None),
    commodity: Optional[str] = Query(None),
):
    try:
        response = requests.get(
            "https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice",
            params={"CategoryName": category, "Name": commodity},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise HTTPException(status_code=502, detail="Failed to fetch price data")
