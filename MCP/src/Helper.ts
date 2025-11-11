import fetch from "node-fetch";

// =============== Rate Limiting & Retry Logic ===============

async function makeApiRequestWithRetry(
  url: string,
  maxRetries: number = 3,
  backoffFactor: number = 2.0
): Promise<any | null> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const response = await fetch(url);

      // Check for rate limiting
      if (response.status === 429) {
        const retryAfter = parseInt(response.headers.get('retry-after') || String(backoffFactor ** attempt));
        console.warn(`⚠️  Rate limited. Waiting ${retryAfter} seconds before retry ${attempt + 1}/${maxRetries}...`);
        await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
        continue;
      }

      // Check for API key issues
      if (response.status === 403) {
        const errorData = await response.json().catch(() => ({ message: 'API key invalid or quota exceeded' })) as any;
        console.error(`❌ API Access Forbidden (403): ${errorData.message || 'Unknown error'}`);
        return null;
      }

      // Check for unauthorized
      if (response.status === 401) {
        console.error(`❌ Unauthorized (401): Invalid API key`);
        return null;
      }

      // Check if response is ok
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      // Success!
      return response;

    } catch (err: any) {
      if (err.name === 'AbortError' || err.code === 'ETIMEDOUT') {
        console.warn(`⚠️  Request timeout. Retry ${attempt + 1}/${maxRetries}...`);
      } else if (err.code === 'ECONNREFUSED' || err.code === 'ENOTFOUND') {
        console.warn(`⚠️  Connection error. Retry ${attempt + 1}/${maxRetries}...`);
      } else {
        console.error(`❌ Request error: ${err.message}`);
        return null;
      }

      if (attempt < maxRetries - 1) {
        const waitTime = backoffFactor ** attempt;
        await new Promise(resolve => setTimeout(resolve, waitTime * 1000));
        continue;
      } else {
        console.error(`❌ Request failed after ${maxRetries} attempts`);
        return null;
      }
    }
  }

  return null;
}

// =============== Helper Functions ===============

// Convert ISO 8601 datetime to readable format
export function formatDatetime(isoDatetime?: string): string {
  if (!isoDatetime) return "N/A";
  try {
    const dt = new Date(isoDatetime);
    return dt.toUTCString(); // Example: "Thu, 06 Nov 2025 20:56:00 GMT"
  } catch {
    return isoDatetime;
  }
}

// Haversine formula to calculate distance (in km)
export function calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371.0; // Earth's radius (km)
  const toRad = (deg: number) => (deg * Math.PI) / 180;

  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export interface WeatherTemperature {
  day?: number;
  min?: number;
  max?: number;
  night?: number;
  evening?: number;
  morning?: number;
}

export interface WeatherFeelsLike {
  day?: number;
  night?: number;
  evening?: number;
  morning?: number;
}

export interface WeatherDetails {
  main?: string;
  description?: string;
  icon?: string;
}

export interface DailyWeather{
  date: string;
  date_raw: number;
  feels_like: WeatherFeelsLike;
  pressure?: number;
  humidity?: number;
  clouds?: number;
  wind_speed?: number;
  wind_direction?: number;
  precipitation?: number;
  snow?: number;
  weather: WeatherDetails;
  temperature: WeatherTemperature;
}


export interface WeatherForecastResult {
  location: {
    latitude: number;
    longitude: number;
    city?: string;
    country?: string;
  };
  forecasts: DailyWeather[];
  days_count: number;
  error?: string;
}

