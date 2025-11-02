import { useEffect, useMemo, useState } from "react";
import { getAccountMe } from "../api/account";
import { getTuitionByStudentId } from "../api/tuition";
import { initPayment } from "../api/payment";
import { logout } from "../api/auth";

export default function PaymentForm({ onLoggedOut }) {
  const [me, setMe] = useState(null);
  const [studentId, setStudentId] = useState("");
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
    if (!studentId) return;
    setLoading(true);
    setMsg("");
    try {
      const resp = await getTuitionByStudentId(studentId);
      setTuitionId(resp.tuition_id);
      setStudentName(resp.student_id || "");
      setTermNo(resp.term_no || "");
      setTuitionAmount(String(resp.amount_due ?? ""));
    } catch (e) {
      setMsg("Tuition not found for student id");
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
    if (!agree) {
      setMsg("Please accept the terms.");
      return;
    }
    if (!tuitionId || !tuitionAmount) {
      setMsg("Please lookup tuition first.");
      return;
    }
    setLoading(true);
    setMsg("");
    try {
      const res = await initPayment({ tuition_id: tuitionId, amount: Number(tuitionAmount), term_no: termNo || undefined });
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

  return (
    <form className="card form" onSubmit={handleGetOtp}>
      <h2>Tuition Payment</h2>

      {msg && <div className="info">{msg}</div>}

      <h3>1. Payer Information</h3>
      <label>
        Full Name
        <input value={me?.full_name || ""} disabled />
      </label>
      <label>
        Phone Number
        <input value={me?.phone_number || ""} disabled />
      </label>
      <label>
        Email
        <input value={me?.email || ""} disabled />
      </label>

      <h3>2. Tuition Information</h3>
      <label>
        Student ID (MSSV)
        <div className="row">
          <input value={studentId} onChange={(e) => setStudentId(e.target.value)} placeholder="e.g., 523K0001" />
          <button type="button" onClick={handleLookup} disabled={loading || !studentId} className="secondary">Lookup</button>
        </div>
      </label>
      <label>
        Student Name
        <input value={studentName} onChange={(e) => setStudentName(e.target.value)} />
      </label>
      <label>
        Tuition Amount (VND)
        <input value={tuitionAmount} onChange={(e) => setTuitionAmount(e.target.value)} />
      </label>

      <h3>3. Payment Information</h3>
      <div style={{ marginBottom: 8 }}>
        <strong>Available Balance:</strong> <span style={{ color: "green" }}>{balanceFmt} VND</span>
      </div>
      <label className="checkbox">
        <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} /> I agree to the terms and conditions.
      </label>

      <button type="submit" disabled={loading}>{loading ? "Processing..." : "Get OTP"}</button>
      <button type="button" onClick={handleLogout} className="danger" disabled={loading}>Logout</button>
    </form>
  );
}

