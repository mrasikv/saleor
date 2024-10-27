from unittest.mock import patch

from django.test import override_settings

from .....account.models import User
from .....checkout.actions import call_checkout_event
from .....core.models import EventDelivery
from .....webhook.event_types import WebhookEventAsyncType, WebhookEventSyncType
from ....core.utils import to_global_id_or_none
from ....tests.utils import assert_no_permission, get_graphql_content

MUTATION_CHECKOUT_CUSTOMER_DETACH = """
    mutation checkoutCustomerDetach($id: ID) {
        checkoutCustomerDetach(id: $id) {
            checkout {
                token
            }
            errors {
                field
                message
            }
        }
    }
    """


def test_checkout_customer_detach(user_api_client, checkout_with_item, customer_user):
    checkout = checkout_with_item
    checkout.user = customer_user
    checkout.save(update_fields=["user"])
    previous_last_change = checkout.last_change

    variables = {"id": to_global_id_or_none(checkout)}

    # Mutation should succeed if the user owns this checkout.
    response = user_api_client.post_graphql(
        MUTATION_CHECKOUT_CUSTOMER_DETACH, variables
    )
    content = get_graphql_content(response)
    data = content["data"]["checkoutCustomerDetach"]
    assert not data["errors"]
    checkout.refresh_from_db()
    assert checkout.user is None
    assert checkout.last_change != previous_last_change

    # Mutation should fail when user calling it doesn't own the checkout.
    other_user = User.objects.create_user("othercustomer@example.com", "password")
    checkout.user = other_user
    checkout.save()
    response = user_api_client.post_graphql(
        MUTATION_CHECKOUT_CUSTOMER_DETACH, variables
    )
    assert_no_permission(response)


def test_checkout_customer_detach_by_app(
    app_api_client, checkout_with_item, customer_user, permission_impersonate_user
):
    checkout = checkout_with_item
    checkout.user = customer_user
    checkout.save(update_fields=["user"])
    previous_last_change = checkout.last_change

    variables = {"id": to_global_id_or_none(checkout)}

    # Mutation should succeed if the user owns this checkout.
    response = app_api_client.post_graphql(
        MUTATION_CHECKOUT_CUSTOMER_DETACH,
        variables,
        permissions=[permission_impersonate_user],
    )
    content = get_graphql_content(response)
    data = content["data"]["checkoutCustomerDetach"]
    assert not data["errors"]
    checkout.refresh_from_db()
    assert checkout.user is None
    assert checkout.last_change != previous_last_change


def test_checkout_customer_detach_by_app_without_permissions(
    app_api_client, checkout_with_item, customer_user
):
    checkout = checkout_with_item
    checkout.user = customer_user
    checkout.save(update_fields=["user"])
    previous_last_change = checkout.last_change

    variables = {"id": to_global_id_or_none(checkout)}

    # Mutation should succeed if the user owns this checkout.
    response = app_api_client.post_graphql(MUTATION_CHECKOUT_CUSTOMER_DETACH, variables)

    assert_no_permission(response)
    checkout.refresh_from_db()
    assert checkout.last_change == previous_last_change


def test_with_active_problems_flow(user_api_client, checkout_with_problems):
    # given
    checkout_with_problems.user = user_api_client.user
    checkout_with_problems.save(update_fields=["user"])
    channel = checkout_with_problems.channel
    channel.use_legacy_error_flow_for_checkout = False
    channel.save(update_fields=["use_legacy_error_flow_for_checkout"])

    variables = {"id": to_global_id_or_none(checkout_with_problems)}

    response = user_api_client.post_graphql(
        MUTATION_CHECKOUT_CUSTOMER_DETACH, variables
    )
    content = get_graphql_content(response)

    # then
    assert not content["data"]["checkoutCustomerDetach"]["errors"]


@patch(
    "saleor.graphql.checkout.mutations.checkout_customer_detach.call_checkout_event",
    wraps=call_checkout_event,
)
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_checkout_customer_detach_triggers_webhooks(
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    wrapped_call_checkout_event,
    setup_checkout_webhooks,
    settings,
    user_api_client,
    checkout_with_item,
    customer_user,
):
    # given
    mocked_send_webhook_request_sync.return_value = []
    (
        tax_webhook,
        shipping_webhook,
        shipping_filter_webhook,
        checkout_updated_webhook,
    ) = setup_checkout_webhooks(WebhookEventAsyncType.CHECKOUT_UPDATED)

    checkout = checkout_with_item
    checkout.user = customer_user
    checkout.save(update_fields=["user"])

    variables = {"id": to_global_id_or_none(checkout)}

    # when
    response = user_api_client.post_graphql(
        MUTATION_CHECKOUT_CUSTOMER_DETACH, variables
    )

    # then
    content = get_graphql_content(response)
    assert not content["data"]["checkoutCustomerDetach"]["errors"]

    assert wrapped_call_checkout_event.called

    # confirm that event delivery was generated for each async webhook.
    checkout_update_delivery = EventDelivery.objects.get(
        webhook_id=checkout_updated_webhook.id
    )
    mocked_send_webhook_request_async.assert_called_once_with(
        kwargs={"event_delivery_id": checkout_update_delivery.id},
        queue=settings.CHECKOUT_WEBHOOK_EVENTS_CELERY_QUEUE_NAME,
        bind=True,
        retry_backoff=10,
        retry_kwargs={"max_retries": 5},
    )

    # confirm each sync webhook was called without saving event delivery
    assert mocked_send_webhook_request_sync.call_count == 3
    assert not EventDelivery.objects.exclude(
        webhook_id=checkout_updated_webhook.id
    ).exists()

    shipping_methods_call, filter_shipping_call, tax_delivery_call = (
        mocked_send_webhook_request_sync.mock_calls
    )
    shipping_methods_delivery = shipping_methods_call.args[0]
    assert shipping_methods_delivery.webhook_id == shipping_webhook.id
    assert (
        shipping_methods_delivery.event_type
        == WebhookEventSyncType.SHIPPING_LIST_METHODS_FOR_CHECKOUT
    )
    assert shipping_methods_call.kwargs["timeout"] == settings.WEBHOOK_SYNC_TIMEOUT

    filter_shipping_delivery = filter_shipping_call.args[0]
    assert filter_shipping_delivery.webhook_id == shipping_filter_webhook.id
    assert (
        filter_shipping_delivery.event_type
        == WebhookEventSyncType.CHECKOUT_FILTER_SHIPPING_METHODS
    )
    assert filter_shipping_call.kwargs["timeout"] == settings.WEBHOOK_SYNC_TIMEOUT

    tax_delivery = tax_delivery_call.args[0]
    assert tax_delivery.webhook_id == tax_webhook.id