export async function getWeatherData(
  latitude: number,
  longitude: number,
  days: number = 7,
  apiKey="c55f42e5541afc3eae9c13fe79207a1d"
): Promise<WeatherForecastResult> {
  try {
    // Free tier: 5-day forecast in 3-hour intervals
    const url = `http://api.openweathermap.org/data/2.5/forecast?lat=${latitude}&lon=${longitude}&appid=${apiKey}&units=metric`;
    const response = await makeApiRequestWithRetry(url, 3, 2.0);
    
    if (!response) {
      return {
        location: { latitude, longitude },
        forecasts: [],
        days_count: 0,
        error: 'Failed to fetch weather data after retries (rate limit or API issue)',
      };
    }

    const data = (await response.json()) as any;

    if (!data.list || !Array.isArray(data.list)) {
      return {
        location: {
          latitude,
          longitude,
          city: data.city?.name,
          country: data.city?.country,
        },
        forecasts: [],
        days_count: 0,
        error: "No weather data available",
      };
    }

    // Group 3-hour forecasts by day (YYYY-MM-DD)
    const dailyMap = new Map<string, any[]>();
    
    for (const item of data.list) {
      const date = new Date(item.dt * 1000);
      const dayKey = date.toISOString().split('T')[0];
      
      if (!dailyMap.has(dayKey)) {
        dailyMap.set(dayKey, []);
      }
      dailyMap.get(dayKey)!.push(item);
    }

    // Convert to daily forecasts
    const forecasts: DailyWeather[] = [];
    let dayCount = 0;

    for (const [dayKey, items] of dailyMap) {
      if (dayCount >= days) break;
      
      // Aggregate temperatures from 3-hour intervals
      const temps = items.map(i => i.main.temp);
      const feelsLikes = items.map(i => i.main.feels_like);
      const minTemp = Math.min(...temps);
      const maxTemp = Math.max(...temps);
      const avgTemp = temps.reduce((a, b) => a + b, 0) / temps.length;
      
      // Use midday data (11:00-14:00) for representative weather, or first available
      const middayItem = items.find(i => {
        const hour = new Date(i.dt * 1000).getUTCHours();
        return hour >= 11 && hour <= 14;
      }) || items[0];

      const forecast: DailyWeather = {
        date: formatDatetime(new Date(dayKey + 'T12:00:00Z').toISOString()),
        date_raw: Math.floor(new Date(dayKey).getTime() / 1000),
        temperature: {
          day: Math.round(avgTemp * 10) / 10,
          min: Math.round(minTemp * 10) / 10,
          max: Math.round(maxTemp * 10) / 10,
          morning: temps[0],
          night: temps[temps.length - 1],
        },
        feels_like: {
          day: Math.round((feelsLikes.reduce((a, b) => a + b, 0) / feelsLikes.length) * 10) / 10,
          morning: feelsLikes[0],
          night: feelsLikes[feelsLikes.length - 1],
        },
        pressure: middayItem.main.pressure,
        humidity: middayItem.main.humidity,
        weather: {
          main: middayItem.weather?.[0]?.main,
          description: middayItem.weather?.[0]?.description,
          icon: middayItem.weather?.[0]?.icon,
        },
        clouds: middayItem.clouds?.all || 0,
        wind_speed: middayItem.wind?.speed || 0,
        wind_direction: middayItem.wind?.deg || 0,
        precipitation: items.reduce((sum, i) => sum + (i.rain?.['3h'] || 0), 0),
        snow: items.reduce((sum, i) => sum + (i.snow?.['3h'] || 0), 0),
      };

      forecasts.push(forecast);
      dayCount++;
    }

    return {
      location: {
        latitude,
        longitude,
        city: data.city?.name,
        country: data.city?.country,
      },
      forecasts,
      days_count: forecasts.length,
    };
  } catch (err: any) {
    console.error("API error:", err);
    return {
      location: { latitude, longitude },
      forecasts: [],
      days_count: 0,
      error: String(err),
    };
  }
}

// =============== Geocoding ===============

export interface GeocodeResult {
  name: string;
  local_name: string;
  latitude: number;
  longitude: number;
  country: string;
  state: string;
}

export async function geocodeLocation(
  location: string,
  apiKey = "d9750e4144f8260ffb2fd41fccde41c4"
): Promise<GeocodeResult | null> {
  try {
    const url = `http://api.openweathermap.org/geo/1.0/direct?q=${encodeURIComponent(
      location
    )}&limit=1&appid=${apiKey}`;
    const response = await makeApiRequestWithRetry(url, 3, 2.0);
    
    if (!response) {
      console.error(`❌ Failed to geocode location '${location}' after retries`);
      return null;
    }
    
    const data = (await response.json()) as any[];

    if (data && data.length > 0) {
      const res = data[0];
      return {
        name: res.name,
        local_name: res.local_names?.en || res.name,
        latitude: res.lat,
        longitude: res.lon,
        country: res.country,
        state: res.state || "N/A",
      };
    }
    return null;
  } catch (err) {
    console.error("Geocoding error:", err);
    return null;
  }
}

