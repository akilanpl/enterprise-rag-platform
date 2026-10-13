import uuid
from datetime import datetime, timezone
from decimal import ROUND_CEILING, Decimal

from fastapi import HTTPException
from sqlalchemy import (
    JSON,
    DateTime,
    Integer,
    Numeric,
    String,
    create_engine,
    select,
    text,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Budget(Base):
    __tablename__ = "budgets"
    tenant: Mapped[str] = mapped_column(String(64), primary_key=True)
    month: Mapped[str] = mapped_column(String(7), primary_key=True)
    spent: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal(0))
    reserved: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal(0))


class Usage(Base):
    __tablename__ = "usage"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant: Mapped[str] = mapped_column(String(64), index=True)
    subject: Mapped[str] = mapped_column(String(128))
    month: Mapped[str] = mapped_column(String(7))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    model: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    reservation: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal(0))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    sources: Mapped[list] = mapped_column(JSON, default=list)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    tenant: Mapped[str] = mapped_column(String(64), index=True)
    subject: Mapped[str] = mapped_column(String(128))
    rating: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Ledger:
    def __init__(self, url):
        self.engine = create_engine(url, pool_pre_ping=True)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def create_schema(self):
        # Initial schema bootstrap only. Future releases require explicit migrations.
        Base.metadata.create_all(self.engine)

    def ping(self):
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.execute(select(Budget).limit(1))

    def reserve(self, principal, model, amount, budget, request_id=None):
        now = datetime.now(timezone.utc)
        month = now.strftime("%Y-%m")
        amount = Decimal(str(amount)).quantize(Decimal("0.00000001"), rounding=ROUND_CEILING)
        with self.sessions() as session:
            if session.get(Budget, (principal.tenant, month)) is None:
                session.add(Budget(tenant=principal.tenant, month=month))
                try:
                    session.commit()
                except IntegrityError:
                    session.rollback()  # Another worker inserted this tenant/month.
            session.commit()  # Close the read transaction before atomic reservation.
            with session.begin():
                result = session.execute(
                    update(Budget)
                    .where(
                        Budget.tenant == principal.tenant,
                        Budget.month == month,
                        Budget.spent + Budget.reserved + amount <= Decimal(str(budget)),
                    )
                    .values(reserved=Budget.reserved + amount)
                )
                if result.rowcount != 1:
                    raise HTTPException(402, "Monthly tenant budget exhausted")
                record = Usage(
                    id=request_id or str(uuid.uuid4()),
                    tenant=principal.tenant,
                    subject=principal.subject,
                    month=month,
                    created_at=now,
                    model=model,
                    status="reserved",
                    reservation=amount,
                )
                session.add(record)
            return record.id

    def settle(self, identifier, cost, prompt_tokens, completion_tokens, sources, failed=False):
        with self.sessions.begin() as session:
            record = session.execute(
                select(Usage).where(Usage.id == identifier).with_for_update()
            ).scalar_one()
            if record.status != "reserved":
                return
            # An ambiguous provider failure retains its full reservation as a charge.
            charged = (
                record.reservation
                if failed
                else Decimal(str(cost)).quantize(Decimal("0.00000001"), rounding=ROUND_CEILING)
            )
            session.execute(
                update(Budget)
                .where(
                    Budget.tenant == record.tenant,
                    Budget.month == record.month,
                )
                .values(reserved=Budget.reserved - record.reservation, spent=Budget.spent + charged)
            )
            record.status = "failed_reserved" if failed else "completed"
            record.cost = charged
            record.prompt_tokens = prompt_tokens
            record.completion_tokens = completion_tokens
            record.sources = sources

    def usage(self, principal):
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        with self.sessions() as session:
            budget = session.get(Budget, (principal.tenant, month))
            return {
                "tenant": principal.tenant,
                "month": month,
                "spent_usd": float(budget.spent) if budget else 0,
                "reserved_usd": float(budget.reserved) if budget else 0,
            }

    def feedback(self, principal, request_id, rating):
        with self.sessions.begin() as session:
            record = session.get(Usage, request_id)
            if (
                not record
                or record.tenant != principal.tenant
                or record.subject != principal.subject
            ):
                raise HTTPException(404, "Request not found")
            session.add(
                Feedback(
                    id=str(uuid.uuid4()),
                    request_id=request_id,
                    tenant=principal.tenant,
                    subject=principal.subject,
                    rating=rating,
                    created_at=datetime.now(timezone.utc),
                )
            )
