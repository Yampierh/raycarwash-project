"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export default function SignupPage() {
  const [role, setRole] = useState<"client" | "detailer">("client");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#fafafa" }}>
      <div style={{ width: "100%", maxWidth: "420px", padding: "40px 24px" }}>
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <Link href="/" style={{ display: "inline-flex", alignItems: "center", gap: "8px", marginBottom: "20px" }}>
            <span style={{ width: "32px", height: "32px", borderRadius: "9px", background: "#09090b", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: "16px" }}>R</span>
            <span style={{ fontWeight: 700, fontSize: "16px" }}>RayCarWash</span>
          </Link>
          <h1 style={{ fontSize: "24px", fontWeight: 800, letterSpacing: "-0.02em", margin: "0 0 8px" }}>Create your account</h1>
          <p style={{ fontSize: "14px", color: "#71717a", margin: 0 }}>Join RayCarWash in Fort Wayne, IN</p>
        </div>

        <div style={{ background: "white", borderRadius: "16px", border: "1px solid #e4e4e7", padding: "28px", boxShadow: "0 4px 12px -2px rgba(9,9,11,0.06)" }}>
          {/* Role toggle */}
          <div style={{ marginBottom: "24px" }}>
            <div style={{ fontSize: "13px", fontWeight: 600, marginBottom: "8px" }}>I want to…</div>
            <div className="aud-toggle" style={{ width: "100%" }}>
              <button className={role === "client" ? "on" : ""} onClick={() => setRole("client")} style={{ flex: 1 }}>Book a detail</button>
              <button className={role === "detailer" ? "on" : ""} onClick={() => setRole("detailer")} style={{ flex: 1 }}>Become a detailer</button>
            </div>
          </div>

          <form onSubmit={e => e.preventDefault()}>
            {[
              { label: "Full name", type: "text", value: name, set: setName, placeholder: "Marcus Tate" },
              { label: "Email", type: "email", value: email, set: setEmail, placeholder: "you@example.com" },
              { label: "Password", type: "password", value: password, set: setPassword, placeholder: "8+ characters" },
            ].map(f => (
              <div key={f.label} style={{ marginBottom: "16px" }}>
                <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>{f.label}</label>
                <input
                  type={f.type} value={f.value} onChange={e => f.set(e.target.value)} required
                  style={{ width: "100%", padding: "11px 14px", border: "1px solid #d4d4d8", borderRadius: "10px", fontSize: "14px", outline: "none" }}
                  placeholder={f.placeholder}
                />
              </div>
            ))}
            <button type="submit" className="btn btn-dark btn-block btn-lg" style={{ marginTop: "4px" }}>
              {role === "client" ? "Create account" : "Start application"} <ArrowRight size={16} />
            </button>
            <p style={{ fontSize: "12px", color: "#a1a1aa", textAlign: "center", marginTop: "12px" }}>
              By signing up you agree to our{" "}
              <Link href="/legal/terms" style={{ color: "#2563eb" }}>Terms</Link>{" "}and{" "}
              <Link href="/legal/privacy" style={{ color: "#2563eb" }}>Privacy Policy</Link>.
            </p>
          </form>
          <div style={{ textAlign: "center", marginTop: "16px", fontSize: "14px", color: "#71717a" }}>
            Already have an account?{" "}
            <Link href="/login" style={{ color: "#2563eb", fontWeight: 600 }}>Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
