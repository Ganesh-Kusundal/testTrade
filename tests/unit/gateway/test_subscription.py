from scalpr.domain.instrument import MarketFeed
from scalpr.gateway.subscription import Subscription


def test_subscription_creation():
    sub = Subscription(id="sub-1", instruments=["TCS:NSE"], mode=MarketFeed.QUOTE)
    assert sub.id == "sub-1"
    assert sub.mode == MarketFeed.QUOTE
    assert sub.is_active is True


def test_subscription_deactivate():
    sub = Subscription(id="sub-1", instruments=["TCS:NSE"], mode=MarketFeed.QUOTE)
    sub.deactivate()
    assert sub.is_active is False
