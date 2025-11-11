import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";
import { getNextLaunch, getNearbyLaunches, geocodeLocation, getWeatherData } from "./Helper.js";
import { isTemporalAvailable, executeTemporalWorkflow } from "./temporal-client.js";
import express from "express";

const app = express();

// Create server instance
const server = new McpServer({
  name: "Rocket Agent",
  version: "1.0.0",
  capabilities: {
    resources: {},
    tools: {},
  },
});

server.tool(
    "getNextLaunch",
    "Get upcoming rocket launches worldwide, optionally filtered by provider",
    {
      provider_name: z.string().min(3).optional().describe("Optional: Rocket Company Name to filter (e.g. 'SpaceX', 'Blue Origin'). If not provided, returns all upcoming launches."),
    },
    async ({provider_name}) => {
      const launches = await getNextLaunch("Go", provider_name);
      return {
        content: [
            {
                type: "text",
                text: JSON.stringify(launches, null, 2),
            },
        ],
        structuredContent: { launches } as any,
      };
    }
  );

server.tool(
  "getWeatherData",
  "Get Weather Data",
  {
    latitude: z.number().describe("Latitude of the location"),
    longitude: z.number().describe("Longitude of the location"),
    days: z.number().describe("Number of days to get weather data for"),
  },
  async ({latitude, longitude, days}) => {
    const weatherData = await getWeatherData(latitude, longitude, days);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(weatherData, null, 2),
        },
      ],
      structuredContent: { weatherData } as any,
    };
  }
);

server.tool(
    "getNearbyLaunches",
    "Get nearby visible Rocket Launches and weather for a location, optionally filtered by date",
    {
      location: z.string().min(3).max(50).describe("Clear location (e.g. Florida, New York, Patan)"),
      specific_date: z.string().optional().describe("Optional specific date to filter (e.g. 'Nov 10', '2025-11-10', 'November 10, 2025')"),
    },
    async ({location, specific_date}) => {
      const result = await getNearbyLaunches(location, 1000, 7, 10, specific_date);
      return {
        content: [
            {
                type: "text",
                text: JSON.stringify(result, null, 2),
            },
        ],
        structuredContent: result as any,
      };
    }
);

server.tool(
  "geocode_location",
  "Geocode a location",
  {
    name_of_location: z.string().min(3).max(50).describe("Geocode a location (e.g. Florida, New York, Patan)"),
  },
  async ({name_of_location}) => {
    const location = await geocodeLocation(name_of_location);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(location, null, 2),
        },
      ],
      structuredContent: (location || { error: "Location not found" }) as any,
    };
  }
);

server.tool(
  "pnctScrape",
  "[Temporal-only] Track shipping containers at Port America PNCT (New Jersey) terminal. Executes via Temporal workflows for fault-tolerant scraping with automatic retries. Can search by container number and filter by various criteria.",
  {
    container_number: z.string().optional().describe("Container number to track (e.g. 'TGHU5226554'). Use '*' as wildcard if supported by API."),
    type: z.string().optional().describe("Filter by container type (e.g. 'GP', 'HC', 'OT')"),
    availability_status: z.string().optional().describe("Filter by availability status (e.g. 'No', 'Yes')"),
    custom_release_status: z.string().optional().describe("Filter by customs release status (e.g. 'RELEASED', 'HOLD')"),
    carrier_release_status: z.string().optional().describe("Filter by carrier release status (e.g. 'RELEASED', 'HOLD')"),
    size: z.string().optional().describe("Filter by container size (e.g. '40\\', '20\\')"),
    location: z.string().optional().describe("Filter by location (e.g. 'Vessel', 'Yard')"),
    container_state: z.string().optional().describe("Filter by container state (e.g. 'Inbound', 'Outbound')"),
    is_hazardous: z.boolean().optional().describe("Filter by hazardous status (true/false)"),
  },
  async ({
    container_number,
    type,
    availability_status,
    custom_release_status,
    carrier_release_status,
    size,
    location,
    container_state,
    is_hazardous
  }) => {
    const filters: any = {};
    if (type) filters.type = type;
    if (availability_status) filters.availabilityStatus = availability_status;
    if (custom_release_status) filters.customReleaseStatus = custom_release_status;
    if (carrier_release_status) filters.carrierReleaseStatus = carrier_release_status;
    if (size) filters.size = size;
    if (location) filters.location = location;
    if (container_state) filters.containerState = container_state;
    if (is_hazardous !== undefined) filters.isHazardous = is_hazardous;

    const hasFilters = Object.keys(filters).length > 0;

    // Execute via Temporal workflow only
    let containerInfo;
    if (hasFilters) {
      console.log(`📋 Executing Temporal workflow: pnctContainerScraperWithFilters`);
      containerInfo = await executeTemporalWorkflow('pnctContainerScraperWithFilters', [container_number, filters]);
    } else {
      console.log(`📋 Executing Temporal workflow: pnctContainerScraper`);
      containerInfo = await executeTemporalWorkflow('pnctContainerScraper', [container_number]);
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(containerInfo, null, 2),
        },
      ],
      structuredContent: containerInfo as any,
    };
  }
);


// MCP endpoint
app.post('/mcp', async (req, res) => {
    // Create a new transport for each request to prevent request ID collisions
    const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined,
        enableJsonResponse: true
    });

    res.on('close', () => {
        transport.close();
    });

    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
});

// Start server
const port = 3000;
app.listen(port, async () => {
    console.log(`\n🚀 Rocket Agent MCP Server running on http://localhost:${port}`);
    console.log(`   Version: 1.0.0`);
    console.log(`   Environment: development`);
    console.log(`   MCP Endpoint: /mcp\n`);
    
    // Check Temporal connection (required for pnctScrape tool)
    console.log('🔍 Checking Temporal server connection...');
    const temporalAvailable = await isTemporalAvailable();
    
    if (temporalAvailable) {
        console.log('✅ Temporal server: CONNECTED');
        console.log('   Address: localhost:7233');
        console.log('   Workflows: ENABLED');
        console.log('   Container scraping: ACTIVE\n');
    } else {
        console.error('❌ Temporal server: NOT CONNECTED');
        console.error('   Error: pnctScrape tool requires Temporal');
        console.error('   Please start Temporal server: temporal server start-dev');
        console.error('   Exiting...\n');
        process.exit(1);
    }
}).on('error', error => {
    console.error('❌ Server startup error', error);
    process.exit(1);
});