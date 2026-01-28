import styles from "./PaymentCompleteForm.module.css";

export default function PaymentCompleteForm({
  fullName,
  email,
  phoneNumber,
  studentId,
  studentName,
  tuitionAmount,
  termNo,
  paymentId,
  onNewPayment
}) {
  return (
    <div className={styles.card}>
      <h2 className={styles.title}>Payment Completed</h2>

      <p className={styles.info}>
        Your payment has been successfully processed. Below is a summary of your transaction:
      </p>

      <h3>Payer Information</h3>
      <div className={styles.field}>
        <strong>Full Name:</strong> <span>{fullName}</span>
      </div>
      <div className={styles.field}>
        <strong>Email:</strong> <span>{email}</span>
      </div>
      <div className={styles.field}>
        <strong>Phone Number:</strong> <span>{phoneNumber}</span>
      </div>

      <h3>Tuition Information</h3>
      <div className={styles.field}>
        <strong>Student ID:</strong> <span>{studentId}</span>
      </div>
      <div className={styles.field}>
        <strong>Student Name:</strong> <span>{studentName}</span>
      </div>
      <div className={styles.field}>
        <strong>Term No:</strong> <span>{termNo || "N/A"}</span>
      </div>
      <div className={styles.field}>
        <strong>Amount Paid:</strong>{" "}
        <span>{Number(tuitionAmount).toLocaleString()} VND</span>
      </div>

      <h3>Payment Details</h3>
      <div className={styles.field}>
        <strong>Payment ID:</strong> <span>{paymentId}</span>
      </div>

      <div className={styles.footer}>
        <button onClick={onNewPayment} className={styles.button}>
          Make a New Payment
        </button>
      </div>
    </div>
  );
}
