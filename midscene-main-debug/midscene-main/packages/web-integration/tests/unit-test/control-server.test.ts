import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { MidsceneControlServer } from '@/server';

describe('Control Server', () => {
  let server: MidsceneControlServer;
  let serverBase: string;

  beforeAll(async () => {
    server = new MidsceneControlServer();
    await server.launch();
    serverBase = `http://localhost:${server.port}/api`;
  });

  afterAll(async () => {
    await server.close();
  });

  it('returns status', async () => {
    const response = await fetch(`${serverBase}/status`);
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: 'ok' });
  });

  it('manages sessions and tasks in memory', async () => {
    const sessionsResponse = await fetch(`${serverBase}/sessions`);
    expect(sessionsResponse.status).toBe(200);
    expect(await sessionsResponse.json()).toEqual([]);

    const createResponse = await fetch(`${serverBase}/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    expect(createResponse.status).toBe(500);

    const listResponse = await fetch(`${serverBase}/sessions`);
    expect(listResponse.status).toBe(200);
    expect(await listResponse.json()).toEqual([]);
  });

  it('rejects unsupported task types', async () => {
    const response = await fetch(`${serverBase}/tasks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sessionId: 'missing-session',
        type: 'invalid',
        prompt: 'noop',
      }),
    });

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      error: 'Unsupported task type: invalid',
    });
  });
});
