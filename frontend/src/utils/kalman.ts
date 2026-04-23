/**
 * 1-D Kalman filter for GPS coordinate smoothing.
 * Instantiate one per axis (lat, lng).
 */
export class KalmanFilter {
  private Q = 0.00001; // process noise
  private R = 0.001;   // measurement noise
  private P = 1;       // initial error covariance
  private x = 0;       // state estimate

  update(measurement: number): number {
    this.P += this.Q;
    const K = this.P / (this.P + this.R);
    this.x += K * (measurement - this.x);
    this.P *= 1 - K;
    return this.x;
  }

  reset(value: number): void {
    this.x = value;
    this.P = 1;
  }
}
