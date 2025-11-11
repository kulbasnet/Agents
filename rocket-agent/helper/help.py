from typing import Optional, Dict, Any
from datetime import datetime
import math
import requests
import time


def make_api_request_with_retry(
    url: str,
    timeout: int = 10,
    max_retries: int = 3,
    backoff_factor: float = 2.0
) -> Optional[requests.Response]:
    """
    Make an API request with retry logic and exponential backoff for rate limiting.
    
    Args:
        url: The URL to request
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff (default: 2.0)
    
    Returns:
        Response object if successful, None if all retries failed
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=timeout)
            
            # Check for rate limiting
            if response.status_code == 429:
                # Too Many Requests - rate limited
                retry_after = int(response.headers.get('Retry-After', backoff_factor ** attempt))
                print(f"⚠️  Rate limited. Waiting {retry_after} seconds before retry {attempt + 1}/{max_retries}...")
                time.sleep(retry_after)
                continue
            
            # Check for API key issues
            if response.status_code == 403:
                error_msg = response.json().get('message', 'API key invalid or quota exceeded')
                print(f"❌ API Access Forbidden (403): {error_msg}")
                return None
            
            # Check for other client errors
            if response.status_code == 401:
                print(f"❌ Unauthorized (401): Invalid API key")
                return None
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            # Success!
            return response
            
        except requests.exceptions.Timeout:
            print(f"⚠️  Request timeout. Retry {attempt + 1}/{max_retries}...")
            if attempt < max_retries - 1:
                time.sleep(backoff_factor ** attempt)
                continue
            else:
                print(f"❌ Request timed out after {max_retries} attempts")
                return None
                
        except requests.exceptions.ConnectionError:
            print(f"⚠️  Connection error. Retry {attempt + 1}/{max_retries}...")
            if attempt < max_retries - 1:
                time.sleep(backoff_factor ** attempt)
                continue
            else:
                print(f"❌ Connection failed after {max_retries} attempts")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return None
    
    return None


def format_datetime(iso_datetime: Optional[str]) -> str:
    """
    Convert ISO 8601 datetime format to a human-readable format.
    
    Args:
        iso_datetime: ISO 8601 datetime string (e.g., "2025-11-06T20:56:00Z")
    
    Returns:
        Formatted datetime string (e.g., "November 6, 2025 at 8:56 PM UTC")
    """
    if not iso_datetime:
        return "N/A"
    
    try:
        # Parse ISO format (Z indicates UTC)
        dt = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
        
        # Format as readable string
        formatted = dt.strftime("%B %d, %Y at %I:%M %p UTC")
        return formatted
    except Exception as e:
        return iso_datetime  # Return original if parsing fails

def geocode_location(location: str, api_key: str = "d9750e4144f8260ffb2fd41fccde41c4") -> Optional[Dict[str, Any]]:
    """
    Convert a location name to latitude and longitude coordinates using OpenWeatherMap Geocoding API.
    
    Args:
        location: Location name (e.g., "balkhu", "New York", "London")
        api_key: OpenWeatherMap API key
    
    Returns:
        Dictionary with location details including lat/lon, or None if not found
    """
    try:
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={api_key}"
        response = make_api_request_with_retry(url, timeout=10, max_retries=3)
        
        if response is None:
            print(f"❌ Failed to geocode location '{location}' after retries")
            return None
        
        data = response.json()
        
        if data and len(data) > 0:
            result = data[0]
            return {
                'name': result.get('name'),
                'local_name': result.get('local_names', {}).get('en', result.get('name')),
                'latitude': result.get('lat'),
                'longitude': result.get('lon'),
                'country': result.get('country'),
                'state': result.get('state', 'N/A')
            }
        
        return None
    
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance between two coordinates using the Haversine formula.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
    
    Returns:
        Distance in kilometers
    """
    # Earth's radius in kilometers
    R = 6371.0
    
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance
