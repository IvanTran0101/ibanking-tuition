import { useEffect, useMemo, useRef, useState } from "react";
import { verifyOtp } from "../api/otp";
import styles from "./OTPForm.module.css";

const DEFAULT_TTL_SEC = Number((import.meta && import.meta.env && import.meta.env.VITE_OTP_TTL_SEC) ?? 300);
const DEFAULT_COOLDOWN_MS = Number((import.meta && import.meta.env && import.meta.env.VITE_OTP_ATTEMPT_COOLDOWN_MS) ?? 5000);

function formatDuration(ms) {
  if (ms <= 0) return "00:00";
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export default function OTPForm({
  paymentId,
  expiresAt,
  onVerified,
  onExpired,
  attemptCooldownMs = DEFAULT_COOLDOWN_MS,
}) {
  const fallbackExpires = useMemo(() => Date.now() + DEFAULT_TTL_SEC * 1000, []);
  const effectiveExpiry = expiresAt || fallbackExpires;

  const [otpCode, setOtpCode] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [cooldownUntil, setCooldownUntil] = useState(0);
  const expiredNotified = useRef(false);

  useEffect(() => {
    setOtpCode("");
    setStatus("");
    setError("");
    setCooldownUntil(0);
    expiredNotified.current = false;
  }, [paymentId, effectiveExpiry]);

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, []);

  const remainingMs = Math.max(0, effectiveExpiry - now);
  const expired = remainingMs <= 0;
  const cooldownRemaining = Math.max(0, cooldownUntil - now);

  useEffect(() => {
    if (expired && !expiredNotified.current) {
      expiredNotified.current = true;
      onExpired?.(paymentId);
    }
  }, [expired, onExpired, paymentId]);

  async function handleSubmit(e) {
    e?.preventDefault?.();
    e?.stopPropagation?.();
    if (!otpCode.trim()) return setError("Please enter the OTP sent to you.");
    if (expired) return setError("OTP expired. Request a new OTP.");
    if (cooldownRemaining > 0) {
      return setError(`Too many attempts. Please wait ${formatDuration(cooldownRemaining)} before retrying.`);
    }

    setVerifying(true);
    setError("");
    setStatus("");

    try {
      await verifyOtp({ payment_id: paymentId, otp_code: otpCode.trim() });
      setStatus("OTP verified! Payment authorization is in progress.");
      onVerified?.(paymentId);
    } catch (err) {
      setError(err?.message || "Incorrect OTP. Please try again.");
      setCooldownUntil(Date.now() + attemptCooldownMs);
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h3>Step 4 · Confirm OTP</h3>
        <div className={expired ? styles.expired : styles.timer}>
          Expires in: <span>{formatDuration(remainingMs)}</span>
        </div>
      </div>

      <p className={styles.description}>
        Enter the 6-digit OTP sent to your registered email. This protects your account and prevents unauthorized tuition payments.
      </p>

      <label className={styles.label}>
        Payment ID
        <input className={styles.input} value={paymentId} disabled />
      </label>

      <label className={styles.label}>
        OTP Code
        <input
          className={styles.input}
          value={otpCode}
          onChange={(e) => setOtpCode(e.target.value.replace(/\s+/g, ""))}
          maxLength={10}
          placeholder="Enter 6-digit code"
          disabled={verifying || expired || cooldownRemaining > 0}
          required
        />
      </label>

      {error && <div className={styles.error}>{error}</div>}
      {status && <div className={styles.success}>{status}</div>}
      {cooldownRemaining > 0 && (
        <div className={styles.cooldown}>Retry allowed in {formatDuration(cooldownRemaining)}.</div>
      )}

      <button
        className={styles.button}
        type="button"
        disabled={verifying || expired || cooldownRemaining > 0}
        onClick={handleSubmit}
      >
        {verifying ? "Verifying..." : "Submit OTP"}
      </button>
    </div>
  );
}
