"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#fafafa" }}>
      <div style={{ width: "100%", maxWidth: "400px", padding: "40px 24px" }}>
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <Link href="/" style={{ display: "inline-flex", alignItems: "center", gap: "8px", marginBottom: "20px" }}>
            <span style={{ width: "32px", height: "32px", borderRadius: "9px", background: "#09090b", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: "16px" }}>R</span>
            <span style={{ fontWeight: 700, fontSize: "16px" }}>RayCarWash</span>
          </Link>
          <h1 style={{ fontSize: "24px", fontWeight: 800, letterSpacing: "-0.02em", margin: "0 0 8px" }}>Welcome back</h1>
          <p style={{ fontSize: "14px", color: "#71717a", margin: 0 }}>Sign in to your account</p>
        </div>

        <div style={{ background: "white", borderRadius: "16px", border: "1px solid #e4e4e7", padding: "28px", boxShadow: "0 4px 12px -2px rgba(9,9,11,0.06)" }}>
          <form onSubmit={e => e.preventDefault()}>
            <div style={{ marginBottom: "16px" }}>
              <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>Email</label>
              <input
                type="email" value={email} onChange={e => setEmail(e.target.value)} required
                style={{ width: "100%", padding: "11px 14px", border: "1px solid #d4d4d8", borderRadius: "10px", fontSize: "14px", outline: "none" }}
                placeholder="you@example.com"
              />
            </div>
            <div style={{ marginBottom: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                <label style={{ fontSize: "13px", fontWeight: 600 }}>Password</label>
                <a href="#" style={{ fontSize: "13px", color: "#2563eb" }}>Forgot?</a>
              </div>
              <input
                type="password" value={password} onChange={e => setPassword(e.target.value)} required
                style={{ width: "100%", padding: "11px 14px", border: "1px solid #d4d4d8", borderRadius: "10px", fontSize: "14px", outline: "none" }}
                placeholder="••••••••"
              />
            </div>
            <button type="submit" className="btn btn-dark btn-block btn-lg">
              Sign in <ArrowRight size={16} />
            </button>
          </form>
          <div style={{ textAlign: "center", marginTop: "20px", fontSize: "14px", color: "#71717a" }}>
            Don&apos;t have an account?{" "}
            <Link href="/signup" style={{ color: "#2563eb", fontWeight: 600 }}>Sign up</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
