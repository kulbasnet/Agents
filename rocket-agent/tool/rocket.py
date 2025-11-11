import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from ..helper.help import format_datetime, geocode_location, calculate_distance, make_api_request_with_retry


def get_next_launch(
    status_filter: Optional[str] = "Go",
    provider_filter: Optional[str] = None,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Fetch upcoming rocket launches filtered by status and/or launch provider.
    
    By default, only returns confirmed upcoming launches with "Go for Launch" status.
    
    Args:
        status_filter: Status name to filter by (default: "Go" matches "Go for Launch"). 
                      Set to None to include all statuses (including completed launches).
        provider_filter: Launch service provider to filter by (e.g., "SpaceX", "Rocket Lab"). 
                        If None, all providers are included.
        max_results: Maximum number of results to return (default: 10)
    
    Returns:
        List of matching launches with their details
    
    Examples:
        # Get confirmed upcoming launches (default - "Go for Launch" only)
        get_next_launch()
        
        # Get ALL launches including past ones
        get_next_launch(status_filter=None)
        
        # Get upcoming SpaceX launches
        get_next_launch(provider_filter="SpaceX")
        
        # Get ALL SpaceX launches (including past)
        get_next_launch(status_filter=None, provider_filter="SpaceX")
    """
    try:
        url = "https://ll.thespacedevs.com/2.2.0/launch/upcoming"
        response = make_api_request_with_retry(url, timeout=10, max_retries=3)
        
        if response is None:
            print("❌ Failed to fetch launch data after retries")
            return []
        
        data = response.json()
        
        if not data.get('results'):
            return []
        
        launches = data['results']
        filtered_launches = []
        
        # Filter launches by status and/or provider
        for launch in launches:
            # Status filter
            status = launch.get('status', {})
            status_name = status.get('name', '')
            
            if status_filter and status_filter.lower() not in status_name.lower():
                continue
            
            # Provider filter
            provider_obj = launch.get('launch_service_provider', {})
            provider_name = provider_obj.get('name', '')
            provider_type = provider_obj.get('type', '')
            
            if provider_filter and provider_filter.lower() not in provider_name.lower():
                continue
            
            # Both filters passed, add the launch
            net_raw = launch.get('net')
            window_start_raw = launch.get('window_start')
            window_end_raw = launch.get('window_end')
            
            launch_data = {
                'id': launch.get('id'),
                'name': launch.get('name'),
                'status': status_name,
                'status_abbrev': status.get('abbrev'),
                'status_description': status.get('description'),
                'net': format_datetime(net_raw),  # No Earlier Than (launch time)
                'net_raw': net_raw,  # Keep original for parsing if needed
                'window_start': format_datetime(window_start_raw),
                'window_start_raw': window_start_raw,
                'window_end': format_datetime(window_end_raw),
                'window_end_raw': window_end_raw,
                'probability': launch.get('probability'),
                'launch_service_provider': provider_name,
                'provider_type': provider_type,
                'rocket': launch.get('rocket', {}).get('configuration', {}).get('full_name'),
                'mission_name': launch.get('mission', {}).get('name'),
                'mission_description': launch.get('mission', {}).get('description'),
                'mission_type': launch.get('mission', {}).get('type'),
                'orbit': launch.get('mission', {}).get('orbit', {}).get('name'),
                'pad_name': launch.get('pad', {}).get('name'),
                'location': launch.get('pad', {}).get('location', {}).get('name'),
                'latitude': launch.get('pad', {}).get('latitude'),
                'longitude': launch.get('pad', {}).get('longitude'),
                'country_code': launch.get('pad', {}).get('location', {}).get('country_code'),
                'image': launch.get('image'),
                'webcast_live': launch.get('webcast_live'),
                'url': launch.get('url'),
            }
            
            filtered_launches.append(launch_data)
            
            if len(filtered_launches) >= max_results:
                break
        
        return filtered_launches
    
    except requests.exceptions.RequestException as e:
        print(f"API request error: {e}")
        return []
    except Exception as e:
        print(f"Error processing launch data: {e}")
        return []


def format_launch_info(launch_data: Dict[str, Any]) -> str:
    """
    Format launch data into a readable string.
    
    Args:
        launch_data: Dictionary containing launch information
    
    Returns:
        Formatted string with launch details
    """
    output = []
    output.append("=" * 70)
    output.append(f"🚀 {launch_data.get('name', 'Unknown Launch')}")
    output.append("=" * 70)
    
    if launch_data.get('status'):
        output.append(f"📊 Status: {launch_data['status']} ({launch_data.get('status_abbrev', '')})")
    
    if launch_data.get('net'):
        output.append(f"🕐 Launch Time (NET): {launch_data['net']}")
    
    if launch_data.get('rocket'):
        output.append(f"🚀 Rocket: {launch_data['rocket']}")
    
    if launch_data.get('launch_service_provider'):
        provider_info = launch_data['launch_service_provider']
        if launch_data.get('provider_type'):
            provider_info += f" ({launch_data['provider_type']})"
        output.append(f"🏢 Provider: {provider_info}")
    
    if launch_data.get('mission_name'):
        output.append(f"\n🎯 Mission: {launch_data['mission_name']}")
    
    if launch_data.get('mission_type'):
        output.append(f"📋 Type: {launch_data['mission_type']}")
    
    if launch_data.get('orbit'):
        output.append(f"🛸 Orbit: {launch_data['orbit']}")
    
    if launch_data.get('mission_description'):
        output.append(f"\n📝 Description:\n{launch_data['mission_description']}")
    
    if launch_data.get('pad_name'):
        output.append(f"\n🗺️  Launch Pad: {launch_data['pad_name']}")
    
    if launch_data.get('location'):
        output.append(f"📍 Location: {launch_data['location']}")
    
    if launch_data.get('country_code'):
        output.append(f"🌍 Country: {launch_data['country_code']}")
    
    if launch_data.get('latitude') and launch_data.get('longitude'):
        output.append(f"🗺️  Coordinates: {launch_data['latitude']}, {launch_data['longitude']}")
    
    if launch_data.get('probability') is not None:
        output.append(f"\n📈 Probability: {launch_data['probability']}%")
    
    if launch_data.get('webcast_live'):
        output.append(f"📺 Webcast: LIVE")
    
    if launch_data.get('url'):
        output.append(f"\n🔗 Details: {launch_data['url']}")
    
    output.append("=" * 70)
    
    return "\n".join(output)


def get_all_upcoming_launches(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch all upcoming rocket launches without status filter.
    
    Args:
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        List of upcoming launches with their details
    """
    try:
        url = "https://ll.thespacedevs.com/2.2.0/launch/upcoming"
        response = make_api_request_with_retry(url, timeout=10, max_retries=3)
        
        if response is None:
            print("❌ Failed to fetch launch data after retries")
            return []
        
        data = response.json()
        
        if not data.get('results'):
            return []
        
        launches = data['results'][:limit]
        launch_list = []
        
        for launch in launches:
            net_raw = launch.get('net')
            
            launch_data = {
                'id': launch.get('id'),
                'name': launch.get('name'),
                'status': launch.get('status', {}).get('name'),
                'status_abbrev': launch.get('status', {}).get('abbrev'),
                'net': format_datetime(net_raw),
                'net_raw': net_raw,
                'launch_service_provider': launch.get('launch_service_provider', {}).get('name'),
                'rocket': launch.get('rocket', {}).get('configuration', {}).get('full_name'),
                'mission_name': launch.get('mission', {}).get('name'),
                'location': launch.get('pad', {}).get('location', {}).get('name'),
            }
            launch_list.append(launch_data)
        
        return launch_list
    
    except Exception as e:
        print(f"Error fetching launches: {e}")
        return []



def get_weatherData(
    latitude: float,
    longitude: float,
    days: int = 7,
    api_key: str = "c55f42e5541afc3eae9c13fe79207a1d"
    
) -> Dict[str, Any]:
    """
    Get weather forecast data using latitude and longitude.
    Free tier provides 5-day forecast in 3-hour intervals, aggregated by day.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        days: Number of days to forecast (default: 7, but free API limits to ~5 days)
        api_key: OpenWeatherMap API key
    
    Returns:
        Dictionary containing weather forecast data
    """
    try:
        # Free tier: 5-day forecast in 3-hour intervals
        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={latitude}&lon={longitude}&appid={api_key}&units=metric"
        response = make_api_request_with_retry(url, timeout=10, max_retries=3)
        
        if response is None:
            return {
                'error': 'Failed to fetch weather data after retries (rate limit or API issue)',
                'latitude': latitude,
                'longitude': longitude
            }
        
        data = response.json()
        
        if not data.get('list'):
            return {
                'error': 'No weather data available',
                'latitude': latitude,
                'longitude': longitude
            }
        
        # Group 3-hour forecasts by day (YYYY-MM-DD)
        from collections import defaultdict
        daily_map = defaultdict(list)
        
        for item in data.get('list', []):
            dt = datetime.fromtimestamp(item.get('dt'), tz=timezone.utc)
            day_key = dt.strftime('%Y-%m-%d')
            daily_map[day_key].append(item)
        
        # Convert to daily forecasts
        forecasts = []
        day_count = 0
        
        for day_key in sorted(daily_map.keys()):
            if day_count >= days:
                break
                
            items = daily_map[day_key]
            
            # Aggregate temperatures from 3-hour intervals
            temps = [item['main']['temp'] for item in items]
            feels_likes = [item['main']['feels_like'] for item in items]
            min_temp = min(temps)
            max_temp = max(temps)
            avg_temp = sum(temps) / len(temps)
            
            # Use midday data (11:00-14:00 UTC) for representative weather, or first available
            midday_item = next(
                (item for item in items 
                 if 11 <= datetime.fromtimestamp(item['dt'], tz=timezone.utc).hour <= 14),
                items[0]
            )
            
            forecast = {
                'date': format_datetime(f"{day_key}T12:00:00Z"),
                'date_raw': int(datetime.strptime(day_key, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp()),
                'temperature': {
                    'day': round(avg_temp, 1),
                    'min': round(min_temp, 1),
                    'max': round(max_temp, 1),
                    'morning': temps[0],
                    'night': temps[-1],
                },
                'feels_like': {
                    'day': round(sum(feels_likes) / len(feels_likes), 1),
                    'morning': feels_likes[0],
                    'night': feels_likes[-1],
                },
                'pressure': midday_item['main']['pressure'],
                'humidity': midday_item['main']['humidity'],
                'weather': {
                    'main': midday_item.get('weather', [{}])[0].get('main') if midday_item.get('weather') else None,
                    'description': midday_item.get('weather', [{}])[0].get('description') if midday_item.get('weather') else None,
                    'icon': midday_item.get('weather', [{}])[0].get('icon') if midday_item.get('weather') else None,
                },
                'clouds': midday_item.get('clouds', {}).get('all', 0),
                'wind_speed': midday_item.get('wind', {}).get('speed', 0),
                'wind_direction': midday_item.get('wind', {}).get('deg', 0),
                'precipitation': sum(item.get('rain', {}).get('3h', 0) for item in items),
                'snow': sum(item.get('snow', {}).get('3h', 0) for item in items),
            }
            forecasts.append(forecast)
            day_count += 1
        
        return {
            'location': {
                'latitude': latitude,
                'longitude': longitude,
                'city': data.get('city', {}).get('name'),
                'country': data.get('city', {}).get('country'),
            },
            'forecasts': forecasts,
            'days_count': len(forecasts)
        }
    
    except requests.exceptions.RequestException as e:
        return {
            'error': f'API request error: {str(e)}',
            'latitude': latitude,
            'longitude': longitude
        }
    except Exception as e:
        return {
            'error': f'Error processing weather data: {str(e)}',
            'latitude': latitude,
            'longitude': longitude
        }


def get_iss_passes(
    location: str,
    max_distance_km: float = 1000.0,
    days_ahead: int = 7,
    max_results: int = 10,
    specific_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Find upcoming rocket launches near a specified location and get weather forecast.
    
    Args:
        location: Location name (e.g., "balkhu", "New York", "Cape Canaveral")
        max_distance_km: Maximum distance from location in kilometers (default: 1000km)
        days_ahead: Number of days to look ahead (default: 7 days) - ignored if specific_date is provided
        max_results: Maximum number of results to return (default: 10)
        specific_date: Optional specific date to filter (e.g., "Nov 10", "2025-11-10", "November 10, 2025")
    
    Returns:
        Dictionary containing location info, matching launches, and weather forecast
    """
    try:
        # Step 1: Geocode the location
        location_data = geocode_location(location)
        
        if not location_data:
            return {
                'error': f'Location not found: {location}',
                'location': location
            }
        
        user_lat = location_data['latitude']
        user_lon = location_data['longitude']
        
        # Step 2: Parse specific date if provided
        target_date = None
        date_start = None
        date_end = None
        
        if specific_date:
            try:
                from dateutil import parser
                # Parse the date string (handles "Nov 10", "2025-11-10", "November 10, 2025", etc.)
                target_date = parser.parse(specific_date)
                
                # If no year specified, assume current or next year
                if target_date.year == datetime.now().year and target_date < datetime.now():
                    target_date = target_date.replace(year=datetime.now().year + 1)
                
                # Make timezone-aware
                target_date = target_date.replace(tzinfo=timezone.utc)
                
                # Set date range for the entire day
                date_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                date_end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                
            except Exception as e:
                return {
                    'error': f'Invalid date format: {specific_date}. Try "Nov 10" or "2025-11-10"',
                    'location': location
                }
        
        # Step 3: Get weather data for the location
        weather_data = get_weatherData(
            latitude=user_lat,
            longitude=user_lon,
            days=days_ahead if not specific_date else 16  # Get max days if specific date
        )
        
        # Filter weather for specific date if provided
        if specific_date and target_date:
            target_day = target_date.strftime('%Y-%m-%d')
            filtered_weather = []
            
            for forecast in weather_data.get('forecasts', []):
                forecast_date_obj = datetime.fromtimestamp(forecast.get('date_raw', 0), tz=timezone.utc)
                forecast_day = forecast_date_obj.strftime('%Y-%m-%d')
                
                if forecast_day == target_day:
                    filtered_weather.append(forecast)
            
            weather_data['forecasts'] = filtered_weather
            weather_data['days_count'] = len(filtered_weather)
            weather_data['filtered_for_date'] = target_date.strftime('%B %d, %Y')
        
        # Step 4: Fetch upcoming launches using get_next_launch
        # This gets only "Go for Launch" status by default
        all_launches = get_next_launch(max_results=max_results)
        
        if not all_launches:
            return {
                'location': location_data,
                'weather': weather_data,
                'launches': [],
                'message': 'No upcoming launches found'
            }
        
        # Step 5: Filter launches by date and distance
        filtered_launches = []
        
        # Calculate cutoff date (timezone-aware)
        if specific_date and date_end:
            cutoff_date = date_end
            start_date = date_start
        else:
            cutoff_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)
            start_date = datetime.now(timezone.utc)
        
        for launch in all_launches:
            # Check date
            net_raw = launch.get('net_raw')
            if not net_raw:
                continue
            
            try:
                launch_date = datetime.fromisoformat(net_raw.replace('Z', '+00:00'))
                
                # If specific date provided, check if launch is on that day
                if specific_date and date_start and date_end:
                    if not (date_start <= launch_date <= date_end):
                        continue
                else:
                    # Otherwise, check if within days_ahead range
                    if launch_date > cutoff_date or launch_date < start_date:
                        continue
            except:
                continue
            
            # Check location distance
            launch_lat = launch.get('latitude')
            launch_lon = launch.get('longitude')
            
            if launch_lat is None or launch_lon is None:
                continue
            
            # Convert to float if they're strings
            try:
                launch_lat = float(launch_lat)
                launch_lon = float(launch_lon)
            except:
                continue
            
            # Calculate distance
            distance = calculate_distance(user_lat, user_lon, launch_lat, launch_lon)
            
            if distance <= max_distance_km:
                # Add distance to the already formatted launch data
                launch['distance_km'] = round(distance, 2)
                filtered_launches.append(launch)
        
        # Sort by distance
        filtered_launches.sort(key=lambda x: x['distance_km'])
        
        # Step 6: Check visibility based on weather conditions
        for launch in filtered_launches:
            visibility_status = "Good"
            visibility_reasons = []
            
            # Get launch date to match with weather forecast
            launch_date_str = launch.get('net_raw')
            if launch_date_str:
                try:
                    launch_date = datetime.fromisoformat(launch_date_str.replace('Z', '+00:00'))
                    launch_day = launch_date.strftime('%Y-%m-%d')
                    
                    # Find matching weather forecast for this launch date
                    matching_weather = None
                    for forecast in weather_data.get('forecasts', []):
                        forecast_date_obj = datetime.fromtimestamp(forecast.get('date_raw', 0), tz=timezone.utc)
                        forecast_day = forecast_date_obj.strftime('%Y-%m-%d')
                        
                        if forecast_day == launch_day:
                            matching_weather = forecast
                            break
                    
                    if matching_weather:
                        # Check weather conditions for visibility
                        weather_main = matching_weather.get('weather', {}).get('main', '').lower()
                        clouds = matching_weather.get('clouds', 0)
                        humidity = matching_weather.get('humidity', 0)
                        precipitation = matching_weather.get('precipitation', 0)
                        snow = matching_weather.get('snow', 0)
                        
                        # Check bad weather conditions
                        bad_weather = weather_main in ['clouds', 'rain', 'thunderstorm', 'snow', 'drizzle', 'mist', 'fog']
                        high_clouds = clouds > 30
                        high_humidity = humidity > 80
                        high_precipitation = precipitation > 5
                        high_snow = snow > 5
                        
                        # Determine visibility
                        if bad_weather:
                            visibility_reasons.append(f"Poor weather: {weather_main.title()}")
                        if high_clouds:
                            visibility_reasons.append(f"High cloud cover: {clouds}%")
                        if high_humidity:
                            visibility_reasons.append(f"High humidity: {humidity}%")
                        if high_precipitation:
                            visibility_reasons.append(f"Heavy precipitation: {precipitation}mm")
                        if high_snow:
                            visibility_reasons.append(f"Heavy snow: {snow}mm")
                        
                        # Set visibility status
                        if len(visibility_reasons) >= 3 or high_snow or (bad_weather and high_clouds):
                            visibility_status = "Not Visible"
                        elif len(visibility_reasons) >= 1:
                            visibility_status = "Low Visibility"
                        else:
                            visibility_status = "Good"
                        
                        # Add weather info to launch
                        launch['weather_forecast'] = {
                            'main': matching_weather.get('weather', {}).get('main'),
                            'description': matching_weather.get('weather', {}).get('description'),
                            'clouds': clouds,
                            'humidity': humidity,
                            'precipitation': precipitation,
                            'snow': snow,
                            'temperature': matching_weather.get('temperature', {}),
                        }
                    else:
                        visibility_status = "Unknown"
                        visibility_reasons.append("No weather forecast available for launch date")
                
                except Exception as e:
                    visibility_status = "Unknown"
                    visibility_reasons.append(f"Error checking weather: {str(e)}")
            
            # Add visibility info to launch
            launch['visibility'] = {
                'status': visibility_status,
                'can_be_seen': visibility_status in ['Good', 'Low Visibility'],
                'reasons': visibility_reasons if visibility_reasons else ['Clear conditions expected']
            }
        
        result = {
            'location': location_data,
            'search_params': {
                'max_distance_km': max_distance_km,
                'days_ahead': days_ahead
            },
            'launches_found': len(filtered_launches),
            'launches': filtered_launches
        }
        
        # Only include general weather forecast if no launches found
        # (each launch already has its own weather_forecast)
        if len(filtered_launches) == 0:
            result['weather'] = weather_data
        
        # Add specific date info if provided
        if specific_date and target_date:
            result['search_params']['specific_date'] = target_date.strftime('%B %d, %Y')
            result['search_params']['date_filter_active'] = True
        
        return result
    
    except requests.exceptions.RequestException as e:
        return {
            'error': f'API request error: {str(e)}',
            'location': location
        }
    except Exception as e:
        return {
            'error': f'Error processing data: {str(e)}',
            'location': location
        }