// =============== Launch Data ===============

interface Launch {
  id: string;
  name: string;
  status: string;
  status_abbrev?: string;
  status_description?: string;
  net: string | null;
  net_raw: string | null;
  window_start: string | null;
  window_start_raw: string | null;
  window_end: string | null;
  window_end_raw: string | null;
  probability?: number;
  launch_service_provider?: string;
  provider_type?: string;
  rocket?: string;
  mission_name?: string;
  mission_description?: string;
  mission_type?: string;
  orbit?: string;
  pad_name?: string;
  location?: string;
  latitude?: number;
  longitude?: number;
  country_code?: string;
  image?: string;
  webcast_live?: boolean;
  url?: string;
  distance_km?: number;
}

interface ApiResponse {
  results: any[];
}


export async function getNextLaunch(
  statusFilter: string | null = "Go",
  providerFilter: string | null = null,
  maxResults: number = 10
): Promise<Launch[]> {
  try {
    const url = "https://ll.thespacedevs.com/2.2.0/launch/upcoming";
    const response = await makeApiRequestWithRetry(url, 10000, 3);

    if (!response) {
      console.error("❌ Failed to fetch launch data after retries");
      return [];
    }

    const data: ApiResponse = await response.json();
    if (!data.results || data.results.length === 0) return [];

    const launches = data.results;
    const filteredLaunches: Launch[] = [];

    for (const launch of launches) {
      const statusObj = launch.status || {};
      const statusName: string = statusObj.name || "";

      if (statusFilter && !statusName.toLowerCase().includes(statusFilter.toLowerCase())) {
        continue;
      }

      const providerObj = launch.launch_service_provider || {};
      const providerName: string = providerObj.name || "";
      const providerType: string = providerObj.type || "";

      if (providerFilter && !providerName.toLowerCase().includes(providerFilter.toLowerCase())) {
        continue;
      }

      const netRaw = launch.net;
      const windowStartRaw = launch.window_start;
      const windowEndRaw = launch.window_end;

      const launchData: Launch = {
        id: launch.id,
        name: launch.name,
        status: statusName,
        status_abbrev: statusObj.abbrev,
        status_description: statusObj.description,
        net: formatDatetime(netRaw),
        net_raw: netRaw,
        window_start: formatDatetime(windowStartRaw),
        window_start_raw: windowStartRaw,
        window_end: formatDatetime(windowEndRaw),
        window_end_raw: windowEndRaw,
        probability: launch.probability,
        launch_service_provider: providerName,
        provider_type: providerType,
        rocket: launch.rocket?.configuration?.full_name,
        mission_name: launch.mission?.name,
        mission_description: launch.mission?.description,
        mission_type: launch.mission?.type,
        orbit: launch.mission?.orbit?.name,
        pad_name: launch.pad?.name,
        location: launch.pad?.location?.name,
        latitude: launch.pad?.latitude,
        longitude: launch.pad?.longitude,
        country_code: launch.pad?.location?.country_code,
        image: launch.image,
        webcast_live: launch.webcast_live,
        url: launch.url,
      };

      filteredLaunches.push(launchData);

      if (filteredLaunches.length >= maxResults) break;
    }

    return filteredLaunches;
  } catch (error) {
    console.error("Error processing launch data:", error);
    return [];
  }
}
// =============== ISS / Launch Finder ===============

