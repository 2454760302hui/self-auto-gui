import type { Server } from 'node:http';
import cors from 'cors';
import express from 'express';
import { LogStream } from './log-stream';
import { createServerRoutes } from './routes';
import { SessionManager } from './session-manager';

const defaultPort = 5801;

const errorHandler = (err: any, req: any, res: any, next: any) => {
  console.error(err);
  res.status(500).json({
    error: err?.message || String(err),
  });
};

export class MidsceneControlServer {
  app: express.Application;
  server?: Server;
  port?: number | null;
  sessionManager: SessionManager;
  logStream: LogStream;

  constructor() {
    this.app = express();
    this.sessionManager = new SessionManager();
    this.logStream = new LogStream();
  }

  async launch(port = defaultPort) {
    this.app.use(
      cors({
        origin: '*',
        credentials: true,
      }),
    );

    this.app.use('/api', createServerRoutes(this.sessionManager, this.logStream));
    this.app.use(errorHandler);

    return new Promise<this>((resolve) => {
      this.server = this.app.listen(port, () => {
        this.port = port;
        resolve(this);
      });
    });
  }

  close() {
    if (this.server) {
      return this.server.close();
    }
  }
}

export default MidsceneControlServer;
