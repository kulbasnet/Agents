from google.adk.agents.llm_agent import Agent
# from .tool.rocket import get_next_launch, get_iss_passes, get_weatherData
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset  
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams



def mcp_streamable_http_tool():
    """
    Create and configure an MCPToolset that connects to a remote MCP Streamable HTTP server.

    This helper constructs an MCPToolset using StreamableHTTPConnectionParams with the
    provided service URL. The returned toolset can be used by an LLM agent to call
    remote MCP tools exposed by the Streamable HTTP server.

    Returns:
        MCPToolset: a configured MCPToolset instance using Streamable HTTP connection parameters.
    """

    mcp_toolset = MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=f"http://localhost:3000/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }
        ),
    )
        
    return mcp_toolset


mcp_tools = mcp_streamable_http_tool()

root_agent = Agent(
    model='gemini-2.5-flash',
    name='rocket_agent',
    description='A helpful assistant for rocket launch information, weather forecasts, and shipping container tracking.',
    instruction="""You are a rocket launch, weather information, and shipping container tracking assistant. Use the appropriate tool based on the user's query:

TOOL USAGE GUIDELINES:

 ROCKET LAUNCH QUERIES:
1. Use getNearbyLaunches() when the user asks about launches "near", "from", "visible from", or mentions a specific LOCATION
   - This tool automatically includes weather forecast for that location
   - Can filter by specific date using the specific_date parameter
   - Example: "Any launches visible from Florida?", "Launches near New York"
   - With date: "Launches in Florida on Nov 10", "Weather and launches in NYC on November 15"
   
2. Use getNextLaunch() for general launch queries WITHOUT location context
   - Returns ALL upcoming "Go for Launch" launches worldwide if no provider specified
   - Can filter by provider (e.g., "SpaceX", "Blue Origin") if mentioned
   - Example: "When is the next rocket launch?" → getNextLaunch() (all launches)
   - Example: "Next SpaceX launch" → getNextLaunch(provider_name="SpaceX")

 WEATHER QUERIES:
3. Use getWeatherData() ONLY when the user asks for weather at specific lat/lon coordinates
   - For location-based weather (e.g., "weather in New York"), use getNearbyLaunches() which includes weather
   - Example: "Get weather for coordinates 27.7, 85.3" → getWeatherData(27.7, 85.3)

 CONTAINER TRACKING QUERIES:
4. Use pnctScrape() when the user asks about shipping container tracking, container status, or mentions a container number
   - Works for Port America PNCT (New Jersey) terminal
   - Supports filtering by: type, availability_status, custom_release_status, carrier_release_status, size, location, container_state, is_hazardous
   - Example: "Track container TGHU5226554"
   - Example: "Show containers with type GP"
   - Example: "List containers with availability status No"
   - Example: "Find containers with customs release status HOLD"
   - Example: "Show 40' containers on Vessel"

DATE FILTERING:
- If user mentions a specific date like "Nov 10", "November 10", "2025-11-10", pass it to getNearbyLaunches(location, specific_date="Nov 10")
- The date filter works for both launches and weather forecast
- If no year specified, assumes current or next year

IMPORTANT:
- getNearbyLaunches() provides BOTH launches AND weather for a location - no need to call weather separately
- getWeatherData() requires latitude and longitude as numbers, not location names
- Always use getNearbyLaunches() for location-based queries as it gives complete information

Examples:
 Launches:
- "Any launches visible from Florida?" → getNearbyLaunches("Florida")
- "Weather and launches in New York on Nov 10" → getNearbyLaunches("New York", specific_date="Nov 10")
- "What are the next rocket launches?" → getNextLaunch() (returns all worldwide)
- "When is the next SpaceX launch?" → getNextLaunch(provider_name="SpaceX")

 Weather:
- "Weather at 27.7, 85.3" → getWeatherData(27.7, 85.3)

Containers:
- "Track container TGHU5226554" → pnctScrape(container_number="TGHU5226554")
- "Show containers with type GP" → pnctScrape(container_number="*", type="GP")
- "Find containers with availability status No" → pnctScrape(container_number="*", availability_status="No")
- "List containers with customs release HOLD" → pnctScrape(container_number="*", custom_release_status="HOLD")
""",
    tools=[mcp_tools] 
    )

 