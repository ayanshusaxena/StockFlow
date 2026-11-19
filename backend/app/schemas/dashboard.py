from pydantic import BaseModel

from app.schemas.inventory import ActivityRead


class DashboardSummary(BaseModel):
    total_units: int
    product_count: int
    store_count: int
    category_count: int
    healthy_balances: int
    low_balances: int
    out_of_stock_balances: int
    total_balances: int
    recent_activity: list[ActivityRead]
