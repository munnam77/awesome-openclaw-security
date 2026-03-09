/**
 * OpenClaw Skill: Weather Forecast
 *
 * Fetches weather data from an external API.
 * NOTE: This skill has some suspicious patterns that need manual review,
 * but it is NOT malicious -- it legitimately needs network access for its purpose.
 *
 * Scanner should flag this as WARN (not FAIL).
 */

const https = require("https");

const SKILL_NAME = "weather-forecast";
const SKILL_VERSION = "2.1.0";
const API_BASE = "https://api.openweathermap.org/data/2.5";

/**
 * Fetch weather data from OpenWeatherMap API.
 * SCANNER NOTE: This triggers WARN-001 (outbound HTTP request).
 * Legitimate use: the skill needs to call a weather API.
 */
function fetchWeather(city, apiKey) {
  return new Promise((resolve, reject) => {
    const url = `${API_BASE}/weather?q=${encodeURIComponent(city)}&appid=${apiKey}&units=metric`;

    https.get(url, (res) => {
      let data = "";
      res.on("data", (chunk) => { data += chunk; });
      res.on("end", () => {
        try {
          resolve(JSON.parse(data));
        } catch (err) {
          reject(new Error("Failed to parse weather API response"));
        }
      });
    }).on("error", reject);
  });
}

/**
 * Cache weather data locally to reduce API calls.
 * Uses a simple in-memory cache with TTL.
 */
const cache = new Map();
const CACHE_TTL = 600000; // 10 minutes

function getCached(key) {
  const entry = cache.get(key);
  if (entry && Date.now() - entry.timestamp < CACHE_TTL) {
    return entry.data;
  }
  cache.delete(key);
  return null;
}

function setCache(key, data) {
  cache.set(key, { data, timestamp: Date.now() });
}

/**
 * Format temperature for display.
 * SCANNER NOTE: This triggers WARN-005 pattern due to the template literal
 * complexity, but it's just string formatting.
 */
function formatResponse(weatherData) {
  const temp = weatherData.main.temp;
  const desc = weatherData.weather[0].description;
  const city = weatherData.name;
  const humidity = weatherData.main.humidity;
  const windSpeed = weatherData.wind.speed;

  return {
    city: city,
    temperature: `${temp}°C`,
    description: desc,
    humidity: `${humidity}%`,
    wind: `${windSpeed} m/s`,
    summary: `${city}: ${temp}°C, ${desc}, humidity ${humidity}%, wind ${windSpeed} m/s`,
  };
}

/**
 * Read API key from environment.
 * SCANNER NOTE: This triggers WARN-004 (environment variable access).
 * Legitimate use: API keys should come from environment/config, not hardcoded.
 */
function getApiKey() {
  const key = process.env.OPENWEATHER_API_KEY;
  if (!key) {
    throw new Error(
      "OPENWEATHER_API_KEY environment variable is not set. " +
      "Get a free API key at https://openweathermap.org/api"
    );
  }
  return key;
}

/**
 * Handle incoming skill requests.
 */
async function handleRequest(request) {
  const { city } = request;

  if (!city || typeof city !== "string") {
    return { success: false, error: "City name is required" };
  }

  // Check cache first
  const cached = getCached(city.toLowerCase());
  if (cached) {
    return { success: true, source: "cache", ...cached };
  }

  try {
    const apiKey = getApiKey();
    const weatherData = await fetchWeather(city, apiKey);
    const formatted = formatResponse(weatherData);

    // Cache the result
    setCache(city.toLowerCase(), formatted);

    return { success: true, source: "api", ...formatted };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

module.exports = { handleRequest };
