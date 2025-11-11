# 🚀 Temporal Container Scraping - Usage Guide

## ✅ What's Running Now

You have **3 services** running in the background:

1. **Temporal Server** (localhost:7233) - Workflow orchestrator
2. **Temporal Worker** - Executes the container scraping activities
3. **MCP Server** (localhost:3000) - Exposes tools via HTTP

---

## 📋 Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  User/Agent → MCP Server (localhost:3000)      │
└─────────────────────────────────────────────────┘
                      ↓
         Checks: Is Temporal Connected?
                      ↓
                 ┌─────────┬─────────────┐
                 │   YES   │     NO      │
                 ↓         ↓             ↓
        ┌────────────┐  ┌──────────────────┐
        │  Temporal  │  │  Direct Function │
        │  Workflow  │  │  Call (fallback) │
        └────────────┘  └──────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│  Temporal Worker                                │
│  - Executes pnctScraperActivity                │
│  - Retry logic                                  │
│  - Fault tolerance                              │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│  PNCT API (businquiry.portsamerica.com)        │
│  - Container tracking data                      │
└─────────────────────────────────────────────────┘
```

---

## 🔧 How to Use

### 1. Track a Single Container

```bash
curl --location 'http://localhost:3000/mcp' \
  --header 'Content-Type: application/json' \
  --data '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/call",
    "params": {
      "name": "pnctScrape",
      "arguments": {
        "container_number": "TGHU5226554"
      }
    }
  }'
```

### 2. Search with Filters

```bash
curl --location 'http://localhost:3000/mcp' \
  --header 'Content-Type: application/json' \
  --data '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "tools/call",
    "params": {
      "name": "pnctScrape",
      "arguments": {
        "container_number": "TGHU*",
        "type": "GP",
        "custom_release_status": "HOLD",
        "availability_status": "No"
      }
    }
  }'
```

### 3. Available Filters

- `type` - Container type (e.g., "GP", "HC", "OT")
- `availability_status` - Availability (e.g., "Yes", "No")
- `custom_release_status` - Customs status (e.g., "RELEASED", "HOLD")
- `carrier_release_status` - Carrier status (e.g., "RELEASED", "HOLD")
- `size` - Container size (e.g., "40'", "20'")
- `location` - Location (e.g., "Vessel", "Yard")
- `container_state` - State (e.g., "Inbound", "Outbound")
- `is_hazardous` - Boolean (true/false)

---

## 🎯 Workflow Names (for Temporal UI)

If you open the Temporal UI at http://localhost:8233, you'll see:

- **pnctContainerScraper** - Simple container lookup
- **pnctContainerScraperWithFilters** - Filtered search

---

## 🔄 Managing Services

### Check Running Services
```bash
ps aux | grep -E "(temporal|ts-node|tsx)" | grep -v grep
```

### Stop Services
```bash
# Stop Temporal server
pkill -f "temporal server"

# Stop Temporal worker
pkill -f "ts-node src/worker"

# Stop MCP server
pkill -f "tsx src/index"
```

### Restart Services
```bash
# 1. Start Temporal server
temporal server start-dev &

# 2. Start Temporal worker (in Temporal/my-app/)
cd /home/kul/Desktop/AI-Agent/Temporal/my-app
npm start &

# 3. Start MCP server (in MCP/)
cd /home/kul/Desktop/AI-Agent/MCP
npm run dev &
```

---

## 🌟 Benefits of Using Temporal

1. **Automatic Retries** - Failed API calls retry with exponential backoff
2. **Fault Tolerance** - Workflows resume from last checkpoint if worker crashes
3. **Observability** - View workflow execution in Temporal UI
4. **State Management** - Temporal tracks execution state automatically
5. **Scalability** - Add more workers to handle more requests

---

## 📊 Temporal UI

Access the web interface at: **http://localhost:8233**

Here you can:
- View all workflow executions
- See execution history
- Check for failed workflows
- Monitor performance metrics

---

## 🐛 Troubleshooting

### MCP Server says "Temporal: NOT CONNECTED"
```bash
# Check if Temporal server is running
temporal server health

# If not, start it
temporal server start-dev &
```

### Worker not processing workflows
```bash
# Rebuild the worker
cd /home/kul/Desktop/AI-Agent/Temporal/my-app
npm run build
npm start
```

### Check MCP server logs
```bash
# View background process logs
jobs
fg %1  # Brings job 1 to foreground to see logs
```

---

## 🎓 What You've Built

✅ **Temporal Workflows** - Container scraping orchestration  
✅ **Temporal Activities** - API scraping with retry logic  
✅ **MCP Server Integration** - Seamless fallback mechanism  
✅ **Filter Support** - Advanced container search  
✅ **Fault Tolerance** - Automatic recovery from failures  

---

**Your container scraping is now production-ready with enterprise-grade orchestration!** 🚀

