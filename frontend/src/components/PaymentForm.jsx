import { useEffect, useMemo, useRef, useState } from "react";
import { getAccountMe } from "../api/account";
import { getTuitionByStudentId } from "../api/tuition";
import { initPayment } from "../api/payment";
import { logout } from "../api/auth";
import styles from "./PaymentForm.module.css";

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
    if (!tuitionId || !tuitionAmount) return setMsg("Please lookup tuition first.");

    setLoading(true);
    setMsg("");

    try {
      const res = await initPayment({
        tuition_id: tuitionId,
        amount: Number(tuitionAmount),
        term_no: termNo || undefined
      });
      setMsg(`OTP sent for payment ${res.payment_id}. Please check your email.`);
    } catch (e) {
      setMsg(e?.message || "Failed to start payment");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    logout();
    onLoggedOut?.();
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
    <form className="card form" onSubmit={handleGetOtp}>
      <h2 className="title">Tuition Payment</h2>

      {msg && <div className="info">{msg}</div>}

      <h3>1. Payer Information</h3>

      <label className="label">
        Full Name
        <input className="input" value={me?.full_name || ""} disabled />
      </label>

      <label className="label">
        Phone Number
        <input className="input" value={me?.phone_number || ""} disabled />
      </label>

      <label className="label">
        Email
        <input className="input" value={me?.email || ""} disabled />
      </label>

      <h3>2. Tuition Information</h3>

      <label className="label">
        Student ID (MSSV)
        <div className="row">
          <input
            className="input"
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
            placeholder="Enter student code (e.g., 523K0017)"
          />
        </div>
      </label>

      <label className="label">
        Student Name
        <input className="input" value={studentName} onChange={(e) => setStudentName(e.target.value)} />
      </label>

      <label className="label">
        Tuition Amount (VND)
        <input className="input" value={tuitionAmount} onChange={(e) => setTuitionAmount(e.target.value)} />
      </label>

      <h3>3. Payment Information</h3>

      <div>
        <strong>Available Balance:</strong>{" "}
        <span style={{ color: "green" }}>{balanceFmt} VND</span>
      </div>

      <label className="checkbox">
        <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
        I agree to the terms and conditions.
      </label>

      <button className="button" type="submit" disabled={loading}>
        {loading ? "Processing..." : "Get OTP"}
      </button>

      <button type="button" onClick={handleLogout} className="button danger" disabled={loading}>
        Logout
      </button>
    </form>
  );
}