export async function getNearbyLaunches(
  location: string,
  maxDistanceKm = 1000,
  daysAhead = 7,
  maxResults = 10,
  specificDate?: string
): Promise<Record<string, any>> {
  try {
    // Step 1: Geocode the location
    const locData = await geocodeLocation(location);
    if (!locData) {
      return { error: `Location not found: ${location}`, location };
    }

    // Step 2: Parse specific date if provided
    let targetDate: Date | null = null;
    let dateStart: Date | null = null;
    let dateEnd: Date | null = null;

    if (specificDate) {
      try {
        // Parse date string (handles "Nov 10", "2025-11-10", "November 10, 2025", etc.)
        targetDate = new Date(specificDate);
        
        // Check if valid date
        if (isNaN(targetDate.getTime())) {
          throw new Error("Invalid date");
        }

        // If date is in the past (and no year was specified), assume next year
        const now = new Date();
        if (targetDate < now && !specificDate.match(/\d{4}/)) {
          targetDate.setFullYear(now.getFullYear() + 1);
        }

        // Set date range for the entire day (UTC)
        dateStart = new Date(Date.UTC(
          targetDate.getFullYear(),
          targetDate.getMonth(),
          targetDate.getDate(),
          0, 0, 0, 0
        ));
        dateEnd = new Date(Date.UTC(
          targetDate.getFullYear(),
          targetDate.getMonth(),
          targetDate.getDate(),
          23, 59, 59, 999
        ));
      } catch (err) {
        return {
          error: `Invalid date format: ${specificDate}. Try "Nov 10" or "2025-11-10"`,
          location,
        };
      }
    }

    // Step 3: Get weather data for the location
    const weatherData = await getWeatherData(
      locData.latitude,
      locData.longitude,
      specificDate ? 16 : daysAhead // Get max days if specific date
    );

    // Filter weather for specific date if provided
    if (specificDate && targetDate) {
      const targetDay = targetDate.toISOString().split('T')[0];
      const filteredWeather = weatherData.forecasts.filter((forecast: any) => {
        const forecastDate = new Date(forecast.date_raw * 1000);
        const forecastDay = forecastDate.toISOString().split('T')[0];
        return forecastDay === targetDay;
      });

      weatherData.forecasts = filteredWeather;
      weatherData.days_count = filteredWeather.length;
      (weatherData as any).filtered_for_date = targetDate.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    }

    // Step 4: Fetch upcoming launches
    const launches = await getNextLaunch("Go", undefined, maxResults);
    const cutoff = specificDate && dateEnd ? dateEnd : new Date(Date.now() + daysAhead * 86400000);
    const startDate = specificDate && dateStart ? dateStart : new Date();
    const nearby: Launch[] = [];

    // Step 5: Filter launches by date and distance
    for (const launch of launches) {
      if (!launch.net_raw) continue;
      const launchTime = new Date(launch.net_raw);

      // If specific date provided, check if launch is on that day
      if (specificDate && dateStart && dateEnd) {
        if (!(launchTime >= dateStart && launchTime <= dateEnd)) {
          continue;
        }
      } else {
        // Otherwise, check if within days_ahead range
        if (launchTime > cutoff || launchTime < startDate) {
          continue;
        }
      }

      if (launch.latitude === undefined || launch.longitude === undefined) continue;
      
      const distance = calculateDistance(
        locData.latitude,
        locData.longitude,
        launch.latitude,
        launch.longitude
      );
      if (distance <= maxDistanceKm) {
        launch.distance_km = Math.round(distance * 100) / 100;
        nearby.push(launch);
      }
    }

    nearby.sort((a, b) => (a.distance_km || 0) - (b.distance_km || 0));

    // Step 6: Check visibility based on weather conditions
    for (const launch of nearby) {
      let visibilityStatus = "Good";
      const visibilityReasons: string[] = [];

      // Get launch date to match with weather forecast
      const launchDateStr = launch.net_raw;
      if (launchDateStr) {
        try {
          const launchDate = new Date(launchDateStr);
          const launchDay = launchDate.toISOString().split('T')[0];

          // Find matching weather forecast for this launch date
          let matchingWeather: any = null;
          for (const forecast of weatherData.forecasts) {
            const forecastDate = new Date(forecast.date_raw * 1000);
            const forecastDay = forecastDate.toISOString().split('T')[0];

            if (forecastDay === launchDay) {
              matchingWeather = forecast;
              break;
            }
          }

          if (matchingWeather) {
            // Check weather conditions for visibility
            const weatherMain = (matchingWeather.weather?.main || '').toLowerCase();
            const clouds = matchingWeather.clouds || 0;
            const humidity = matchingWeather.humidity || 0;
            const precipitation = matchingWeather.precipitation || 0;
            const snow = matchingWeather.snow || 0;

            // Check bad weather conditions
            const badWeather = ['clouds', 'rain', 'thunderstorm', 'snow', 'drizzle', 'mist', 'fog'].includes(weatherMain);
            const highClouds = clouds > 30;
            const highHumidity = humidity > 80;
            const highPrecipitation = precipitation > 5;
            const highSnow = snow > 5;

            // Determine visibility
            if (badWeather) {
              visibilityReasons.push(`Poor weather: ${weatherMain.charAt(0).toUpperCase() + weatherMain.slice(1)}`);
            }
            if (highClouds) {
              visibilityReasons.push(`High cloud cover: ${clouds}%`);
            }
            if (highHumidity) {
              visibilityReasons.push(`High humidity: ${humidity}%`);
            }
            if (highPrecipitation) {
              visibilityReasons.push(`Heavy precipitation: ${precipitation}mm`);
            }
            if (highSnow) {
              visibilityReasons.push(`Heavy snow: ${snow}mm`);
            }

            // Set visibility status
            if (visibilityReasons.length >= 3 || highSnow || (badWeather && highClouds)) {
              visibilityStatus = "Not Visible";
            } else if (visibilityReasons.length >= 1) {
              visibilityStatus = "Low Visibility";
            } else {
              visibilityStatus = "Good";
            }

            // Add weather info to launch
            (launch as any).weather_forecast = {
              main: matchingWeather.weather?.main,
              description: matchingWeather.weather?.description,
              clouds,
              humidity,
              precipitation,
              snow,
              temperature: matchingWeather.temperature,
            };
          } else {
            visibilityStatus = "Unknown";
            visibilityReasons.push("No weather forecast available for launch date");
          }
        } catch (err) {
          visibilityStatus = "Unknown";
          visibilityReasons.push(`Error checking weather: ${String(err)}`);
        }
      }

      // Add visibility info to launch
      (launch as any).visibility = {
        status: visibilityStatus,
        can_be_seen: ['Good', 'Low Visibility'].includes(visibilityStatus),
        reasons: visibilityReasons.length > 0 ? visibilityReasons : ['Clear conditions expected']
      };
    }

    const result: Record<string, any> = {
      location: locData,
      search_params: { maxDistanceKm, daysAhead },
      launches_found: nearby.length,
      launches: nearby,
    };

    // Only include general weather forecast if no launches found
    // (each launch already has its own weather_forecast)
    if (nearby.length === 0) {
      result.weather = weatherData;
    }

    // Add specific date info if provided
    if (specificDate && targetDate) {
      result.search_params.specific_date = targetDate.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
      result.search_params.date_filter_active = true;
    }

    return result;
  } catch (err) {
    return { error: `Processing error: ${String(err)}`, location };
  }
}

