import React, { useState } from 'react';
import { Copy, Check, Terminal, Code2, Send, Zap } from 'lucide-react';
import { copyTextToClipboard } from '../services/clipboard';

export default function ApiDocsView() {
  const [copiedKey, setCopiedKey] = useState(null);

  const copyCode = async (key, text) => {
    const success = await copyTextToClipboard(text);
    if (success) {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    }
  };

  const postmanUrl = `${window.location.origin}/api/v1/purchase-books/1`;
  const curlExample = `curl -X GET "${window.location.origin}/api/v1/purchase-books/1"`;
  const sampleResponse = `{
  "Purchase Books": {
    "GRN No.": "",
    "Voucher No": "SA-992",
    "Voucher Date  :": "07/10/2026",
    "Supplier": "SHREE NAKODA TEXTILES",
    "Bill No": "SA-992",
    "Bill Date  ": "07/10/2026",
    "Product Amount": 152918.22,
    "Taxable Amount": 148331.0,
    "Total Qty": 5201.3,
    "Total Pcs": 48,
    "total Tax": 7416.0,
    "Invoice Amount": 155747.0,
    "Narration": "Payment within 20 Days",
    "Product Details": [
      {
        "SrNo": 1,
        "Product": "SAMLL SALLY GADWAL 2218 -",
        "Qty": 5201.3,
        "Rate": 29.4,
        "Value": 152918.22,
        "Pcs": 48,
        "Quality": "SAMLL SALLY GADWAL 2218 -",
        "Other Information": "547",
        "Location": "PLOT NO.A-44, MIDC BADLAPUR, DIST.THANE, BADLAPUR 421503",
        "Remark": "",
        "Chapter Heading": "520811"
      }
    ],
    "Terms": "1. We are not responsible for loss or damage in transit. 2. Payment must be done by PAYEE A/C. Draft by registered post. 3. Interest @ 24% per annum after due date.",
    "cgst": 3708.0,
    "sgst": 3708.0
  }
}`;

  return (
    <div className="animate-fade-in" style={{ maxWidth: 950, margin: '0 auto' }}>
      <div style={{ marginBottom: 28 }}>
        <h1 className="page-title">Purchase Books ERP API</h1>
        <p className="page-desc">
          Single dedicated GET API to retrieve exact Purchase Books JSON directly into Postman or ERP systems.
        </p>
      </div>

      {/* Main Single API Card */}
      <div className="card" style={{ border: '1px solid var(--tiffany-border)', boxShadow: '0 4px 20px rgba(78, 205, 196, 0.08)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span 
              style={{ 
                padding: '6px 14px', 
                borderRadius: 6, 
                fontWeight: 700, 
                fontSize: '0.88rem',
                background: 'rgba(16, 185, 129, 0.2)',
                color: 'var(--success)',
                fontFamily: 'var(--font-mono)'
              }}
            >
              GET
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-main)' }}>
              /api/v1/purchase-books/{'{id}'}
            </span>
          </div>
          <span style={{ fontSize: '0.8rem', padding: '4px 10px', borderRadius: 20, background: 'var(--tiffany-tint)', color: 'var(--tiffany-deep)', fontWeight: 600 }}>
            Postman Ready
          </span>
        </div>

        <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', marginBottom: 20, lineHeight: 1.6 }}>
          Pass the document's <strong>SR NO</strong> (e.g. <code>1</code>, <code>2</code>, <code>3</code>) from the Dashboard / Explorer table, or the unique Document UUID. Returns the exact <strong>Purchase Books</strong> ERP JSON directly with zero wrappers or extraneous fields.
        </p>

        {/* Postman URL Quick Copy */}
        <div style={{ marginBottom: 20, padding: 16, background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Send size={14} color="var(--primary)" /> Postman Request URL
            </span>
            <button 
              className="btn btn-secondary" 
              style={{ padding: '4px 10px', fontSize: '0.78rem' }}
              onClick={() => copyCode('postman', postmanUrl)}
            >
              {copiedKey === 'postman' ? <Check size={13} color="var(--success)" /> : <Copy size={13} />} Copy URL
            </button>
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.88rem', color: 'var(--primary)', wordBreak: 'break-all' }}>
            {postmanUrl}
          </div>
        </div>

        {/* Parameters Section */}
        <div style={{ marginBottom: 22 }}>
          <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: 10 }}>
            Path Parameters
          </h3>
          <table className="data-table" style={{ width: '100%', fontSize: '0.85rem' }}>
            <thead>
              <tr>
                <th style={{ width: 140 }}>Parameter</th>
                <th style={{ width: 100 }}>Type</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><code>id</code></td>
                <td><span style={{ color: 'var(--text-dim)' }}>Integer / UUID</span></td>
                <td>
                  The <strong>SR NO</strong> (e.g., <code>1</code>, <code>2</code>) displayed to the left of the Filename in the table, or the Document UUID.
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* cURL Example */}
        <div style={{ marginBottom: 22 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Terminal size={14} /> Example cURL Command
            </span>
            <button 
              className="btn btn-secondary" 
              style={{ padding: '4px 8px', fontSize: '0.75rem' }}
              onClick={() => copyCode('curl', curlExample)}
            >
              {copiedKey === 'curl' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />} Copy cURL
            </button>
          </div>
          <div className="code-block" style={{ fontSize: '0.82rem' }}>
            {curlExample}
          </div>
        </div>

        {/* Sample Response */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Code2 size={14} /> Result in Postman (Direct Purchase Books ERP JSON)
            </span>
            <button 
              className="btn btn-secondary" 
              style={{ padding: '4px 8px', fontSize: '0.75rem' }}
              onClick={() => copyCode('resp', sampleResponse)}
            >
              {copiedKey === 'resp' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />} Copy Sample JSON
            </button>
          </div>
          <div className="code-block" style={{ fontSize: '0.8rem', maxHeight: 320, overflowY: 'auto' }}>
            {sampleResponse}
          </div>
        </div>
      </div>
    </div>
  );
}
