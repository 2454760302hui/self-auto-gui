import type { Response } from 'express';

export interface TaskEvent {
  taskId: string;
  sessionId: string;
  type:
    | 'task-started'
    | 'step'
    | 'snapshot'
    | 'dump-updated'
    | 'task-finished'
    | 'task-failed';
  message: string;
  timestamp: number;
  status?: 'pending' | 'running' | 'success' | 'error';
  result?: any;
  error?: string;
  reportFile?: string | null;
  dump?: string;
  detail?: any;
  taskType?: string;
}

interface TaskEventStream {
  events: TaskEvent[];
  listeners: Set<Response>;
}

export class LogStream {
  private streams = new Map<string, TaskEventStream>();

  private ensure(taskId: string): TaskEventStream {
    let stream = this.streams.get(taskId);
    if (!stream) {
      stream = {
        events: [],
        listeners: new Set(),
      };
      this.streams.set(taskId, stream);
    }
    return stream;
  }

  publish(event: TaskEvent) {
    const stream = this.ensure(event.taskId);
    stream.events.push(event);
    const payload = `data: ${JSON.stringify(event)}\n\n`;
    stream.listeners.forEach((listener) => listener.write(payload));
  }

  publishStep(
    taskId: string,
    sessionId: string,
    message: string,
    detail?: any,
  ) {
    this.publish({
      taskId,
      sessionId,
      type: 'step',
      message,
      timestamp: Date.now(),
      status: 'running',
      detail,
    });
  }

  subscribe(taskId: string, res: Response) {
    const stream = this.ensure(taskId);
    stream.listeners.add(res);

    stream.events.forEach((event) => {
      res.write(`data: ${JSON.stringify(event)}\n\n`);
    });

    const unsubscribe = () => {
      stream.listeners.delete(res);
      if (stream.listeners.size === 0 && this.isFinished(stream.events)) {
        this.streams.delete(taskId);
      }
    };

    res.on('close', unsubscribe);
    res.on('finish', unsubscribe);
  }

  private isFinished(events: TaskEvent[]) {
    const lastEvent = events[events.length - 1];
    return Boolean(
      lastEvent &&
        (lastEvent.type === 'task-finished' || lastEvent.type === 'task-failed'),
    );
  }
}
