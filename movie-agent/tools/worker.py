import requests
from typing import Optional, Dict, Any, List
import re


def search_movie_by_title(title: str) -> Optional[str]:
    """
    Search for a movie by title and return the first matching IMDB ID.
    
    Args:
        title: Movie title to search for
    
    Returns:
        IMDB ID of the first matching movie, or None if not found
    """
    try:
        url = f"https://imdb.iamidiotareyoutoo.com/search?q={title}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('ok') and data.get('description'):
            # Return the first result's IMDB ID
            return data['description'][0].get('#IMDB_ID')
        
        return None
    except Exception as e:
        print(f"Search error: {e}")
        return None


def discover(
    query: str,
    year: Optional[int] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None,
    min_rating: Optional[float] = None,
    genre_filter: Optional[str] = None,
    fetch_details: bool = False,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Discover movies or TV shows by search query with filters.
    
    NOTE: The API searches by TITLE keywords, not by genre or production company.
    For better results with franchise queries (Marvel, DC, Star Wars):
    - Use specific titles: "Avengers", "Iron Man", "Batman", "Star Wars"
    - Set fetch_details=True to get genre info and filter
    - Use genre_filter to filter by genre after fetching details
    
    Example queries:
    - "Avengers" → finds Avengers movies
    - "Korean" + genre_filter="Thriller" → Korean + Thriller genre
    - "Action" + fetch_details=True → gets detailed genre info
    
    Args:
        query: Search query (e.g., "Avengers", "Korean", "Inception")
        year: Specific year (e.g., 2020)
        year_start: Start of year range (e.g., 2020)
        year_end: End of year range (e.g., 2024)
        min_rating: Minimum IMDB rating (e.g., 7.5)
        genre_filter: Filter by genre (e.g., "Action", "Thriller") - requires fetch_details=True
        fetch_details: Fetch full details for each movie (slower but more accurate)
        max_results: Maximum number of results to return (default: 10)
    
    Returns:
        List of matching movies with their details
    """
    try:
        # Make API request for search results
        url = f"https://imdb.iamidiotareyoutoo.com/search?q={query}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('ok') or not data.get('description'):
            return []
        
        results = data['description']
        filtered_results = []
        
        # Filter and fetch details for each movie
        for movie in results[:30]:  # Check more movies to account for filtering
            # Year filter
            movie_year = movie.get('#YEAR')
            
            # Skip if no year data when year filter is specified
            if (year or year_start or year_end) and movie_year is None:
                continue
            
            if year and movie_year != year:
                continue
            
            if year_start and year_end:
                if not (year_start <= movie_year <= year_end):
                    continue
            
            # Get detailed info if we need to filter by rating or genre
            imdb_id = movie.get('#IMDB_ID')
            
            if (min_rating or genre_filter or fetch_details) and imdb_id:
                # Fetch detailed info to get rating
                detail_url = f"https://imdb.iamidiotareyoutoo.com/search?tt={imdb_id}"
                try:
                    detail_response = requests.get(detail_url, timeout=10)
                    detail_data = detail_response.json()
                    
                    if detail_data.get('ok') and 'short' in detail_data:
                        short = detail_data['short']
                        
                        # Check rating filter
                        rating = 0
                        if 'aggregateRating' in short:
                            rating = short['aggregateRating'].get('ratingValue', 0)
                            if min_rating and rating < min_rating:
                                continue
                        elif min_rating:
                            # No rating data but rating filter is set
                            continue
                        
                        # Check genre filter
                        genres = short.get('genre', [])
                        if genre_filter:
                            # Check if the genre_filter is in any of the genres (case-insensitive)
                            genre_match = any(genre_filter.lower() in g.lower() for g in genres)
                            if not genre_match:
                                continue
                        
                        # Add detailed movie data
                        movie_data = {
                            'title': short.get('name', movie.get('#TITLE')),
                            'year': movie_year,
                            'imdb_id': imdb_id,
                            'rating': rating if rating > 0 else 'N/A',
                            'rating_count': short.get('aggregateRating', {}).get('ratingCount', 0) if 'aggregateRating' in short else 0,
                            'rank': movie.get('#RANK', 'N/A'),
                            'actors': movie.get('#ACTORS', 'N/A'),
                            'url': short.get('url', movie.get('#IMDB_URL')),
                            'image': short.get('image', movie.get('#IMG_POSTER')),
                            'genre': genres,
                            'description': short.get('description', 'N/A'),
                        }
                        filtered_results.append(movie_data)
                        
                        if len(filtered_results) >= max_results:
                            break
                except:
                    continue
            else:
                # Simple data without rating filter
                movie_data = {
                    'title': movie.get('#TITLE', 'N/A'),
                    'year': movie_year,
                    'imdb_id': imdb_id,
                    'rank': movie.get('#RANK', 'N/A'),
                    'actors': movie.get('#ACTORS', 'N/A'),
                    'url': movie.get('#IMDB_URL', 'N/A'),
                    'image': movie.get('#IMG_POSTER', 'N/A'),
                }
                filtered_results.append(movie_data)
                
                if len(filtered_results) >= max_results:
                    break
        
        return filtered_results
    
    except Exception as e:
        print(f"Discover error: {e}")
        return []


def get_movie_info(movie_input: str) -> Dict[str, Any]:
    """
    Fetch detailed movie information from IMDB API.
    Accepts either an IMDB ID (e.g., 'tt2250912') or a movie title (e.g., 'Spider-Man').
    
    Args:
        movie_input: The IMDB ID or movie title
    
    Returns:
        Dictionary containing movie information including title, rating, description, etc.
    """
    try:
        # Check if input is an IMDB ID (starts with 'tt' followed by digits)
        if re.match(r'^tt\d+$', movie_input):
            imdb_id = movie_input
        else:
            # Search for the movie by title
            imdb_id = search_movie_by_title(movie_input)
            if not imdb_id:
                return {
                    'error': f'Movie not found with title: {movie_input}',
                    'query': movie_input
                }
        
        # API endpoint for detailed info
        url = f"https://imdb.iamidiotareyoutoo.com/search?tt={imdb_id}"
        
        # Make the request
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        if not data.get('ok'):
            return {
                'error': 'Movie not found',
                'imdb_id': imdb_id
            }
        
        # Extract useful information from the response
        movie_data = {}
        
        # Basic info from 'short' section
        if 'short' in data:
            short = data['short']
            movie_data['title'] = short.get('name', 'N/A')
            movie_data['description'] = short.get('description', 'N/A')
            movie_data['image'] = short.get('image', 'N/A')
            movie_data['url'] = short.get('url', 'N/A')
            movie_data['genre'] = short.get('genre', [])
            movie_data['content_rating'] = short.get('contentRating', 'N/A')
            movie_data['date_published'] = short.get('datePublished', 'N/A')
            
            # Rating information
            if 'aggregateRating' in short:
                rating = short['aggregateRating']
                movie_data['rating'] = rating.get('ratingValue', 'N/A')
                movie_data['rating_count'] = rating.get('ratingCount', 'N/A')
        
        # Detailed info from 'top' section
        if 'top' in data:
            top = data['top']
            movie_data['imdb_id'] = top.get('id', imdb_id)
            
            # Title information
            if 'titleText' in top:
                movie_data['title'] = top['titleText'].get('text', movie_data.get('title', 'N/A'))
            
            # Release year
            if 'releaseYear' in top:
                movie_data['release_year'] = top['releaseYear'].get('year', 'N/A')
            
            # Runtime
            if 'runtime' in top and 'displayableProperty' in top['runtime']:
                runtime_display = top['runtime']['displayableProperty']['value'].get('plainText', 'N/A')
                movie_data['runtime'] = runtime_display
            
            # Certificate/Rating
            if 'certificate' in top:
                movie_data['certificate'] = top['certificate'].get('rating', 'N/A')
            
            # Plot summary
            if 'plot' in top and 'plotText' in top['plot']:
                movie_data['plot'] = top['plot']['plotText'].get('plainText', movie_data.get('description', 'N/A'))
            
            # Production budget
            if 'productionBudget' in top and 'budget' in top['productionBudget']:
                budget = top['productionBudget']['budget']
                movie_data['budget'] = f"${budget.get('amount', 0):,} {budget.get('currency', 'USD')}"
            
            # Box office
            if 'worldwideGross' in top and 'total' in top['worldwideGross']:
                gross = top['worldwideGross']['total']
                movie_data['worldwide_gross'] = f"${gross.get('amount', 0):,} {gross.get('currency', 'USD')}"
            
            # Countries
            if 'countriesDetails' in top and 'countries' in top['countriesDetails']:
                countries = [c.get('text', '') for c in top['countriesDetails']['countries']]
                movie_data['countries'] = countries
            
            # Keywords
            if 'keywords' in top and 'edges' in top['keywords']:
                keywords = [edge['node'].get('text', '') for edge in top['keywords']['edges']]
                movie_data['keywords'] = keywords
        
        return movie_data
    
    except requests.exceptions.RequestException as e:
        return {
            'error': f'Failed to fetch movie data: {str(e)}',
            'imdb_id': imdb_id
        }
    except Exception as e:
        return {
            'error': f'Error processing movie data: {str(e)}',
            'imdb_id': imdb_id
        }


def format_movie_info(movie_data: Dict[str, Any]) -> str:
    """
    Format movie data into a readable string.
    
    Args:
        movie_data: Dictionary containing movie information
    
    Returns:
        Formatted string with movie details
    """
    if 'error' in movie_data:
        return f"❌ Error: {movie_data['error']}"
    
    output = []
    output.append("=" * 60)
    output.append(f"🎬 {movie_data.get('title', 'Unknown Title')}")
    output.append("=" * 60)
    
    if movie_data.get('release_year'):
        output.append(f"📅 Year: {movie_data['release_year']}")
    
    if movie_data.get('rating'):
        output.append(f"⭐ Rating: {movie_data['rating']}/10 ({movie_data.get('rating_count', 0):,} votes)")
    
    if movie_data.get('runtime'):
        output.append(f"⏱️  Runtime: {movie_data['runtime']}")
    
    if movie_data.get('certificate'):
        output.append(f"🔞 Rating: {movie_data['certificate']}")
    
    if movie_data.get('genre'):
        output.append(f"🎭 Genre: {', '.join(movie_data['genre'])}")
    
    if movie_data.get('description'):
        output.append(f"\n📝 Description:\n{movie_data['description']}")
    
    if movie_data.get('budget'):
        output.append(f"\n💰 Budget: {movie_data['budget']}")
    
    if movie_data.get('worldwide_gross'):
        output.append(f"💵 Box Office: {movie_data['worldwide_gross']}")
    
    if movie_data.get('countries'):
        output.append(f"\n🌍 Countries: {', '.join(movie_data['countries'])}")
    
    if movie_data.get('keywords'):
        output.append(f"🏷️  Keywords: {', '.join(movie_data['keywords'][:5])}")
    
    if movie_data.get('url'):
        output.append(f"\n🔗 IMDB: {movie_data['url']}")
    
    output.append("=" * 60)
    
    return "\n".join(output)
