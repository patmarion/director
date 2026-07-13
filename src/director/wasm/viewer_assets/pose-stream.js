// PoseStream: WebSocket client that yields pose frames for a streamed scene.
//
// The backend pushes {seq, poses} messages where `poses` maps an object key to
// 16 row-major floats. This class handles connection lifecycle with automatic
// reconnect/backoff and forwards each frame to `onFrame`.

export class PoseStream {
  /**
   * @param {object} cfg
   * @param {string} cfg.url                       WebSocket URL.
   * @param {(poses:Record<string, number[]>, seq:number)=>void} cfg.onFrame
   * @param {(status:string, isError?:boolean)=>void} [cfg.onStatus]
   * @param {number} [cfg.maxBackoffMs]            Reconnect backoff ceiling.
   */
  constructor({ url, onFrame, onStatus, maxBackoffMs = 5000 }) {
    this._url = url;
    this._onFrame = onFrame;
    this._onStatus = onStatus || (() => {});
    this._maxBackoffMs = maxBackoffMs;
    this._backoffMs = 500;
    this._ws = null;
    this._closed = false;
  }

  connect() {
    this._closed = false;
    this._open();
  }

  close() {
    this._closed = true;
    if (this._ws) this._ws.close();
    this._ws = null;
  }

  _open() {
    const ws = new WebSocket(this._url);
    this._ws = ws;

    ws.onopen = () => {
      this._backoffMs = 500;
      this._onStatus("Streaming poses");
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg && msg.poses) this._onFrame(msg.poses, msg.seq);
    };

    ws.onclose = () => {
      if (this._closed) return;
      this._onStatus("Pose stream closed — reconnecting…", true);
      setTimeout(() => this._open(), this._backoffMs);
      this._backoffMs = Math.min(this._backoffMs * 2, this._maxBackoffMs);
    };

    ws.onerror = () => ws.close();
  }
}
