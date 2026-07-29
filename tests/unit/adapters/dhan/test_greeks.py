from __future__ import annotations

import pytest

mibian = pytest.importorskip("mibian")

from scalpr.adapters.dhan._greeks import GreeksCalculationError, GreeksCalculator

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def calculator() -> GreeksCalculator:
    return GreeksCalculator()


@pytest.fixture
def atm_params() -> dict:
    return {
        "underlying_price": 100.0,
        "strike": 100.0,
        "days_to_expiry": 30,
        "option_type": "CE",
        "interest_rate": 0.1,
        "volatility": 0.15,
    }


# ============================================================================
# calculate_greeks — structure & key presence
# ============================================================================


class TestCalculateGreeksStructure:
    def test_returns_dict(self, calculator: GreeksCalculator, atm_params: dict) -> None:
        result = calculator.calculate_greeks(**atm_params)
        assert isinstance(result, dict)

    def test_contains_all_required_keys(
        self, calculator: GreeksCalculator, atm_params: dict
    ) -> None:
        result = calculator.calculate_greeks(**atm_params)
        expected_keys = {"delta", "gamma", "theta", "vega", "rho", "iv", "call_price", "put_price"}
        assert expected_keys.issubset(result.keys())

    def test_values_are_floats(
        self, calculator: GreeksCalculator, atm_params: dict
    ) -> None:
        result = calculator.calculate_greeks(**atm_params)
        for key in ("delta", "gamma", "theta", "vega", "rho", "iv", "call_price", "put_price"):
            assert isinstance(result[key], float), f"{key} is not float"


# ============================================================================
# calculate_greeks — sign and magnitude
# ============================================================================


class TestCalculateGreeksSign:
    def test_atm_call_delta_positive(
        self, calculator: GreeksCalculator
    ) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "CE", 0.1, 0.15)
        assert result["delta"] > 0

    def test_atm_put_delta_negative(
        self, calculator: GreeksCalculator
    ) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "PE", 0.1, 0.15)
        assert result["delta"] < 0

    def test_atm_call_delta_approx_half(
        self, calculator: GreeksCalculator
    ) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "CE", 0.1, 0.15)
        assert 0.4 < result["delta"] < 0.8

    def test_atm_put_delta_approx_neg_half(
        self, calculator: GreeksCalculator
    ) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "PE", 0.1, 0.15)
        assert -0.8 < result["delta"] < -0.4

    def test_itm_call_delta_gt_half(
        self, calculator: GreeksCalculator
    ) -> None:
        result = calculator.calculate_greeks(100, 80, 30, "CE", 0.1, 0.15)
        assert result["delta"] > 0.5

    def test_itm_put_delta_lt_neg_half(
        self, calculator: GreeksCalculator
    ) -> None:
        result = calculator.calculate_greeks(100, 120, 30, "PE", 0.1, 0.15)
        assert result["delta"] < -0.5

    def test_gamma_positive(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "CE", 0.1, 0.15)
        assert result["gamma"] > 0

    def test_theta_negative(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "CE", 0.1, 0.15)
        assert result["theta"] < 0

    def test_vega_positive(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "CE", 0.1, 0.15)
        assert result["vega"] > 0


# ============================================================================
# calculate_greeks — implied volatility
# ============================================================================


class TestCalculateGreeksIV:
    def test_iv_in_result(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "CE", 0.1, 0.15)
        assert result["iv"] == 15.0

    def test_iv_default_when_none(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "CE", 0.1, volatility=None)
        assert result["iv"] == 15.0

    def test_iv_custom_volatility(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "CE", 0.1, 0.5)
        assert result["iv"] == 50.0


# ============================================================================
# calculate_greeks — edge cases
# ============================================================================


class TestCalculateGreeksEdgeCases:
    def test_zero_days_to_expiry(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 100, 0, "CE", 0.1, 0.15)
        assert isinstance(result["delta"], float)

    def test_one_day_to_expiry(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 100, 1, "CE", 0.1, 0.15)
        assert isinstance(result["delta"], float)

    def test_zero_volatility(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "CE", 0.1, 0.0)
        assert isinstance(result["delta"], float)

    def test_deep_itm_call_delta_near_one(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 50, 30, "CE", 0.1, 0.15)
        assert result["delta"] >= 0.99

    def test_deep_itm_put_delta_near_neg_one(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 150, 30, "PE", 0.1, 0.15)
        assert result["delta"] <= -0.99

    def test_deep_otm_call_delta_near_zero(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 150, 30, "CE", 0.1, 0.15)
        assert abs(result["delta"]) < 0.01

    def test_deep_otm_put_delta_near_zero(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 50, 30, "PE", 0.1, 0.15)
        assert abs(result["delta"]) < 0.01

    def test_negative_days_to_expiry(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 100, -5, "CE", 0.1, 0.15)
        assert isinstance(result["delta"], float)


# ============================================================================
# calculate_greeks — option type aliases
# ============================================================================


