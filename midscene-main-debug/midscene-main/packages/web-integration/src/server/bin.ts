#!/usr/bin/env node
import { MidsceneControlServer } from './index';

const port = process.env.PORT ? Number(process.env.PORT) : undefined;

if (port !== undefined && Number.isNaN(port)) {
  throw new Error(`Invalid PORT: ${process.env.PORT}`);
}

const server = new MidsceneControlServer();
Promise.resolve()
  .then(() => server.launch(port))
  .then(() => {
    console.log(
      `Midscene control server is running on http://localhost:${server.port}`,
    );
  });
