import { Connection, Client } from '@temporalio/client';
import { nanoid } from 'nanoid';

let temporalClient: Client | null = null;
let temporalConnection: Connection | null = null;

/**
 * Initialize Temporal client connection
 */
export async function initializeTemporalClient(): Promise<Client> {
  if (temporalClient) {
    return temporalClient;
  }

  try {
    temporalConnection = await Connection.connect({
      address: 'localhost:7233',
    });

    temporalClient = new Client({
      connection: temporalConnection,
    });

    console.log('✅ Temporal client connected');
    return temporalClient;
  } catch (error) {
    console.error('❌ Failed to connect to Temporal:', error);
    throw error;
  }
}

/**
 * Execute a Temporal workflow by name and wait for result
 * The workflow must be registered in the Temporal worker (in /Temporal/my-app/)
 */
export async function executeTemporalWorkflow<T = any>(
  workflowType: string,
  args: any[]
): Promise<T> {
  const client = await initializeTemporalClient();
  const workflowId = `${workflowType}-${nanoid()}`;

  try {
    console.log(`🚀 Executing workflow: ${workflowType}`);

    // Start workflow by name (workflows are registered in Temporal worker, not here)
    const handle = await client.workflow.start(workflowType, {
      taskQueue: 'hello-world',
      args,
      workflowId,
      workflowExecutionTimeout: '5 minutes',
    });

    // Wait for result
    const result = await handle.result() as T;

    console.log(`✅ Workflow completed: ${workflowId}`);
    return result;
  } catch (error) {
    console.error(`❌ Workflow failed:`, error);
    throw error;
  }
}

/**
 * Check if Temporal server is available
 */
export async function isTemporalAvailable(): Promise<boolean> {
  try {
    await initializeTemporalClient();
    return true;
  } catch {
    return false;
  }
}

