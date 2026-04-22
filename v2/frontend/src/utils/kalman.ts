/**
 * 1-D Kalman Filter for GPS coordinate smoothing.
 *
 * Use one instance per axis (lat, lng). When a real GPS measurement arrives,
 * call update() to blend it with the dead-reckoned estimate. The result is a
 * smoothly interpolated value — no teleportation, no jarring jumps.
 *
 * Tuning:
 *   Q (process noise)    — how much the true value can drift per tick.
 *                          Lower Q → trusts the model more → smoother but slower to react.
 *   R (measurement noise) — how noisy the GPS sensor is.
 *                          Lower R → trusts the GPS more → reacts faster but jittery.
 */
export class KalmanFilter {
  private Q: number; // process noise variance
  private R: number; // measurement noise variance
  private P: number; // estimate error covariance
  private x: number; // current state estimate

  constructor(initialValue: number, Q = 0.00001, R = 0.001) {
    this.Q = Q;
    this.R = R;
    this.P = 1;
    this.x = initialValue;
  }

  update(measurement: number): number {
    // Predict step: propagate error covariance
    this.P += this.Q;

    // Update step: compute Kalman gain and correct estimate
    const K = this.P / (this.P + this.R); // Kalman gain (0–1)
    this.x += K * (measurement - this.x);  // weighted correction
    this.P *= 1 - K;                        // updated error covariance

    return this.x;
  }

  get estimate(): number {
    return this.x;
  }

  reset(value: number): void {
    this.x = value;
    this.P = 1;
  }
}
