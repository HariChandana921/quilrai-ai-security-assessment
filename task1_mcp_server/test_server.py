
import pytest
from pydantic import ValidationError
from task1_mcp_server.server import trigger_refund

from task1_mcp_server.server import (
    CustomerRequest,
    get_customer_record,
)


def test_valid_customer():
    result = get_customer_record("CUST-12345")

    assert result["success"] is True
    assert result["customer"]["name"] == "Alice Johnson"


def test_customer_not_found():
    result = get_customer_record("CUST-99999")

    assert result["success"] is False
    assert result["message"] == "Customer not found"


def test_invalid_customer_id():
    with pytest.raises(ValidationError):
        get_customer_record("INVALID-ID")



def test_valid_refund():
    result = trigger_refund(
        customer_id="CUST-12345",
        amount=50.00,
        reason="Product arrived damaged",
    )

    assert result["success"] is True
    assert result["amount"] == 50.00
    assert result["message"] == "Mock refund approved"


def test_refund_customer_not_found():
    result = trigger_refund(
        customer_id="CUST-99999",
        amount=25.00,
        reason="Incorrect product delivered",
    )

    assert result["success"] is False
    assert result["message"] == "Customer not found"


def test_refund_negative_amount():
    with pytest.raises(ValidationError):
        trigger_refund(
            customer_id="CUST-12345",
            amount=-50.00,
            reason="Product arrived damaged",
        )


def test_refund_exceeds_limit():
    with pytest.raises(ValidationError):
        trigger_refund(
            customer_id="CUST-12345",
            amount=1500.00,
            reason="Product arrived damaged",
        )


def test_refund_invalid_customer_id():
    with pytest.raises(ValidationError):
        trigger_refund(
            customer_id="INVALID",
            amount=50.00,
            reason="Product arrived damaged",
        )



def test_refund_short_reason():
    with pytest.raises(ValidationError):
        trigger_refund(
            customer_id="CUST-12345",
            amount=50.00,
            reason="Damaged",
        )
