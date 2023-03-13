import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Detection(Base):
    __tablename__ = "detection"
    # ...


# EXAMPLE
meta = Base.metadata
item_t = meta.tables[Item.__tablename__]
detection_t = meta.tables[Detection.__tablename__]

target_shop_id = 1  # test value

ins = item_t.insert().from_select(
    ["detection_id", "price_in_dollar"],
    sa.select(
        [
            detection_t.c.id.label("detection_id"),
            (detection_t.c.price_in_cents / sa.text("100")).label(
                "price_in_dollar"
            ),
        ]
    ).where(detection_t.c.shop_id == target_shop_id),
)

with engine.begin() as conn:
    conn.execute(ins)