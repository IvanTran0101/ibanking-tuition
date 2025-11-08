import { useState } from "react";
import { login } from "../api/auth";
import styles from "./LoginForm.module.css";

export default function LoginForm({ onLoggedIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login({ username, password });
      onLoggedIn?.();
    } catch (err) {
      setError(//err?.message || 
        "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className={styles.card} onSubmit={handleSubmit}>
      <h2 className={styles.title}>Sign In</h2>

      {error && <div className={styles.error}>{error}</div>}

      <label className={styles.label}>
        Username
        <input
          className={styles.input}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
      </label>

      <label className={styles.label}>
        Password
        <input
          className={styles.input}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </label>

      <button className={styles.button} type="submit" disabled={loading}>
        {loading ? "Signing in..." : "Login"}
      </button>
    </form>
  );
}