// =============== PNCT Container Tracking ===============

export interface ContainerInfo {
  containerNumber: string;
  location: string;
  availabilityStatus: string;
  containerState: string;
  carrierName: string;
  vesselName?: string;
  voyageNumber?: string;
  billOfLading?: string;
  size: string;
  type: string;
  customReleaseStatus?: string;
  carrierReleaseStatus?: string;
  usdaStatus?: string;
  freeDays?: string;
  lastFreeDate?: string;
  demurrageAmount?: number;
  isHazardous?: boolean;
  isOog?: boolean;
  consignee?: string;
  portOfDischarge?: string;
  vesselArrivalTime?: string;
  rawData?: any;
}

export interface ContainerFilters {
  type?: string;              // e.g., "GP", "HC", "OT"
  availabilityStatus?: string; // e.g., "No", "Yes"
  customReleaseStatus?: string; // e.g., "RELEASED", "HOLD"
  carrierReleaseStatus?: string; // e.g., "RELEASED", "HOLD"
  size?: string;              // e.g., "40'", "20'"
  location?: string;          // e.g., "Vessel", "Yard"
  containerState?: string;    // e.g., "Inbound", "Outbound"
  isHazardous?: boolean;
}

/**
 * Helper function to check if a container matches the given filters
 */
function matchesFilters(container: ContainerInfo, filters: ContainerFilters): boolean {
  if (filters.type && container.type.toUpperCase() !== filters.type.toUpperCase()) {
    return false;
  }
  if (filters.availabilityStatus && container.availabilityStatus.toLowerCase() !== filters.availabilityStatus.toLowerCase()) {
    return false;
  }
  if (filters.customReleaseStatus && container.customReleaseStatus?.toUpperCase() !== filters.customReleaseStatus.toUpperCase()) {
    return false;
  }
  if (filters.carrierReleaseStatus && container.carrierReleaseStatus?.toUpperCase() !== filters.carrierReleaseStatus.toUpperCase()) {
    return false;
  }
  if (filters.size && !container.size.includes(filters.size)) {
    return false;
  }
  if (filters.location && container.location.toLowerCase() !== filters.location.toLowerCase()) {
    return false;
  }
  if (filters.containerState && container.containerState.toLowerCase() !== filters.containerState.toLowerCase()) {
    return false;
  }
  if (filters.isHazardous !== undefined && container.isHazardous !== filters.isHazardous) {
    return false;
  }
  return true;
}

