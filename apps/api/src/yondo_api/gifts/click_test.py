"""CLICK Shop API-shaped OFFLINE emulator.

This emulates Prepare (action=0) and Complete (action=1) using a local test key.
CLICK itself is never contacted; no card, real invoice, or monetary transfer occurs.
The legacy MD5 signature follows the CLICK Shop API wire format ONLY in test mode.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qsl
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import Admin, Session
from yondo_api.gifts.orders_models import GiftTestOrder, GiftTestStatus
from yondo_api.gifts.test_orders import (
    ensure_test_enabled,
    locked_order,
    order_payload,
    restore_test_stock,
)
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType
from yondo_api.notifications.gifts import enqueue_gift_notice

router = APIRouter(prefix='/gifts/click-test', tags=['CLICK offline test'])
_MAX_BODY = 4096
_MAX_CLICK_TRANS = 9_223_372_036_854_775_807


class TestCallbackError(Exception):
    def __init__(self, code: int, reason: str):
        super().__init__(reason)
        self.code = code
        self.reason = reason


def _click_response(
    fields: dict[str, str],
    action: int,
    error: int = 0,
    reason: str = 'Success',
    prepared_id: int | None = None,
) -> JSONResponse:
    trans_id = fields.get('click_trans_id', '')
    try:
        trans_id = int(trans_id)
    except (TypeError, ValueError):
        pass
    data = {
        'click_trans_id': trans_id,
        'merchant_trans_id': fields.get('merchant_trans_id', ''),
        'error': error,
        'error_note': reason,
    }
    if error == 0:
        data['merchant_prepare_id' if action == 0 else 'merchant_confirm_id'] = prepared_id
    return JSONResponse(content=data)


def _read_callback(body: bytes, content_type: str) -> dict[str, str]:
    if len(body) > _MAX_BODY:
        raise TestCallbackError(-8, 'Test callback too large')
    if content_type.split(';', 1)[0].strip().lower() != 'application/x-www-form-urlencoded':
        raise TestCallbackError(-8, 'Form-encoded callback required')
    try:
        pairs = parse_qsl(body.decode('utf-8'), keep_blank_values=True, max_num_fields=20)
    except (ValueError, UnicodeDecodeError) as exc:
        raise TestCallbackError(-8, 'Invalid form body') from exc
    params = dict(pairs)
    if len(pairs) != len(params):
        raise TestCallbackError(-8, 'Duplicate parameters are not allowed')
    return params


def _verified(fields: dict[str, str], action: int, secret: str, service_id: int) -> int:
    required = [
        'click_trans_id', 'service_id', 'merchant_trans_id',
        'amount', 'action', 'error', 'sign_time', 'sign_string',
    ]
    if action == 1:
        required.append('merchant_prepare_id')
    if any(not fields.get(k) for k in required):
        raise TestCallbackError(-8, 'Missing callback fields')
    try:
        trans_id = int(fields['click_trans_id'])
        submitted_service = int(fields['service_id'])
        submitted_action = int(fields['action'])
        int(fields['error'])
    except (TypeError, ValueError) as exc:
        raise TestCallbackError(-8, 'Invalid callback numeric field') from exc
    if trans_id <= 0 or trans_id > _MAX_CLICK_TRANS or submitted_action != action:
        raise TestCallbackError(-3, 'Invalid CLICK test action')
    if submitted_service != service_id:
        raise TestCallbackError(-8, 'Wrong CLICK test service ID')
    try:
        signed_at = datetime.strptime(fields['sign_time'], '%Y-%m-%d %H:%M:%S').replace(
            tzinfo=UTC
        )
    except ValueError as exc:
        raise TestCallbackError(-8, 'Invalid signature timestamp') from exc
    if abs((datetime.now(UTC) - signed_at).total_seconds()) > 600:
        raise TestCallbackError(-1, 'Expired test signature')
    parts = [
        fields['click_trans_id'],
        fields['service_id'],
        secret,
        fields['merchant_trans_id'],
    ]
    if action == 1:
        parts.append(fields['merchant_prepare_id'])
    parts += [fields['amount'], fields['action'], fields['sign_time']]
    expected = hashlib.md5(''.join(parts).encode('utf-8')).hexdigest()  # noqa: S324
    if not hmac.compare_digest(expected, fields['sign_string'].lower()):
        raise TestCallbackError(-1, 'Invalid CLICK test signature')
    return trans_id


def _check_amount(amount: str, total_minor: int) -> None:
    try:
        value = Decimal(amount)
    except InvalidOperation as exc:
        raise TestCallbackError(-2, 'Invalid amount') from exc
    if not value.is_finite() or value <= 0 or value * 100 != total_minor:
        raise TestCallbackError(-2, 'Amount mismatch')


async def _order_for_callback(session: Session, raw_order_id: str) -> GiftTestOrder:
    try:
        order_id = UUID(raw_order_id)
    except (ValueError, TypeError) as exc:
        raise TestCallbackError(-5, 'Unknown order') from exc
    order = await session.scalar(
        select(GiftTestOrder).where(GiftTestOrder.id == order_id).with_for_update()
        .execution_options(populate_existing=True)
    )
    if order is None:
        raise TestCallbackError(-5, 'Unknown order')
    if order.currency != 'UZS':
        raise TestCallbackError(-2, 'Test currency must be UZS')
    return order


async def _check_customer(session: Session, customer_id: UUID) -> None:
    user = await session.get(User, customer_id)
    role = await session.get(UserRole, (customer_id, UserRoleType.CUSTOMER))
    if user is None or user.account_status != AccountStatus.ACTIVE or role is None:
        raise TestCallbackError(-5, 'Customer unavailable')


async def _prepare(fields: dict[str, str], session: Session, trans_id: int) -> int:
    order = await _order_for_callback(session, fields['merchant_trans_id'])
    _check_amount(fields['amount'], order.subtotal_minor)
    await _check_customer(session, order.customer_id)
    if int(fields['error']) != 0:
        raise TestCallbackError(-8, 'Prepare reports an error')
    if order.status != GiftTestStatus.AWAITING_TEST_PAYMENT:
        raise TestCallbackError(-4, 'Test order is not payable')
    if order.click_trans_id is not None:
        if order.click_trans_id != trans_id:
            raise TestCallbackError(-8, 'Conflicting transaction for order')
        return trans_id
    order.click_trans_id = trans_id
    order.prepared_at = datetime.now(UTC)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise TestCallbackError(-8, 'Duplicate CLICK test transaction') from exc
    return trans_id


async def _complete(fields: dict[str, str], session: Session, trans_id: int) -> int:
    order = await _order_for_callback(session, fields['merchant_trans_id'])
    _check_amount(fields['amount'], order.subtotal_minor)
    try:
        prepare_id = int(fields['merchant_prepare_id'])
    except ValueError as exc:
        raise TestCallbackError(-6, 'Invalid prepare ID') from exc
    if order.click_trans_id != trans_id or prepare_id != trans_id:
        raise TestCallbackError(-6, 'Unrecognized prepare transaction')
    if order.status == GiftTestStatus.TEST_PAID and int(fields['error']) == 0:
        return trans_id  # Idempotent CLICK test Complete.
    if order.status != GiftTestStatus.AWAITING_TEST_PAYMENT:
        raise TestCallbackError(-9, 'Order no longer awaiting test payment')
    if int(fields['error']) != 0:
        await restore_test_stock(session, order)
        order.status = GiftTestStatus.CANCELLED
        await enqueue_gift_notice(session, order, 'gift_cancelled')
        await session.commit()
        raise TestCallbackError(-9, 'Test payment cancelled')
    await _check_customer(session, order.customer_id)
    order.status = GiftTestStatus.TEST_PAID
    order.test_paid_at = datetime.now(UTC)
    await enqueue_gift_notice(session, order, 'gift_test_paid')
    await session.commit()
    return trans_id


async def _incoming(action: int, request: Request, session: Session) -> JSONResponse:
    ensure_test_enabled(request.app.state.settings)
    fields: dict[str, str] = {}
    try:
        fields = _read_callback(await request.body(), request.headers.get('content-type', ''))
        config = request.app.state.settings
        trans_id = _verified(
            fields, action, config.click_test_secret.get_secret_value(),
            config.click_test_service_id,
        )
        if action == 0:
            response_id = await _prepare(fields, session, trans_id)
        else:
            response_id = await _complete(fields, session, trans_id)
    except TestCallbackError as exc:
        return _click_response(fields, action, exc.code, exc.reason)
    return _click_response(fields, action, prepared_id=response_id)


@router.post('/prepare')
async def click_test_prepare(request: Request, session: Session):
    return await _incoming(0, request, session)


@router.post('/complete')
async def click_test_complete(request: Request, session: Session):
    return await _incoming(1, request, session)


class SimulateWrite(BaseModel):
    result: str


@router.post('/admin/orders/{order_id}/simulate')
async def admin_simulate_click(
    order_id: UUID, payload: SimulateWrite,
    request: Request, admin: Admin, session: Session,
):
    """Operator-only convenience test: never makes network requests or real payments."""
    ensure_test_enabled(request.app.state.settings)
    if payload.result not in {'success', 'cancel'}:
        raise ApplicationError('click_test_result_invalid', 'Use success or cancel', 422)
    order = await locked_order(session, order_id)
    if order.status != GiftTestStatus.AWAITING_TEST_PAYMENT:
        raise ApplicationError('gift_test_transition_invalid', 'Order is no longer payable', 409)
    if order.click_trans_id is None:
        order.click_trans_id = secrets.randbelow(_MAX_CLICK_TRANS - 1) + 1
        order.prepared_at = datetime.now(UTC)
    if payload.result == 'cancel':
        await restore_test_stock(session, order)
        order.status = GiftTestStatus.CANCELLED
    else:
        order.status = GiftTestStatus.TEST_PAID
        order.test_paid_at = datetime.now(UTC)
    order.status_changed_by = admin.id
    await enqueue_gift_notice(
        session,
        order,
        'gift_cancelled' if payload.result == 'cancel' else 'gift_test_paid',
        actor_id=admin.id,
    )
    await session.commit()
    await session.refresh(order)
    return await order_payload(session, order)