class TestCalculateGreeksOptionType:
    def test_ce_alias(self, calculator: GreeksCalculator) -> None:
        assert (
            calculator.calculate_greeks(100, 100, 30, "CE", 0.1, 0.15)["delta"]
            == calculator.calculate_greeks(100, 100, 30, "CALL", 0.1, 0.15)["delta"]
        )

    def test_c_alias(self, calculator: GreeksCalculator) -> None:
        assert (
            calculator.calculate_greeks(100, 100, 30, "CE", 0.1, 0.15)["delta"]
            == calculator.calculate_greeks(100, 100, 30, "C", 0.1, 0.15)["delta"]
        )

    def test_pe_alias(self, calculator: GreeksCalculator) -> None:
        assert (
            calculator.calculate_greeks(100, 100, 30, "PE", 0.1, 0.15)["delta"]
            == calculator.calculate_greeks(100, 100, 30, "PUT", 0.1, 0.15)["delta"]
        )

    def test_p_alias(self, calculator: GreeksCalculator) -> None:
        assert (
            calculator.calculate_greeks(100, 100, 30, "PE", 0.1, 0.15)["delta"]
            == calculator.calculate_greeks(100, 100, 30, "P", 0.1, 0.15)["delta"]
        )

    def test_case_insensitive(self, calculator: GreeksCalculator) -> None:
        assert (
            calculator.calculate_greeks(100, 100, 30, "ce", 0.1, 0.15)["delta"]
            == calculator.calculate_greeks(100, 100, 30, "Ce", 0.1, 0.15)["delta"]
        )


# ============================================================================
# calculate_greeks — interest rate & rho
# ============================================================================


class TestCalculateGreeksInterestRate:
    def test_call_rho_positive(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "CE", 0.1, 0.15)
        assert result["rho"] > 0

    def test_put_rho_negative(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "PE", 0.1, 0.15)
        assert result["rho"] < 0

    def test_higher_rate_increases_call_price(
        self, calculator: GreeksCalculator
    ) -> None:
        low = calculator.calculate_greeks(100, 100, 30, "CE", 0.05, 0.15)
        high = calculator.calculate_greeks(100, 100, 30, "CE", 0.15, 0.15)
        assert high["call_price"] > low["call_price"]


# ============================================================================
# implied_volatility
# ============================================================================


class TestImpliedVolatility:
    def test_returns_float(self, calculator: GreeksCalculator) -> None:
        iv = calculator.implied_volatility(100, 110, 30, "CE", 2.5)
        assert isinstance(iv, float)

    def test_call_option(self, calculator: GreeksCalculator) -> None:
        iv = calculator.implied_volatility(100, 110, 30, "CE", 2.5)
        assert iv > 0

    def test_put_option(self, calculator: GreeksCalculator) -> None:
        iv = calculator.implied_volatility(100, 90, 30, "PE", 2.5)
        assert iv > 0

    def test_higher_market_price_higher_iv(
        self, calculator: GreeksCalculator
    ) -> None:
        iv_low = calculator.implied_volatility(100, 110, 30, "CE", 2.5)
        iv_high = calculator.implied_volatility(100, 110, 30, "CE", 5.0)
        assert iv_high > iv_low

    def test_zero_days_edge(self, calculator: GreeksCalculator) -> None:
        iv = calculator.implied_volatility(100, 110, 0, "CE", 2.5)
        assert isinstance(iv, float)

    def test_deep_itm_call(self, calculator: GreeksCalculator) -> None:
        iv = calculator.implied_volatility(100, 50, 30, "CE", 50.0)
        assert iv > 0

    def test_custom_interest_rate(self, calculator: GreeksCalculator) -> None:
        iv = calculator.implied_volatility(100, 110, 30, "CE", 2.5, interest_rate=0.05)
        assert iv > 0


# ============================================================================
# GreeksCalculationError
# ============================================================================


class TestGreeksCalculationError:
    def test_is_exception(self) -> None:
        assert issubclass(GreeksCalculationError, Exception)

    def test_raised_on_invalid_option_type(
        self, calculator: GreeksCalculator
    ) -> None:
        bs = mibian.BS([100, 100, 0.1, 1], callPrice=0.0)
        assert bs.impliedVolatility is None


# ============================================================================
# calculate_greeks — call/put price consistency
# ============================================================================


class TestPriceConsistency:
    def test_call_price_positive(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "CE", 0.1, 0.15)
        assert result["call_price"] >= 0

    def test_put_price_positive(self, calculator: GreeksCalculator) -> None:
        result = calculator.calculate_greeks(100, 100, 30, "PE", 0.1, 0.15)
        assert result["put_price"] >= 0

    def test_put_call_parity_atm(
        self, calculator: GreeksCalculator
    ) -> None:
        r = calculator.calculate_greeks(100, 100, 30, "CE", 0.1, 0.15)
        call = r["call_price"]
        put = r["put_price"]
        assert abs((call - put) - (100 - 100)) < 5
