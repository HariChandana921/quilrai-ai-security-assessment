
import logging
import sys

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, StrictStr

# Send debugging messages to stderr, never stdout.
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
)

# Create our MCP server.
mcp = FastMCP("QuilrAI Customer Server")


# Define strict customer ID validation.
class CustomerRequest(BaseModel):
    customer_id: StrictStr = Field(
        pattern=r"^CUST-[0-9]{5}$"
    )


# Mock customer records.
CUSTOMERS = {
    "CUST-12345": {
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "status": "active",
    },
    "CUST-67890": {
        "name": "Bob Smith",
        "email": "bob@example.com",
        "status": "active",
    },
}


@mcp.tool()
def get_customer_record(customer_id: str) -> dict:
    """Retrieve customer information by customer ID."""

    request = CustomerRequest(
        customer_id=customer_id
    )

    customer = CUSTOMERS.get(request.customer_id)

    if customer is None:
        return {
            "success": False,
            "message": "Customer not found",
        }

    return {
        "success": True,
        "customer_id": request.customer_id,
        "customer": customer,
    }

from decimal import Decimal
from pydantic import field_validator


class RefundRequest(BaseModel):
    customer_id: StrictStr = Field(
        pattern=r"^CUST-[0-9]{5}$"
    )
    amount: Decimal = Field(gt=0, le=1000)
    reason: StrictStr = Field(min_length=10, max_length=200)

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, value):
        if isinstance(value, bool) or not isinstance(
            value, (int, float, str, Decimal)
        ):
            raise ValueError("Invalid amount type")
        return value


@mcp.tool()
def trigger_refund(
    customer_id: str,
    amount: float,
    reason: str,
) -> dict:
    """Simulate a refund for an existing customer."""

    request = RefundRequest(
        customer_id=customer_id,
        amount=amount,
        reason=reason,
    )

    if request.customer_id not in CUSTOMERS:
        return {
            "success": False,
            "message": "Customer not found",
        }

    return {
        "success": True,
        "message": "Mock refund approved",
        "customer_id": request.customer_id,
        "amount": float(request.amount),
        "reason": request.reason,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
