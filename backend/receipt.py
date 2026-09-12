from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Supermarket = Literal["mercadona", "carrefour", "bonpreu", "elcorteingles", "alcampo"]
Money = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


def validate_barcode(value):
    if value:
        digits = [int(c) for c in value]
        check = (
            10
            - sum(
                n * (3 if i % 2 == 0 else 1)
                for i, n in enumerate(reversed(digits[:-1]))
            )
            % 10
        ) % 10
        if digits[-1] != check:
            raise ValueError("Código de barras inválido")
    return value


class ReceiptLine(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    raw_name: str = Field(min_length=1, max_length=250)
    canonical_name: str = Field(min_length=1, max_length=250)
    quantity: Decimal = Field(gt=0, le=10000, max_digits=12, decimal_places=4)
    unit_price: Money
    total_price: Money
    barcode: str = Field(
        default="", max_length=14, pattern=r"^([0-9]{8}|[0-9]{12,14})?$"
    )

    @field_validator("barcode")
    @classmethod
    def valid_barcode(cls, value):
        return validate_barcode(value)


class Receipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supermarket: Supermarket | Literal["unknown"]
    date: date | None
    total: Money
    products: list[ReceiptLine] = Field(min_length=1, max_length=100)

    def warnings(self):
        warnings = []
        if abs(sum(p.total_price for p in self.products) - self.total) > Decimal(
            "0.02"
        ):
            warnings.append(
                "El total del ticket no coincide con la suma de sus líneas."
            )
        if not self.date:
            warnings.append("Falta la fecha del ticket.")
        if self.supermarket == "unknown":
            warnings.append("Selecciona el supermercado antes de guardar.")
        return warnings


class ReviewedReceipt(Receipt):
    receipt_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def reconciled(self):
        if self.warnings():
            raise ValueError(" ".join(self.warnings()))
        return self


class ManualProductInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    barcode: str = Field(
        default="", max_length=14, pattern=r"^([0-9]{8}|[0-9]{12,14})?$"
    )
    name: str = Field(min_length=1, max_length=250)
    supermarket: Supermarket
    category: str = Field(default="", max_length=100)
    price: Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]

    @field_validator("barcode")
    @classmethod
    def valid_barcode(cls, value):
        if value:
            digits = [int(c) for c in value]
            check = (
                10
                - sum(
                    n * (3 if i % 2 == 0 else 1)
                    for i, n in enumerate(reversed(digits[:-1]))
                )
                % 10
            ) % 10
            if digits[-1] != check:
                raise ValueError("Código de barras inválido")
        return value
