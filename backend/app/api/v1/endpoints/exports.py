import csv
import io
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.listing import Listing
from app.models.location import Location
from app.models.property import Property, PropertyType

router = APIRouter()

HEADERS = ["İlan ID", "Gayrimenkul ID", "Tür", "Konum", "İlan Fiyatı", "Para Birimi", "Durum", "Kaynak", "Kaynak URL", "Oluşturulma", "Güncellenme"]


def _rows(db: Session, limit: int, include_archived: bool):
    stmt = (select(Listing, Property, PropertyType, Location)
        .join(Property, Listing.property_id == Property.id)
        .join(PropertyType, Property.property_type_id == PropertyType.id)
        .join(Location, Property.location_id == Location.id)
        .order_by(Listing.id.desc()).limit(limit))
    if not include_archived:
        stmt = stmt.where(Listing.archived_at.is_(None))
    for listing, prop, ptype, location in db.execute(stmt):
        yield [listing.id, prop.id, ptype.name, location.name, str(listing.asking_price), listing.currency, listing.status, listing.source_name or listing.source_type, listing.source_url or "", listing.created_at.isoformat(), listing.updated_at.isoformat()]


def _safe_spreadsheet_text(value):
    text_value = str(value if value is not None else "")
    if text_value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text_value
    return text_value


@router.get("/listings.csv")
def export_listings_csv(
    limit: int = Query(default=1000, ge=1, le=5000),
    include_archived: bool = False,
    db: Session = Depends(get_db),
):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(HEADERS)
    writer.writerows([_safe_spreadsheet_text(value) for value in row] for row in _rows(db, limit, include_archived))
    payload = "\ufeff" + stream.getvalue()
    return StreamingResponse(iter([payload]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="real-estate-listings.csv"'})


@router.get("/listings.xlsx")
def export_listings_xlsx(
    limit: int = Query(default=1000, ge=1, le=5000),
    include_archived: bool = False,
    db: Session = Depends(get_db),
):
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("İlanlar")
    sheet.append(HEADERS)
    for row in _rows(db, limit, include_archived):
        safe_row = []
        for value in row:
            if isinstance(value, (int, Decimal)):
                safe_row.append(value)
            else:
                cell = WriteOnlyCell(sheet, value=_safe_spreadsheet_text(value))
                cell.data_type = "s"
                safe_row.append(cell)
        sheet.append(safe_row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="real-estate-listings.xlsx"'})
