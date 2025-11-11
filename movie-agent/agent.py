from google.adk.agents.llm_agent import Agent
from .tools.worker import get_movie_info, discover

root_agent = Agent(
    model='gemini-2.5-flash',
    name='movie_agent',
    description='A helpful movie information assistant that can search for movies and discover movies by genre, year, language, and rating.',
    instruction='''Help users get information about movies. You have two tools:
    
1. get_movie_info: Use this when users ask about a specific movie by title or IMDB ID.
   Example: get_movie_info("Spider-Man")

2. discover: Search and filter movies. IMPORTANT: The API searches by TITLE keywords.
   
   Parameters:
   - query: Search keywords in movie titles (e.g., "Avengers", "Korean", "Inception")  
   - year/year_start/year_end: Year filters
   - min_rating: Minimum IMDB rating
   - genre_filter: Filter by genre (e.g., "Action", "Thriller")
   - fetch_details: Set True to get full details including genres
   - max_results: Number of results (default: 10)
   
Examples:
- "Marvel movies" → Use specific titles since API searches titles, not studios
  → discover(query="Avengers", fetch_details=True)
  → discover(query="Iron Man", fetch_details=True)  
  → discover(query="Thor", fetch_details=True)
  
- "Top Korean thrillers from 2020-2024 with rating ≥7.5"
  → discover(query="Korean", year_start=2020, year_end=2024, min_rating=7.5, genre_filter="Thriller", fetch_details=True)
  
- "Tell me about Spider-Man"
  → get_movie_info("Spider-Man")
  
- "Action movies from 2023"
  → discover(query="action", year=2023, genre_filter="Action", fetch_details=True)

NOTE: For franchise movies (Marvel, DC, Star Wars), use specific movie titles like "Avengers", "Batman", "Star Wars" instead of the studio name.
''',
    tools=[get_movie_info, discover]
)