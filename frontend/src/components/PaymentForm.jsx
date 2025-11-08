import { useEffect, useMemo, useRef, useState } from "react";
import { getAccountMe } from "../api/account";
import { getTuitionByStudentId } from "../api/tuition";
import { initPayment } from "../api/payment";
import { logout } from "../api/auth";
import styles from "./PaymentForm.module.css";
import OTPForm from "./OTPForm";

const OTP_TTL_MS = Number((import.meta && import.meta.env && import.meta.env.VITE_OTP_TTL_SEC) ?? 300) * 1000;

export default function PaymentForm({ onLoggedOut }) {
  const [me, setMe] = useState(null);
  const [studentId, setStudentId] = useState("");
  const lookupTimer = useRef(null);
  const [studentName, setStudentName] = useState("");
  const [tuitionAmount, setTuitionAmount] = useState("");
  const [tuitionId, setTuitionId] = useState("");
  const [termNo, setTermNo] = useState("");
  const [agree, setAgree] = useState(false);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [otpContext, setOtpContext] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getAccountMe();
        setMe(data);
      } catch (e) {
        setMsg("Failed to load profile. Please re-login.");
      }
    })();
  }, []);

  async function handleLookup() {
    const sid = (studentId || "").trim();
    if (!sid) return;
    setLoading(true);
    setMsg("");
    try {
      const resp = await getTuitionByStudentId(sid);
      setStudentId(resp.student_id || sid);
      setTuitionId(resp.tuition_id);
      setStudentName(resp.full_name || "");
      setTermNo(resp.term_no || "");
      setTuitionAmount(String(resp.amount_due ?? ""));
    } catch (e) {
      setMsg(e?.message || "Tuition not found for student id");
      setTuitionId("");
      setStudentName("");
      setTermNo("");
      setTuitionAmount("");
    } finally {
      setLoading(false);
    }
  }

  async function handleGetOtp(e) {
    e.preventDefault();
    if (!agree) return setMsg("Please accept the terms.");
    const trimmedStudentId = studentId.trim();
    if (!trimmedStudentId) return setMsg("Please enter a valid student ID and lookup tuition.");
    if (!tuitionId || !tuitionAmount) return setMsg("Please lookup tuition first.");

    setOtpContext(null);
    setLoading(true);
    setMsg("");

    try {
      const res = await initPayment({
        tuition_id: tuitionId,
        amount: Number(tuitionAmount),
        term_no: termNo || undefined,
        student_id: trimmedStudentId,
      });
      const expiresAt = Date.now() + OTP_TTL_MS;
      setOtpContext({ paymentId: res.payment_id, expiresAt });
      setMsg(`OTP sent for payment ${res.payment_id}. Enter it below within ${Math.floor(OTP_TTL_MS / 60000)} minutes.`);
    } catch (e) {
      setMsg(e?.message || "Failed to start payment");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    setOtpContext(null);
    logout();
    onLoggedOut?.();
  }

  function handleOtpVerified(pid) {
    setOtpContext(null);
    setMsg(`OTP verified!. Payment authorization is in progress. Please reload the page`);
  }

  function handleOtpExpired(pid) {
    setOtpContext(null);
    setMsg(`OTP has expired. Request a new OTP to continue.`);
  }

  const balanceFmt = useMemo(() => {
    const v = Number(me?.balance ?? 0);
    return v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }, [me]);

  // Debounce: after 5 seconds since last input, trigger lookup
  useEffect(() => {
    if (lookupTimer.current) clearTimeout(lookupTimer.current);
    if (!studentId) return;
    lookupTimer.current = setTimeout(() => handleLookup(), 5000);
    return () => {
      if (lookupTimer.current) clearTimeout(lookupTimer.current);
    };
  }, [studentId]);

  return (
    <form className={styles.card} onSubmit={handleGetOtp}>
      <h2 className={styles.title}>Tuition Payment</h2>

      {msg && (
        <div
          className={styles.info}
          style={
            msg.startsWith("OTP verified!")
              ? { color: "#0f5132" }
              : undefined
          }
        >
          {msg}
        </div>
      )}

      <h3>1. Payer Information</h3>

      <label className={styles.label}>
        Full Name
        <input className={styles.input} value={me?.full_name || ""} disabled />
      </label>

      <label className={styles.label}>
        Phone Number
        <input className={styles.input} value={me?.phone_number || ""} disabled />
      </label>

      <label className={styles.label}>
        Email
        <input className={styles.input} value={me?.email || ""} disabled />
      </label>

      <h3>2. Tuition Information</h3>

      <label className={styles.label}>
        Student ID (MSSV)
        <div className={styles.row}>
          <input
            className={styles.input}
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
            placeholder="Enter student code (e.g., 523K0017)"
          />
        </div>
      </label>

      <label className={styles.label}>
        Student Name
        <input className={styles.input} value={studentName} onChange={(e) => setStudentName(e.target.value)} disabled/>
      </label>

      <label className={styles.label}>
        Tuition Amount (VND)
        <input className={styles.input} value={tuitionAmount} onChange={(e) => setTuitionAmount(e.target.value)} disabled/>
      </label>

      <h3>3. Payment Information</h3>

      <div className={styles.balance}>
        <strong>Available Balance:</strong>{" "}
        <span>{balanceFmt} VND</span>
      </div>

      <label className={styles.checkbox}>
        <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
        I agree to the terms and conditions.
      </label>

       <div className={styles.buttonGroup}>
        <button className={styles.button} type="submit" disabled={loading}>
          {loading ? "Processing..." : "Get OTP"}
        </button>

        <button type="button" onClick={handleLogout} className={`${styles.button} ${styles.danger}`} disabled={loading}>
          Logout
        </button>
      </div>

      {otpContext && (
        <OTPForm
          key={otpContext.paymentId}
          paymentId={otpContext.paymentId}
          expiresAt={otpContext.expiresAt}
          onVerified={handleOtpVerified}
          onExpired={handleOtpExpired}
        />
      )}
    </form>
  );
}
