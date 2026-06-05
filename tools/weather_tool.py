"""Weather forecast tool using the free Open-Meteo APIs."""

import logging
from datetime import date, datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from models import (
    ApiLocation,
    WeatherDailyForecast,
    WeatherForecastResponse,
    WeatherHourlyForecast,
)

logger = logging.getLogger(__name__)


class WeatherTool:
    """Tool for location-based weather forecasts."""

    geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
    forecast_url = "https://api.open-meteo.com/v1/forecast"

    def __init__(
        self,
        timeout: int = 20,
        max_forecast_days: int = 16,
        user_agent: str = "mcp-web-server/0.1",
    ):
        self.timeout = timeout
        self.max_forecast_days = max(1, max_forecast_days)
        self.headers = {"User-Agent": user_agent}

    async def forecast(
        self,
        location: str,
        forecast_date: Optional[str] = None,
    ) -> WeatherForecastResponse:
        """Return weather forecast for a resolved location and local date."""
        location = location.strip()
        if not location:
            return self._error(location, forecast_date, "location must not be empty")

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
            ) as client:
                resolved = await self._resolve_location(client, location)
                if resolved is None:
                    return self._error(location, forecast_date, "location not found")

                selected_date = self._select_date(forecast_date, resolved.timezone)
                if selected_date is None:
                    return self._error(
                        location,
                        forecast_date,
                        "date must be ISO format YYYY-MM-DD",
                        resolved,
                    )

                today = self._today_for_timezone(resolved.timezone)
                days_ahead = (selected_date - today).days
                if days_ahead < 0:
                    return self._error(
                        location,
                        selected_date.isoformat(),
                        "Open-Meteo forecast does not cover past dates",
                        resolved,
                    )
                if days_ahead >= self.max_forecast_days:
                    return self._error(
                        location,
                        selected_date.isoformat(),
                        f"date is outside the {self.max_forecast_days}-day forecast window",
                        resolved,
                    )

                payload = await self._fetch_forecast(client, resolved, days_ahead + 1)
        except httpx.HTTPStatusError as exc:
            return self._error(
                location,
                forecast_date,
                f"Open-Meteo request failed with HTTP {exc.response.status_code}",
            )
        except httpx.HTTPError as exc:
            return self._error(
                location,
                forecast_date,
                f"Open-Meteo request failed: {exc.__class__.__name__}",
            )

        daily = self._daily_for_date(payload.get("daily", {}), selected_date)
        hourly = self._hourly_for_date(payload.get("hourly", {}), selected_date)

        return WeatherForecastResponse(
            query=location,
            date=selected_date.isoformat(),
            location=resolved,
            daily=daily,
            hourly=hourly,
            source_url=self._source_url(resolved),
        )

    async def _resolve_location(
        self,
        client: httpx.AsyncClient,
        location: str,
    ) -> Optional[ApiLocation]:
        params = {
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json",
        }
        response = await client.get(self.geocoding_url, params=params)
        response.raise_for_status()

        results = response.json().get("results") or []
        if not results:
            return None

        item = results[0]
        return ApiLocation(
            name=item.get("name") or location,
            country=item.get("country"),
            admin1=item.get("admin1"),
            latitude=float(item["latitude"]),
            longitude=float(item["longitude"]),
            timezone=item.get("timezone"),
        )

    async def _fetch_forecast(
        self,
        client: httpx.AsyncClient,
        location: ApiLocation,
        forecast_days: int,
    ) -> dict[str, Any]:
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "daily": ",".join(
                [
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "precipitation_probability_max",
                    "wind_speed_10m_max",
                ]
            ),
            "hourly": ",".join(
                [
                    "temperature_2m",
                    "precipitation",
                    "precipitation_probability",
                    "weather_code",
                    "wind_speed_10m",
                ]
            ),
            "forecast_days": forecast_days,
            "timezone": "auto",
        }
        response = await client.get(self.forecast_url, params=params)
        response.raise_for_status()
        return response.json()

    def _select_date(
        self,
        forecast_date: Optional[str],
        timezone: Optional[str],
    ) -> Optional[date]:
        if forecast_date:
            try:
                return date.fromisoformat(forecast_date)
            except ValueError:
                return None
        return self._today_for_timezone(timezone)

    def _today_for_timezone(self, timezone: Optional[str]) -> date:
        if timezone:
            try:
                return datetime.now(ZoneInfo(timezone)).date()
            except ZoneInfoNotFoundError:
                logger.warning("Unknown timezone from Open-Meteo: %s", timezone)
        return datetime.utcnow().date()

    def _daily_for_date(
        self,
        daily: dict[str, list[Any]],
        selected_date: date,
    ) -> Optional[WeatherDailyForecast]:
        dates = daily.get("time") or []
        date_text = selected_date.isoformat()
        if date_text not in dates:
            return None

        idx = dates.index(date_text)
        code = self._value_at(daily.get("weather_code"), idx)
        return WeatherDailyForecast(
            date=date_text,
            weather_code=code,
            weather_description=self._weather_description(code),
            temperature_min_c=self._value_at(daily.get("temperature_2m_min"), idx),
            temperature_max_c=self._value_at(daily.get("temperature_2m_max"), idx),
            precipitation_sum_mm=self._value_at(daily.get("precipitation_sum"), idx),
            precipitation_probability_max_percent=self._value_at(
                daily.get("precipitation_probability_max"),
                idx,
            ),
            wind_speed_max_kmh=self._value_at(daily.get("wind_speed_10m_max"), idx),
        )

    def _hourly_for_date(
        self,
        hourly: dict[str, list[Any]],
        selected_date: date,
    ) -> list[WeatherHourlyForecast]:
        times = hourly.get("time") or []
        date_prefix = selected_date.isoformat()
        forecasts = []

        for idx, timestamp in enumerate(times):
            if not isinstance(timestamp, str) or not timestamp.startswith(date_prefix):
                continue
            code = self._value_at(hourly.get("weather_code"), idx)
            forecasts.append(
                WeatherHourlyForecast(
                    time=timestamp,
                    weather_code=code,
                    weather_description=self._weather_description(code),
                    temperature_c=self._value_at(hourly.get("temperature_2m"), idx),
                    precipitation_mm=self._value_at(hourly.get("precipitation"), idx),
                    precipitation_probability_percent=self._value_at(
                        hourly.get("precipitation_probability"),
                        idx,
                    ),
                    wind_speed_kmh=self._value_at(hourly.get("wind_speed_10m"), idx),
                )
            )

        return forecasts

    def _source_url(self, location: ApiLocation) -> str:
        return (
            "https://open-meteo.com/en/docs"
            f"?latitude={location.latitude}&longitude={location.longitude}"
        )

    def _error(
        self,
        location: str,
        forecast_date: Optional[str],
        error: str,
        resolved: Optional[ApiLocation] = None,
    ) -> WeatherForecastResponse:
        return WeatherForecastResponse(
            query=location,
            date=forecast_date or "",
            location=resolved,
            success=False,
            error=error,
        )

    def _value_at(self, values: Optional[list[Any]], idx: int) -> Any:
        if values is None or idx >= len(values):
            return None
        return values[idx]

    def _weather_description(self, code: Optional[int]) -> Optional[str]:
        if code is None:
            return None
        descriptions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            56: "Light freezing drizzle",
            57: "Dense freezing drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Light freezing rain",
            67: "Heavy freezing rain",
            71: "Slight snow fall",
            73: "Moderate snow fall",
            75: "Heavy snow fall",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
        }
        return descriptions.get(code, f"Unknown weather code {code}")
