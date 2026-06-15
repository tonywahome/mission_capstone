"""
Location Service - Reverse geocoding for coordinates to location names
"""
import httpx
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def get_centroid_from_geometry(geometry: Dict) -> Optional[Tuple[float, float]]:
    """
    Extract centroid coordinates from GeoJSON geometry.
    
    Args:
        geometry: GeoJSON geometry object
        
    Returns:
        Tuple of (longitude, latitude) or None
    """
    try:
        geom_type = geometry.get('type')
        coords = geometry.get('coordinates', [])
        
        if geom_type == 'Point':
            return tuple(coords)
        elif geom_type == 'Polygon':
            # Get first ring (exterior)
            ring = coords[0] if coords else []
            if not ring:
                return None
            # Calculate centroid
            lon_sum = sum(p[0] for p in ring)
            lat_sum = sum(p[1] for p in ring)
            count = len(ring)
            return (lon_sum / count, lat_sum / count)
        elif geom_type == 'MultiPolygon':
            # Use first polygon
            if coords and coords[0]:
                ring = coords[0][0]
                lon_sum = sum(p[0] for p in ring)
                lat_sum = sum(p[1] for p in ring)
                count = len(ring)
                return (lon_sum / count, lat_sum / count)
        
        return None
    except Exception as e:
        logger.error(f"Error extracting centroid: {e}")
        return None


def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """
    Get location name from coordinates using Nominatim (OpenStreetMap).
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        Location string or None
    """
    try:
        # Use Nominatim API (free, no API key needed)
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': lat,
            'lon': lon,
            'format': 'json',
            'zoom': 10,  # City/town level
            'accept-language': 'en'
        }
        headers = {
            'User-Agent': 'TerraFoma Carbon Credit Platform'
        }
        
        response = httpx.get(url, params=params, headers=headers, timeout=5.0)
        
        if response.status_code == 200:
            data = response.json()
            address = data.get('address', {})
            
            # Build location string from available components
            parts = []
            
            # Try to get city/town/village
            for key in ['city', 'town', 'village', 'county', 'state_district']:
                if key in address:
                    parts.append(address[key])
                    break
            
            # Add country
            if 'country' in address:
                parts.append(address['country'])
            
            if parts:
                location = ', '.join(parts)
                logger.info(f"Geocoded ({lat}, {lon}) -> {location}")
                return location
        
        logger.warning(f"Geocoding failed for ({lat}, {lon}): {response.status_code}")
        return None
        
    except Exception as e:
        logger.error(f"Error in reverse geocoding: {e}")
        return None


def get_location_from_geometry(geometry: Dict) -> str:
    """
    Get location name from GeoJSON geometry.
    
    Args:
        geometry: GeoJSON geometry object
        
    Returns:
        Location string (e.g., "Nairobi, Kenya") or fallback
    """
    coords = get_centroid_from_geometry(geometry)
    
    if coords:
        lon, lat = coords
        location = reverse_geocode(lat, lon)
        if location:
            return location
        else:
            # Fallback to coordinates
            return f"{lat:.4f}°, {lon:.4f}°"
    
    # Final fallback
    return "Unknown Location"


if __name__ == "__main__":
    # Test with Kenyan coordinates
    logging.basicConfig(level=logging.INFO)
    
    # Test Point
    test_point = {"type": "Point", "coordinates": [36.8219, -1.2921]}
    print(f"Point test: {get_location_from_geometry(test_point)}")
    
    # Test Polygon (Nairobi area)
    test_polygon = {
        "type": "Polygon",
        "coordinates": [[
            [36.7, -1.3],
            [36.9, -1.3],
            [36.9, -1.2],
            [36.7, -1.2],
            [36.7, -1.3]
        ]]
    }
    print(f"Polygon test: {get_location_from_geometry(test_polygon)}")