/**
 * Fetch container tracking information from Port America PNCT API
 * Can fetch a single container by number or search with filters
 * 
 * @param containerNumber - Container number to track (e.g., "TGHU5226554"), or empty string to search all
 * @param filters - Optional filters to apply to results
 * @returns Container tracking information or list of containers matching filters
 */
export async function pnctScrape(
  containerNumber?: string, 
  filters?: ContainerFilters
): Promise<ContainerInfo | ContainerInfo[] | { error: string }> {
  try {
    // Validate input
    if (!containerNumber || containerNumber.trim().length === 0) {
      if (filters && Object.keys(filters).length > 0) {
        return { error: "Container number or search pattern is required. The PNCT API requires a container number to search." };
      }
      return { error: "Container number is required" };
    }

    const cleanContainerNumber = containerNumber.trim().toUpperCase();
    
    // Build API URL - support wildcards with *
    const searchKey = cleanContainerNumber.includes('*') ? cleanContainerNumber : cleanContainerNumber;
    const url = `https://businquiry.portsamerica.com/api/track/GetContainers?siteId=PNCT_NJ&key=${encodeURIComponent(searchKey)}`;
    
    // Make API request with retry logic
    const response = await makeApiRequestWithRetry(url, 3, 2.0);
    
    if (!response) {
      return { error: `Failed to fetch container information for ${cleanContainerNumber} after retries` };
    }

    const data = await response.json() as any[];
    
    // Check if containers were found
    if (!data || data.length === 0) {
      return { error: `No containers found matching: ${cleanContainerNumber}` };
    }

    // Parse all containers from response
    const containers: ContainerInfo[] = data.map((container: any) => ({
      containerNumber: container.ContainerNumber || cleanContainerNumber,
      location: container.Location || "Unknown",
      availabilityStatus: container.AvailabilityDisplayStatus || "Unknown",
      containerState: container.ContainerState || "Unknown",
      carrierName: container.CarrierName || "Unknown",
      vesselName: container.VesselName || undefined,
      voyageNumber: container.VoyageNumber || undefined,
      billOfLading: container.BillOfLadingNumber || undefined,
      size: `${container.Length || 'N/A'} x ${container.Height || 'N/A'}`,
      type: container.Type || container.IsoType || "Unknown",
      customReleaseStatus: container.CustomReleaseStatus || undefined,
      carrierReleaseStatus: container.CarrierReleaseStatus || undefined,
      usdaStatus: container.UsdaStatus || undefined,
      freeDays: container.FreeDays || undefined,
      lastFreeDate: container.LastFreeDate || container.LastFreeDt || undefined,
      demurrageAmount: container.DemurrageAmount || 0,
      isHazardous: container.IsHazardous || false,
      isOog: container.IsOog || false,
      consignee: container.Consignee || undefined,
      portOfDischarge: container.PortOfDischarge || undefined,
      vesselArrivalTime: container.VesselArrivalTime || undefined,
      rawData: container
    }));

    // Apply filters if provided
    let filteredContainers = containers;
    if (filters && Object.keys(filters).length > 0) {
      filteredContainers = containers.filter(c => matchesFilters(c, filters));
      
      if (filteredContainers.length === 0) {
        return { error: `No containers found matching the specified filters` };
      }
    }

    // Return single container if only one result, otherwise return array
    if (filteredContainers.length === 1) {
      return filteredContainers[0];
    }
    
    return filteredContainers;

  } catch (err) {
    return { 
      error: `Error fetching container information: ${err instanceof Error ? err.message : String(err)}` 
    };
  }
}